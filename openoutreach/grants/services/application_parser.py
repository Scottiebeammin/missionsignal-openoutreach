"""Turn a pasted grant application into structured questions.

Deliberately deterministic — regex and heuristics, no LLM. Three reasons:

1. **Fidelity.** The funder's wording must survive byte-for-byte. A model that
   paraphrases a question has changed what the organization is answering.
2. **Testability.** Every rule here is pinned by a test. "Maximum 500 words"
   must become ``word_limit=500`` every time, not usually.
3. **Availability.** Import works with no LLM key configured, like the rest of
   the non-drafting half of Grant Builder.

The parser is honest about being fallible: it reports a confidence level and
notes what it was unsure of, and nothing it produces is saved until a person has
reviewed it on the import-review screen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from openoutreach.grants.models import GrantApplicationSection

QuestionType = GrantApplicationSection.QuestionType


@dataclass
class ParsedQuestion:
    text: str
    section_group: str = ""
    label: str = ""
    instructions: str = ""
    question_type: str = QuestionType.NARRATIVE
    required: bool = True
    word_limit: int | None = None
    character_limit: int | None = None
    page_limit_note: str = ""
    scoring_notes: str = ""
    attachment_requirement: str = ""
    order: int = 0


@dataclass
class ParsedAttachment:
    title: str
    document_type: str = "other"


@dataclass
class ParsedApplication:
    questions: list[ParsedQuestion] = field(default_factory=list)
    application_instructions: list[str] = field(default_factory=list)
    attachments: list[ParsedAttachment] = field(default_factory=list)
    confidence: str = "medium"
    notes: list[str] = field(default_factory=list)
    # Text the parser could not place. Surfaced for review rather than dropped.
    unparsed_blocks: list[str] = field(default_factory=list)

    @property
    def question_count(self) -> int:
        return len(self.questions)


# ── Limit detection ──────────────────────────────────────────────────────────
# Ordered most-specific first; the first match wins so "2,500 characters" never
# gets read as the number 2.

_WORD_LIMIT_PATTERNS = (
    re.compile(r"(?:maximum|max\.?|no more than|not to exceed|limit(?:ed)?(?:\s+(?:your\s+)?response)?\s+to|up to)\s*(?:of\s*)?([\d,]+)\s*words?", re.I),
    re.compile(r"([\d,]+)[\s-]*words?\s*(?:maximum|max\.?|limit|or less|or fewer)", re.I),
    re.compile(r"\(\s*([\d,]+)\s*words?\s*\)", re.I),
    re.compile(r"word\s*(?:count\s*)?limit\s*[:\-]?\s*([\d,]+)", re.I),
)

_CHAR_LIMIT_PATTERNS = (
    re.compile(r"(?:maximum|max\.?|no more than|not to exceed|limit(?:ed)? (?:your )?response to|limit(?:ed)? to|up to)\s*(?:of\s*)?([\d,]+)\s*characters?", re.I),
    re.compile(r"([\d,]+)[\s-]*characters?\s*(?:maximum|max\.?|limit|or less|or fewer)", re.I),
    re.compile(r"\(\s*([\d,]+)\s*characters?\s*\)", re.I),
    re.compile(r"character\s*(?:count\s*)?limit\s*[:\-]?\s*([\d,]+)", re.I),
)

_PAGE_LIMIT_PATTERN = re.compile(
    r"(?:(?:maximum|max\.?|no more than|not to exceed|limit(?:ed)? to|up to)\s*(?:of\s*)?([\d,]+|one|two|three)\s*pages?"
    r"|([\d,]+|one|two|three)[\s-]*pages?\s*(?:maximum|max\.?|limit))",
    re.I,
)


def _to_int(raw: str) -> int | None:
    try:
        return int(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def detect_word_limit(text: str) -> int | None:
    for pattern in _WORD_LIMIT_PATTERNS:
        match = pattern.search(text)
        if match:
            value = _to_int(match.group(1))
            if value:
                return value
    return None


def detect_character_limit(text: str) -> int | None:
    for pattern in _CHAR_LIMIT_PATTERNS:
        match = pattern.search(text)
        if match:
            value = _to_int(match.group(1))
            if value:
                return value
    return None


def detect_page_limit(text: str) -> str:
    """Page limits are recorded as a note — Atlas cannot count the funder's pages."""
    match = _PAGE_LIMIT_PATTERN.search(text)
    if not match:
        return ""
    value = (match.group(1) or match.group(2) or "").strip()
    if not value:
        return ""
    plural = "" if value in {"1", "one"} else "s"
    return f"maximum {value} page{plural}"


