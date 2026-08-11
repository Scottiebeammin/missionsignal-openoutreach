"""Score how relevant an opportunity is to a specific organization.

Federal grants (Grants.gov) arrive with no focus_areas/beneficiaries, so a plain
keyword pull surfaces off-topic grants (e.g. "English Teaching in Brazil" for a
girls-empowerment org). This module scores each opportunity by how much its text
overlaps the org's OWN focus areas + beneficiaries + mission — so what surfaces is
tied to what the nonprofit actually does and who it serves.

When the org checks a new focus area or beneficiary (financial literacy, people
with disabilities, etc.), those keywords immediately start matching opportunities —
no code change needed; the relevance just shifts with the profile.
"""
import html
import re

# Generic words that would match almost anything — excluded so scoring is meaningful.
_STOPWORDS = {
    "and", "the", "for", "with", "that", "this", "from", "into", "your", "our",
    "their", "support", "program", "programs", "services", "service", "general",
    "other", "inc", "ages", "age", "of", "to", "in", "on", "or", "at", "by", "an",
    "a", "grant", "grants", "funding", "fund", "foundation", "community", "people",
    "development", "national", "initiative", "project", "competition",
}


# Foreign-country / overseas markers — a US-domestic nonprofit can't use these grants
# even if the topic overlaps (e.g. "English Teaching for STEM in Brazil"). State Dept
# / embassy / mission grants are the usual culprits in a Grants.gov pull.
_FOREIGN_COUNTRIES = {
    "brazil", "algeria", "albania", "mexico", "india", "china", "kenya", "nigeria",
    "egypt", "ukraine", "pakistan", "afghanistan", "iraq", "jordan", "lebanon",
    "morocco", "tunisia", "colombia", "peru", "ecuador", "ghana", "ethiopia",
    "tanzania", "uganda", "vietnam", "indonesia", "philippines", "bangladesh",
    "nepal", "cambodia", "armenia", "azerbaijan", "kazakhstan", "moldova",
    "serbia", "kosovo", "bosnia", "macedonia", "turkmenistan", "uzbekistan", "mongolia",
    "rwanda", "senegal", "zambia", "zimbabwe", "malawi", "mozambique", "angola",
}
_FOREIGN_PHRASES = ("u.s. mission to", "u.s. embassy", "overseas", " abroad", "foreign assistance")

# If the grant explicitly supports US-based orgs/communities, KEEP it even when a
# foreign country is mentioned (e.g. a multinational corp's US giving program, or a
# program serving the US among other countries). US-only focus, but not at the cost
# of dropping grants that fund US nonprofits.
_US_SUPPORT_PHRASES = (
    "u.s.-based", "us-based", "u.s. based", "domestic nonprofit", "u.s. nonprofit",
    "us nonprofit", "u.s. nonprofits", "nationwide", "all 50 states",
    "across the united states", "u.s. communities", "american nonprofit",
    "501(c)(3)", "united states-based",
)


# Academic / research-grant markers — NIH/NSF studies, fellowships, scholarships,
# and university-research mechanisms a community nonprofit can't realistically pursue.
# These often match on a topic keyword ("adolescent", "youth") but are the wrong fit.
_RESEARCH_MARKERS = (
    "limited competition for the", "cognitive neuroscience", "clinical trial",
    "principal investigator", "investigator-initiated", "research project grant",
    "graduate education", "undergraduate", "postdoctoral", "doctoral",
    "fellowship", "scholarship", "abcd study", "formation of engineers",
    "biomedical research", "scientific research", "r01", "u01", "sbir", "sttr",
    "dissertation", "laboratory", "neuroimaging",
    # broadened: research/clinical centers, NIH/NSF mechanisms, defense-research pipelines
    "research center", "research institute", "post-traumatic", "epilepsy",
    "national defense education", "u24", "u54", "r21", "p20", "p30", "k23",
    "phase ii clinical", "phase iii clinical", "data coordinating center",
    "informatics and resource", "translational research", "basic research",
)


def is_research_grant(opportunity) -> bool:
    """True if the opportunity is an academic / research grant (NIH/NSF study,
    fellowship, scholarship, university mechanism) — wrong fit for a community nonprofit."""
    text = f"{opportunity.name} {opportunity.source_name or ''}".lower()
    return any(m in text for m in _RESEARCH_MARKERS)


def is_not_applicable(opportunity, organization=None) -> bool:
    """True when a US-domestic community nonprofit can never act on this row.

    The single definition of "don't put this on a client's board", shared by the
    recommendation views, the lifecycle board and the discovery inventory. Those
    three used to screen differently — discovery scored CREST at 85 while the
    recommendation views forced it to zero — which is how university-only and
    overseas programmes stayed visible on the one screen clients actually work
    from. Disqualification is a different judgement from a low score and belongs
    in one place.
    """
    return is_off_geography(opportunity, organization) or is_research_grant(opportunity)


def is_off_geography(opportunity, organization=None) -> bool:
    """True if the opportunity is tied to a foreign country / overseas post — disqualified
    for a US-domestic nonprofit. Override: kept if it explicitly supports US-based orgs."""
    text = (
        f"{opportunity.name} {opportunity.source_name or ''} "
        f"{opportunity.eligibility_notes or ''} {opportunity.notes or ''}"
    ).lower()
    if any(p in text for p in _US_SUPPORT_PHRASES):
        return False
    if any(phrase in text for phrase in _FOREIGN_PHRASES):
        return True
    return bool(set(re.findall(r"[a-z]+", text)) & _FOREIGN_COUNTRIES)