# ── Required / optional ──────────────────────────────────────────────────────

_OPTIONAL_MARKERS = re.compile(
    r"\(\s*optional\s*\)|\boptional\b|\bif applicable\b|\bif desired\b|\byou may\b|\bnot required\b", re.I,
)
_REQUIRED_MARKERS = re.compile(r"\(\s*required\s*\)|\brequired\b|\bmust\b|\bmandatory\b", re.I)


def detect_required(text: str) -> bool:
    """Default to required — under-claiming an obligation is the safer error."""
    if _OPTIONAL_MARKERS.search(text) and not _REQUIRED_MARKERS.search(text):
        return False
    return True


# ── Question type ────────────────────────────────────────────────────────────

_YES_NO = re.compile(r"\(\s*yes\s*/\s*no\s*\)|\byes or no\b|^\s*(?:do|does|did|is|are|was|were|has|have|will|can)\b.*\?\s*$", re.I)
_CURRENCY = re.compile(
    r"\bamount requested\b|\btotal budget\b|\$\s*_+|\bdollar amount\b|\brequested amount\b"
    r"|\bbudget total\b|\b(?:annual\s+)?operating budget\b|\bannual budget\b"
    r"|\bamount of (?:the )?request\b",
    re.I,
)
_NUMERIC = re.compile(r"\bhow many\b|\bnumber of\b|\bcount of\b|\btotal number\b|\bpercentage of\b|\bein\b|\btax id\b", re.I)
_DATE = re.compile(r"\bdate of\b|\bstart date\b|\bend date\b|\bdate founded\b|\byear (?:founded|established|incorporated)\b|\bmm/dd/yyyy\b", re.I)
_ATTACHMENT = re.compile(r"\battach\b|\bupload\b|\benclose\b|\bsubmit a copy\b|\binclude a copy\b|\bplease provide a copy\b", re.I)
_MULTIPLE_CHOICE = re.compile(r"\bselect (?:one|all that apply)\b|\bcheck all that apply\b|\bchoose one\b", re.I)
_INFORMATIONAL = re.compile(
    r"^(?:organization\s+name|legal\s+name|name\s+of\s+organization|ein|tax\s*id|address|city|"
    r"state|zip|phone|website|contact\s+(?:name|person|email|title)|email|executive\s+director|"
    r"federal\s+tax\s+id)\b[^?]{0,40}:?\s*$", re.I,
)
_NARRATIVE_VERBS = re.compile(
    r"^\s*(?:describe|explain|provide|summarize|summarise|outline|discuss|detail|tell us|share|"
    r"identify|list|state|what|how|why|who|when|where|in what ways)\b", re.I,
)


def classify_question(text: str, word_limit: int | None, character_limit: int | None) -> str:
    stripped = text.strip()
    if _ATTACHMENT.search(stripped):
        return QuestionType.ATTACHMENT
    if _MULTIPLE_CHOICE.search(stripped):
        return QuestionType.MULTIPLE_CHOICE
    if _YES_NO.search(stripped):
        return QuestionType.YES_NO
    if _CURRENCY.search(stripped):
        return QuestionType.CURRENCY
    if _DATE.search(stripped):
        return QuestionType.DATE
    if _NUMERIC.search(stripped):
        return QuestionType.NUMERIC
    if _INFORMATIONAL.match(stripped):
        return QuestionType.INFORMATIONAL
    if _NARRATIVE_VERBS.match(stripped) or stripped.endswith("?"):
        # A tight limit means a short answer, not an essay.
        if character_limit and character_limit <= 250:
            return QuestionType.SHORT_TEXT
        if word_limit and word_limit <= 50:
            return QuestionType.SHORT_TEXT
        return QuestionType.NARRATIVE
    if len(stripped) > 80:
        return QuestionType.NARRATIVE
    return QuestionType.UNKNOWN