# Grants.gov applicant-type codes are useless for this: NSF tags nearly every
# program "25 — Others (see text field entitled Additional Information on
# Eligibility)", so a type check passes programs that are closed to nonprofits.
# The truth is in the eligibility prose, which we already store.
_WHO_MAY_SUBMIT = re.compile(r"who\s+may\s+submit[^:]*:", re.I)
_NONPROFIT_CATEGORY = re.compile(r"non-?profit", re.I)
_HIGHER_ED_CATEGORY = re.compile(
    r"institutions?\s+of\s+higher\s+(education|learning)|\bIHEs?\b"
    r"|minority[-\s]serving\s+institutions|\bMSIs\b",
    re.I,
)

ELIGIBILITY_OPEN = "open"
ELIGIBILITY_RESTRICTED = "restricted"
ELIGIBILITY_UNKNOWN = "unknown"


def eligibility_stance(opportunity) -> str:
    """Can a community nonprofit be the prime applicant?

    "open"       — a nonprofit category is named among eligible applicants
    "restricted" — only degree-granting institutions are named
    "unknown"    — the notice doesn't say, or we have no text

    Reads the "Who May Submit Proposals" block rather than the whole document,
    which is the difference between getting LSAMP right and wrong: every LSAMP
    track (ADG, SPIO, SPRA) lists Institutions of Higher Education and nothing
    else, while the word "nonprofit" still appears further down the notice in
    other contexts. ATE, by contrast, names "Non-profit, non-academic
    organizations" inside the block itself.

    Deliberately conservative: absent an explicit restriction this returns
    "unknown", never "restricted". Hiding a grant a client could have won is a
    worse failure than showing one they have to read twice.
    """
    text = html.unescape(opportunity.eligibility_notes or "")
    if not text.strip():
        return ELIGIBILITY_UNKNOWN
    match = _WHO_MAY_SUBMIT.search(text)
    if match:
        # NSF delimits its sections with "*"; stop at the next one so a later
        # section ("Who May Serve as PI") can't leak categories into this answer.
        block = text[match.end():]
        star = block.find("*")
        if star > 0:
            block = block[:star]
    else:
        block = text
    if _NONPROFIT_CATEGORY.search(block):
        return ELIGIBILITY_OPEN
    if _HIGHER_ED_CATEGORY.search(block):
        return ELIGIBILITY_RESTRICTED
    return ELIGIBILITY_UNKNOWN


def eligibility_rank(opportunity) -> int:
    """Sort key: 0 keeps an opportunity in contention, 1 sinks it.

    Only demotes what the notice itself rules out, so "unknown" ranks alongside
    "open" — the ordering within each tier is still relevance.
    """
    return 1 if eligibility_stance(opportunity) == ELIGIBILITY_RESTRICTED else 0


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", (text or "").lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def org_keywords(organization) -> set[str]:
    """The org's relevance vocabulary — what it does + who it serves + its mission."""
    kw: set[str] = set()
    for term in list(organization.focus_areas or []) + list(organization.beneficiaries or []):
        kw |= _tokens(str(term))
    kw |= _tokens(getattr(organization, "mission", "") or "")
    return kw


# State/county/city sources reach a project only by matching its geography, so
# they arrive having passed a test the federal pull never applies. Scoring them
# on keyword overlap measures the wrong thing: a federal notice carries pages of
# matchable prose, while a local source is "City of Orlando — Community
# Investment Program" and nothing else. Left unfloored, three of Tech Sassy
# Girlz's four local sources scored 0 and never reached the board at all.
LOCAL_SOURCE_PREFIX = "localgov:"

# Calibrated against the real prod distribution for Tech Sassy Girlz, not guessed:
#   score: 8→1  7→2  6→1  5→2  4→12  3→5  2→14  1→40  0→138
# The mass at 4 is the marginal band — Medical Student Education, HBCU Excellence
# in Research, EPSCoR — matches on a shared word rather than a real fit. A floor
# of 4 ties local sources with those eight federal rows, and since local rows
# carry no deadline they lose the tiebreak and land around position 15, still off
# the shelf. 5 is the smallest value that clears the marginal band outright while
# staying below every federal row scoring 5+, so a county programme can outrank a
# coincidental keyword hit but never a genuine topical match. Local rows still
# score above the floor when their own text overlaps.
LOCAL_GEOGRAPHY_FLOOR = 5


def is_local_government_source(opportunity) -> bool:
    """True for rows created by pull_local_grants (state / county / city)."""
    return str(getattr(opportunity, "external_id", "") or "").startswith(LOCAL_SOURCE_PREFIX)


def opportunity_relevance(opportunity, keywords: set[str]) -> int:
    """Count of distinct org keywords that appear in the opportunity's text.

    0 = no overlap (off-topic — kept out of the top recommendations).

    Geography-matched local sources are floored at LOCAL_GEOGRAPHY_FLOOR: being
    the county you operate in is relevance of a different kind than sharing
    vocabulary, and the disqualifiers in the callers (off-geography, research-
    only) still zero these rows if they trip.
    """
    if not keywords:
        return LOCAL_GEOGRAPHY_FLOOR if is_local_government_source(opportunity) else 0
    parts = [
        opportunity.name,
        opportunity.notes,
        opportunity.eligibility_notes,
        opportunity.source_name,
    ]
    parts += [str(x) for x in (opportunity.focus_areas or [])]
    parts += [str(x) for x in (opportunity.beneficiaries or [])]
    opp_tokens = _tokens(" ".join(p for p in parts if p))
    score = len(keywords & opp_tokens)
    if is_local_government_source(opportunity):
        return max(score, LOCAL_GEOGRAPHY_FLOOR)
    return score