# ── Attachments ──────────────────────────────────────────────────────────────

_KNOWN_ATTACHMENTS = (
    (re.compile(r"501\s*\(?c\)?\s*\(?3\)?|determination letter|irs\s+determination|tax[- ]exempt (?:status )?letter", re.I),
     "IRS determination letter", "irs_determination_letter"),
    (re.compile(r"\bboard (?:roster|list|of directors)\b|\blist of board members\b", re.I),
     "Board roster", "board_list"),
    (re.compile(r"\bproject budget\b|\bprogram budget\b", re.I), "Project budget", "program_budget"),
    (re.compile(r"\b(?:organizational|organisation(?:al)?|annual|agency) budget\b|\boperating budget\b", re.I),
     "Organizational budget", "annual_budget"),
    (re.compile(r"\baudit(?:ed)?(?:\s+financial\s+statements?)?\b|\bfinancial statements?\b|\bform 990\b|\b990\b", re.I),
     "Audited financial statements", "audit_financial_statement"),
    (re.compile(r"\bletters? of support\b|\bletters? of commitment\b|\bpartner letters?\b", re.I),
     "Letters of support", "other"),
    (re.compile(r"\bstrategic plan\b", re.I), "Strategic plan", "strategic_plan"),
    (re.compile(r"\bannual report\b", re.I), "Annual report", "annual_report"),
    (re.compile(r"\bw-?9\b", re.I), "W-9", "w9"),
    (re.compile(r"\bcertificate of insurance\b|\bproof of insurance\b", re.I), "Insurance certificate", "insurance"),
    (re.compile(r"\bstaff (?:roster|list)\b|\bkey personnel\b|\bresumes?\b|\bbios?\b", re.I),
     "Staff roster or bios", "other"),
    (re.compile(r"\blogic model\b|\bevaluation plan\b", re.I), "Evaluation plan", "outcome_report"),
)

_ATTACHMENT_CONTEXT = re.compile(
    r"\battach|\bupload|\benclose|\bsubmit|\binclude|\brequired document|\bsupporting document|"
    r"\bappendix|\bexhibit|\bdocumentation", re.I,
)


def detect_attachments(text: str, require_context: bool = True) -> list[ParsedAttachment]:
    """Find named documents, but only where the text is actually asking for one.

    The context guard matters: a Statement of Need mentioning "our annual budget
    grew" must not become an attachment requirement.
    """
    found: list[ParsedAttachment] = []
    seen: set[str] = set()
    for line in text.splitlines():
        if require_context and not _ATTACHMENT_CONTEXT.search(line):
            continue
        for pattern, title, doc_type in _KNOWN_ATTACHMENTS:
            if pattern.search(line) and title not in seen:
                seen.add(title)
                found.append(ParsedAttachment(title=title, document_type=doc_type))
    return found


# ── Structure detection ──────────────────────────────────────────────────────

_NUMBERED = re.compile(r"^\s*(?:question\s+)?(\d{1,2})\s*[\.\):]\s+(?=\S)", re.I)
_Q_PREFIX = re.compile(r"^\s*Q\s*(\d{1,2})\s*[\.\):]?\s+(?=\S)", re.I)
_LETTERED = re.compile(r"^\s*\(?([a-hA-H])\s*[\.\)]\s+(?=\S)")
_SECTION_HEADING = re.compile(
    r"^\s*(?:(?:section|part)\s+([A-Z0-9]{1,3})\s*[\.\:\-–]?\s*)(.*)$", re.I,
)
_MD_HEADING = re.compile(r"^\s*#{1,4}\s+(.*)$")
_INSTRUCTION_LEAD = re.compile(
    r"^\s*(?:note|please note|instructions?|important|reminder|all\b|responses? must|"
    r"applications? must|proposals? must|use \d+|font|margins?|single[- ]spac|double[- ]spac|"
    r"submit(?:ted)? (?:by|via|through)|deadline|eligibility|applicants? must|budget must|"
    r"before you begin|organizations? must|proposals? (?:should|will)|applications? (?:should|will))\b",
    re.I,
)
# A statement of obligation that is not a question is an instruction, wherever
# it sits in the document.
_OBLIGATION = re.compile(r"\b(?:must|may not|are required to|is required to|shall)\b", re.I)
_ATTACHMENT_HEADING = re.compile(
    r"^\s*(?:required\s+)?(?:attachments?|supporting\s+documents?|required\s+documents?|documents?\s+(?:required|checklist)|exhibits?|appendices)\s*:?\s*$",
    re.I,
)
_INSTRUCTION_HEADING = re.compile(
    r"^\s*(?:general\s+)?(?:instructions?|guidelines?|before\s+you\s+begin|how\s+to\s+apply|"
    r"application\s+instructions?|submission\s+(?:instructions?|requirements?))\s*:?\s*$", re.I,
)
_BULLET = re.compile(r"^\s*[-*•·]\s+(?=\S)")


def _is_heading(line: str) -> bool:
    """A heading names a part of the form; it does not ask anything."""
    stripped = line.strip()
    if not stripped or stripped.endswith("?"):
        return False
    if _MD_HEADING.match(stripped) or _SECTION_HEADING.match(stripped):
        return True
    if _NUMBERED.match(stripped) or _Q_PREFIX.match(stripped) or _BULLET.match(stripped):
        return False
    if _NARRATIVE_VERBS.match(stripped):
        return False
    words = stripped.rstrip(":").split()
    if not (1 <= len(words) <= 8):
        return False
    letters = [c for c in stripped if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return True
    return stripped.endswith(":") and len(stripped) < 70


def _heading_text(line: str) -> str:
    stripped = line.strip()
    md = _MD_HEADING.match(stripped)
    if md:
        stripped = md.group(1).strip()
    section = _SECTION_HEADING.match(stripped)
    if section:
        label, rest = section.group(1), section.group(2).strip()
        return rest or f"Section {label}"
    return stripped.rstrip(":").strip()


def _starts_sentence(line: str) -> bool:
    """A new question starts with a capital. A lowercase line is a wrapped continuation."""
    for char in line.strip():
        if char.isalpha():
            return char.isupper()
        if char.isdigit():
            return True
    return False


def _is_question_start(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _NUMBERED.match(stripped) or _Q_PREFIX.match(stripped):
        return True
    if _LETTERED.match(stripped) and len(stripped) > 12:
        return True
    if not _starts_sentence(stripped):
        return False
    if stripped.endswith("?"):
        return True
    return bool(_NARRATIVE_VERBS.match(stripped))


def _question_label(line: str) -> str:
    for pattern in (_Q_PREFIX, _NUMBERED, _LETTERED):
        match = pattern.match(line.strip())
        if match:
            return match.group(1)
    return ""


def _strip_label(line: str) -> str:
    """Remove the funder's numbering, keeping their words untouched."""
    stripped = line.strip()
    for pattern in (_Q_PREFIX, _NUMBERED, _LETTERED):
        match = pattern.match(stripped)
        if match:
            return stripped[match.end():].strip()
    return stripped


def _split_instructions(block_lines: list[str]) -> tuple[str, str]:
    """Separate the question itself from the guidance printed beneath it."""
    if not block_lines:
        return "", ""
    question = block_lines[0].strip()
    rest = []
    for line in block_lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        # A trailing sentence that only states a limit belongs to the question.
        if (
            not rest
            and not _INSTRUCTION_LEAD.match(stripped)
            and not stripped.startswith("(")
            and len(question) < 200
            and not detect_word_limit(stripped)
            and not detect_character_limit(stripped)
        ):
            question = f"{question} {stripped}".strip()
            continue
        rest.append(stripped)
    return question, "\n".join(rest)


# ── Parser ───────────────────────────────────────────────────────────────────

def parse_application(text: str) -> ParsedApplication:
    """Parse pasted application text into questions, instructions and attachments."""
    result = ParsedApplication()
    if not (text or "").strip():
        result.confidence = "low"
        result.notes.append("No text was provided.")
        return result

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    current_section = ""
    mode = "body"           # body | instructions | attachments
    blocks: list[tuple[str, list[str]]] = []   # (section_group, lines)
    instruction_lines: list[str] = []
    attachment_lines: list[str] = []
    pending: list[str] | None = None
    pending_section = ""

    def flush():
        nonlocal pending, pending_section
        if pending:
            blocks.append((pending_section, pending))
        pending = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            continue

        if _INSTRUCTION_HEADING.match(stripped):
            flush()
            mode = "instructions"
            continue
        if _ATTACHMENT_HEADING.match(stripped):
            flush()
            mode = "attachments"
            continue

        if _is_heading(stripped):
            flush()
            current_section = _heading_text(stripped)
            mode = "body"
            continue

        if _is_question_start(stripped):
            flush()
            mode = "body"
            pending = [_strip_label(stripped)]
            pending_section = current_section
            continue

        if mode == "instructions":
            instruction_lines.append(_BULLET.sub("", stripped))
            continue
        if mode == "attachments":
            attachment_lines.append(_BULLET.sub("", stripped))
            continue

        if pending is not None:
            pending.append(stripped)
        elif _INSTRUCTION_LEAD.match(stripped) or _OBLIGATION.search(stripped):
            instruction_lines.append(stripped)
        else:
            result.unparsed_blocks.append(stripped)

    flush()

    # ── Build questions ──
    for index, (section_group, block_lines) in enumerate(blocks):
        raw_label = ""
        for original in lines:
            if original.strip() and _strip_label(original.strip()) == block_lines[0]:
                raw_label = _question_label(original)
                break
        question_text, instructions = _split_instructions(block_lines)
        searchable = "\n".join([question_text, instructions])
        word_limit = detect_word_limit(searchable)
        character_limit = detect_character_limit(searchable)
        page_note = detect_page_limit(searchable)
        question = ParsedQuestion(
            text=question_text,
            section_group=section_group,
            label=raw_label,
            instructions=instructions,
            word_limit=word_limit,
            character_limit=character_limit,
            page_limit_note=page_note,
            required=detect_required(searchable),
            question_type=classify_question(question_text, word_limit, character_limit),
            order=index + 1,
        )
        if question.question_type == QuestionType.ATTACHMENT:
            question.attachment_requirement = question_text[:300]
        result.questions.append(question)

    # ── Instructions and attachments ──
    result.application_instructions = [line for line in instruction_lines if line]
    attachment_text = "\n".join(attachment_lines)
    if attachment_text:
        # Everything under an explicit attachments heading is a requirement.
        result.attachments = detect_attachments(attachment_text, require_context=False)
    else:
        result.attachments = detect_attachments(text)
    # Bullets under an explicit "Required Attachments" heading are requirements
    # even when they are not one of the names we recognise.
    known = {a.title.casefold() for a in result.attachments}
    for line in attachment_lines:
        cleaned = line.strip(" .;:")
        if cleaned and len(cleaned) < 120 and cleaned.casefold() not in known:
            if not any(pattern.search(cleaned) for pattern, _t, _d in _KNOWN_ATTACHMENTS):
                result.attachments.append(ParsedAttachment(title=cleaned, document_type="other"))
                known.add(cleaned.casefold())

    result.confidence, result.notes = _assess(result, lines)
    return result


def _assess(result: ParsedApplication, lines: list[str]) -> tuple[str, list[str]]:
    """Say plainly how much to trust this parse."""
    notes: list[str] = []
    count = result.question_count
    non_empty = len([line for line in lines if line.strip()])

    if count == 0:
        notes.append(
            "Atlas could not identify any questions in this text. Check that you pasted the "
            "application's questions, or add them by hand below."
        )
        return "low", notes

    numbered = sum(1 for q in result.questions if q.label)
    if numbered == 0:
        notes.append(
            "No question numbering was found, so Atlas split the text on wording alone. "
            "Check the question boundaries carefully."
        )
    if result.unparsed_blocks:
        notes.append(
            f"{len(result.unparsed_blocks)} block(s) of text could not be placed and were left out. "
            "They are shown below so you can add anything that is really a question."
        )
    if count == 1 and non_empty > 12:
        notes.append("Only one question was detected in a long document — the split may be wrong.")
    if not any(q.word_limit or q.character_limit for q in result.questions):
        notes.append("No word or character limits were detected. Add them by hand if the funder set any.")

    if count >= 3 and numbered >= max(2, count // 2) and not result.unparsed_blocks:
        return "high", notes
    if count == 1 and non_empty > 12:
        return "low", notes
    if numbered == 0 and count < 3:
        return "low", notes
    return "medium", notes
