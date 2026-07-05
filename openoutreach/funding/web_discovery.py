"""Layer 2 grounded discovery — fetch-then-extract foundation grant scanning.

The old research path (`signals/research.py`) asks a bare LLM to *remember*
funders and grants — that produced fake `example.org` rows. This module
inverts the flow:

  1. FETCH real pages first (stdlib urllib, honest UA, same-host redirects).
  2. The LLM's only job is EXTRACTION: it structures what is provably in the
     fetched text. Its output schema has no URL field at all — it cannot
     invent a source. Candidates are stamped with the URL *we fetched*.
  3. Everything is persisted through the existing grounding gate
     (`grounding.ingest_verified_opportunities`) — reachability-checked
     source_urls, reserved-domain rejection, `needs_review` status.

So a saved Opportunity can only ever point at a page this process actually
downloaded. The LLM structures facts; it never generates them.

Public surface:
  fetch_page(url)                        → readable text (headings/paras/list
                                           items, links as [text](href)) or None
  find_grant_links(text, base_url)       → up to N same-host grant-ish links,
                                           deterministic, no LLM
  extract_grant_programs(text, url, org) → LLM extraction, list[dict]
  discover_for_project(project, ...)     → DiscoveryReport (orchestrator)
"""
from __future__ import annotations

import hashlib
import logging
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field

from openoutreach.funding.exceptions import WebDiscoveryLLMUnavailable
from openoutreach.funding.grounding import ingest_verified_opportunities, is_reserved_domain
from openoutreach.funding.models import Funder, Opportunity

logger = logging.getLogger(__name__)

_UA = "AnansiAtlas-discovery/1.0 (+https://anansiatlas.com)"
_MAX_PROMPT_CHARS = 12_000  # cap page text fed to the extractor

# File extensions that can never be an HTML grant page — skip without fetching.
_SKIP_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".mp3", ".mp4",
)


# ── Fetching (stdlib urllib, same-host redirects only) ──────────────────────

def _host(url: str) -> str:
    """Normalized host for same-host comparison (www. stripped, lowercased)."""
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


class _SameHostRedirects(urllib.request.HTTPRedirectHandler):
    """Follow redirects only within the original host — a foundation page that
    redirects off-site is not that foundation's page anymore."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _host(newurl) != _host(req.full_url):
            return None  # urllib raises HTTPError → fetch_page returns None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _http_get(url: str, timeout: int, max_bytes: int) -> tuple[bytes, str, str]:
    """One GET. Returns (body, content_type, charset). Raises on any failure."""
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    opener = urllib.request.build_opener(_SameHostRedirects())
    with opener.open(req, timeout=timeout) as resp:
        content_type = (resp.headers.get("Content-Type") or "").lower()
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read(max_bytes)
    return body, content_type, charset


class _TextExtractor(HTMLParser):
    """Small stdlib HTML→text extractor.

    Keeps headings, paragraphs, list items, and anchors. Anchors are rendered
    as markdown-style ``[text](href)`` so `find_grant_links` can recover them
    from the plain-text output.
    """

    _SKIP = {"script", "style", "noscript", "template", "svg", "iframe"}
    _BLOCK = {
        "p", "div", "section", "article", "header", "footer", "nav", "main",
        "ul", "ol", "table", "tr", "br", "hr", "title",
        "h1", "h2", "h3", "h4", "h5", "h6", "li",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            self._flush_link()
            self._href = dict(attrs).get("href") or ""
            self._link_text = []
            return
        if tag in self._BLOCK:
            self._flush_link()
            self.parts.append("\n")
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                self.parts.append("# ")
            elif tag == "li":
                self.parts.append("- ")

    def handle_endtag(self, tag):
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "a":
            self._flush_link()
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth or not data.strip():
            return
        chunk = " ".join(data.split())
        if self._href is not None:
            self._link_text.append(chunk)
        else:
            self.parts.append(chunk + " ")

    def _flush_link(self):
        if self._href is None:
            return
        text = " ".join(self._link_text).strip()
        href = self._href.strip()
        if href and not href.startswith(("javascript:", "#")):
            self.parts.append(f"[{text}]({href}) ")
        elif text:
            self.parts.append(text + " ")
        self._href = None
        self._link_text = []

    def text(self) -> str:
        self._flush_link()
        joined = "".join(self.parts)
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r" ?\n ?", "\n", joined)
        joined = re.sub(r"\n{2,}", "\n", joined)
        return joined.strip()


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # malformed HTML — keep whatever was parsed so far
        pass
    return parser.text()


def fetch_page(url: str, timeout: int = 12, max_bytes: int = 400_000) -> str | None:
    """Fetch one URL and return readable text, or None on any failure.

    A crawler survives anything: bad DNS, timeouts, non-HTML content, off-host
    redirects, and decode errors all collapse to None.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        body, content_type, charset = _http_get(url, timeout, max_bytes)
    except Exception as exc:  # network/HTTP/redirect — expected for a crawler
        logger.debug("fetch_page failed for %s: %s", url, exc)
        return None
    if content_type and "html" not in content_type:
        return None
    try:
        html = body.decode(charset, errors="replace")
    except LookupError:
        html = body.decode("utf-8", errors="replace")
    return _html_to_text(html) or None


# ── Grant-link finder (deterministic, no LLM) ────────────────────────────────

_LINK_MD_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
_GRANTISH_RE = re.compile(
    r"grant|funding|apply|application|\brfps?\b|letter[\s_-]*of[\s_-]*inquiry"
    r"|\bloi\b|guidelines|scholarship",
    re.I,
)


def find_grant_links(page_text: str, base_url: str, limit: int = 3) -> list[str]:
    """Surface up to `limit` same-host links whose text/href suggests grant
    programs. Operates on `fetch_page` output (links as ``[text](href)``)."""
    base_host = _host(base_url)
    base_normalized = base_url.split("#", 1)[0].rstrip("/")
    seen: set[str] = set()
    found: list[str] = []
    for text, href in _LINK_MD_RE.findall(page_text or ""):
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href).split("#", 1)[0]
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if _host(absolute) != base_host:
            continue
        if parsed.path.lower().endswith(_SKIP_EXTENSIONS):
            continue
        normalized = absolute.rstrip("/")
        if normalized in seen or normalized == base_normalized:
            continue
        if not (_GRANTISH_RE.search(text) or _GRANTISH_RE.search(parsed.path)):
            continue
        seen.add(normalized)
        found.append(absolute)
        if len(found) >= limit:
            break
    return found


# ── Deadline parsing (stdlib, unambiguous formats only) ─────────────────────

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}
_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MDY_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_MONTH_DAY_YEAR_RE = re.compile(
    r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_DAY_MONTH_YEAR_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")


def _month_number(name: str) -> int | None:
    n = name.lower().rstrip(".")
    if n in _MONTHS:
        return _MONTHS[n]
    if len(n) >= 3:
        for full, i in _MONTHS.items():
            if full.startswith(n):
                return i
    return None


def parse_deadline_text(text: str | None) -> date | None:
    """Parse a deadline string to a date when unambiguous; else None.

    Handles ISO (2026-03-15), US numeric (03/15/2026), "March 15, 2026" (with
    ordinals), and "15 March 2026". "Rolling", "quarterly", etc. → None.
    """
    if not text or not text.strip():
        return None
    t = text.strip()
    try:
        if m := _ISO_RE.search(t):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if m := _MDY_RE.search(t):
            return date(int(m[3]), int(m[1]), int(m[2]))
        if m := _MONTH_DAY_YEAR_RE.search(t):
            month = _month_number(m[1])
            return date(int(m[3]), month, int(m[2])) if month else None
        if m := _DAY_MONTH_YEAR_RE.search(t):
            month = _month_number(m[2])
            return date(int(m[3]), month, int(m[1])) if month else None
    except ValueError:  # e.g. "February 30, 2026" — not a real date
        return None
    return None


# ── LLM extraction (structures fetched text — never generates facts) ────────

class ExtractedProgram(BaseModel):
    title: str = Field(description="Grant program title exactly as written on the page.")
    description: str = Field(
        default="", description="What the page says about this program, max 400 chars.")
    deadline_text: str = Field(
        default="", description="Deadline exactly as written on the page; empty if none stated.")
    amount_text: str = Field(
        default="", description="Award amount exactly as written; empty if none stated.")
    eligibility_text: str = Field(
        default="", description="Eligibility exactly as written; empty if none stated.")
    confidence: Literal["high", "medium", "low"] = "medium"


class ProgramList(BaseModel):
    programs: list[ExtractedProgram] = Field(default_factory=list)


_EXTRACTION_SYSTEM_PROMPT = """\
You extract structured grant-program data from fetched web page text for Anansi Atlas.

Extract ONLY grant programs, application processes, or funding opportunities \
EXPLICITLY described in the provided page text. If the page describes none, \
return an empty list. Never infer, never use outside knowledge, never invent \
deadlines or amounts — omit fields not present in the text. Quote titles as \
written on the page.

The organization context you may receive is for judging relevance only — it is \
NEVER a source of facts about the funder or its programs."""


def _require_llm() -> None:
    """Raise WebDiscoveryLLMUnavailable unless SiteConfig has a usable LLM."""
    from openoutreach.core.llm import get_llm_model
    try:
        get_llm_model()
    except (ValueError, ImportError) as exc:
        raise WebDiscoveryLLMUnavailable(str(exc)) from exc


def extract_grant_programs(page_text: str, page_url: str, org_profile: str) -> list[dict]:
    """THE LLM step: structure grant programs explicitly described in `page_text`.

    Returns dicts of {title, description, deadline(date|None), deadline_text,
    amount_text, eligibility_text, confidence, source_url}. `source_url` is
    always `page_url` — the output schema has no URL field, so the LLM cannot
    supply one; any URL-ish attribute it smuggles in is never read.

    Raises WebDiscoveryLLMUnavailable when SiteConfig has no usable LLM.
    """
    if not page_text or not page_text.strip():
        return []

    _require_llm()
    from pydantic_ai import Agent

    from openoutreach.core.llm import get_llm_model, run_agent_sync

    agent = Agent(
        get_llm_model(),
        system_prompt=_EXTRACTION_SYSTEM_PROMPT,
        output_type=ProgramList,
        model_settings={"temperature": 0, "timeout": 90},
    )
    prompt = (
        f"PAGE URL (for reference only): {page_url}\n\n"
        f"ORGANIZATION CONTEXT (relevance only, never a source of facts):\n"
        f"{org_profile.strip() or '(none)'}\n\n"
        f"PAGE TEXT (the only permitted source of facts):\n"
        f"{page_text[:_MAX_PROMPT_CHARS]}"
    )
    output = run_agent_sync(agent.run(prompt)).output

    programs: list[dict] = []
    for p in getattr(output, "programs", None) or []:
        title = (getattr(p, "title", "") or "").strip()
        if not title:
            continue
        description = (getattr(p, "description", "") or "").strip()[:400]
        deadline_text = (getattr(p, "deadline_text", "") or "").strip()
        deadline = parse_deadline_text(deadline_text)
        if deadline_text and deadline is None:
            # Ambiguous ("rolling", "quarterly") — keep the text, not a guess.
            suffix = f" Deadline: {deadline_text}"
            if deadline_text.lower() not in description.lower():
                description = (description + suffix).strip()
        confidence = str(getattr(p, "confidence", "") or "").lower()
        programs.append({
            "title": title,
            "description": description,
            "deadline": deadline,
            "deadline_text": deadline_text,
            "amount_text": (getattr(p, "amount_text", "") or "").strip(),
            "eligibility_text": (getattr(p, "eligibility_text", "") or "").strip(),
            "confidence": confidence if confidence in ("high", "medium", "low") else "medium",
            "source_url": page_url,  # the fetched page — never an LLM-produced URL
        })
    return programs


# ── Orchestrator ─────────────────────────────────────────────────────────────

@dataclass
class DiscoveryReport:
    funders_scanned: int = 0
    pages_fetched: int = 0
    programs_extracted: int = 0
    saved: int = 0
    rejected: int = 0
    skipped_llm_unavailable: bool = False
    lines: list[str] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)


_VERIFICATION_RANK = {
    Funder.VerificationStatus.VERIFIED: 3,
    Funder.VerificationStatus.REVIEWED: 2,
    Funder.VerificationStatus.NEEDS_REVIEW: 1,
    Funder.VerificationStatus.UNVERIFIED: 0,
}


def _funder_homepage(funder) -> str | None:
    """First usable http(s) URL for a funder — website, then source_urls.
    Reserved placeholder domains (the hallucination signature) are never usable.

    Checked against the bare host, not the full URL: the grounding regex only
    matches a reserved name at string start or after a dot, so a full URL like
    ``https://example.org`` (no ``www.``) would otherwise slip through.
    """
    for candidate in [funder.website, *(funder.source_urls or [])]:
        candidate = (candidate or "").strip()
        if candidate.startswith(("http://", "https://")) and not is_reserved_domain(_host(candidate)):
            return candidate
    return None


def _candidate_funders(project, max_funders: int) -> list:
    """Active funders with a usable homepage, preferring verified/reviewed rows
    and focus-area overlap with the project's organization."""
    org = getattr(project, "organization", None)
    org_focus = {
        str(f).strip().lower()
        for f in (getattr(org, "focus_areas", None) or []) if str(f).strip()
    }
    scored = []
    for funder in Funder.objects.filter(active=True):
        if not _funder_homepage(funder):
            continue
        funder_focus = {
            str(f).strip().lower() for f in (funder.focus_areas or []) if str(f).strip()
        }
        overlap = len(org_focus & funder_focus)
        rank = _VERIFICATION_RANK.get(funder.verification_status, 0)
        scored.append((-overlap, -rank, funder.name.lower(), funder))
    scored.sort(key=lambda item: item[:3])
    return [item[3] for item in scored[:max_funders]]


def _org_profile(project) -> str:
    org = getattr(project, "organization", None)
    if org is None:
        return getattr(project, "name", "") or ""
    parts = [f"Organization: {org.name}"]
    if getattr(org, "mission", ""):
        parts.append(f"Mission: {org.mission}")
    focus = [str(f) for f in (getattr(org, "focus_areas", None) or []) if str(f).strip()]
    if focus:
        parts.append("Focus areas: " + ", ".join(focus))
    home = ", ".join(p for p in [getattr(org, "city", ""), getattr(org, "state", "")] if p)
    if home:
        parts.append(f"Location: {home}")
    return "\n".join(parts)


def _candidate_from_program(program: dict, funder, page_url: str) -> dict:
    """Build a grounding-gate candidate. `page_url` is the URL this process
    fetched — passed explicitly so not even a buggy extractor can change it.

    external_id hashes url+title (not url alone) so multiple programs described
    on one page each keep a stable, non-colliding identity across re-runs.
    """
    title = program["title"]
    notes = [program.get("description") or ""]
    if program.get("amount_text"):
        notes.append(f"Amount: {program['amount_text']}")
    if program.get("eligibility_text"):
        notes.append(f"Eligibility: {program['eligibility_text']}")
    notes.append(f"Extraction confidence: {program.get('confidence', 'medium')}.")
    digest = hashlib.sha1(f"{page_url}|{title.lower()}".encode()).hexdigest()[:12]
    return {
        "name": title,
        "source_url": page_url,
        "source_name": funder.name,
        "deadline": program.get("deadline"),
        "description": " | ".join(part.strip() for part in notes if part.strip()),
        "external_id": f"webdiscovery:{digest}",
    }


def discover_for_project(
    project,
    funders=None,
    max_funders: int = 15,
    max_pages_per_funder: int = 3,
    dry_run: bool = False,
) -> DiscoveryReport:
    """Scan funder websites for grant programs and persist them through the
    grounding gate. Never crashes on an unreachable site or a missing LLM —
    the report says exactly what happened.
    """
    report = DiscoveryReport()
    try:
        _require_llm()  # probe before fetching anything — no LLM, no extraction
    except WebDiscoveryLLMUnavailable as exc:
        report.skipped_llm_unavailable = True
        report.lines.append(f"LLM unavailable — web discovery skipped: {exc}")
        return report

    funder_list = list(funders) if funders is not None else _candidate_funders(project, max_funders)
    funder_list = funder_list[:max_funders]
    org_profile = _org_profile(project)
    candidates: list[dict] = []
    llm_down = False

    for funder in funder_list:
        if llm_down:
            break
        homepage = _funder_homepage(funder)
        if not homepage:
            report.lines.append(f"{funder.name}: no usable website — skipped")
            continue
        report.funders_scanned += 1
        home_text = fetch_page(homepage)
        if home_text is None:
            report.lines.append(f"{funder.name}: homepage unreachable ({homepage})")
            continue
        report.pages_fetched += 1

        pages = []
        for link in find_grant_links(home_text, homepage, limit=max_pages_per_funder):
            text = fetch_page(link)
            if text is not None:
                report.pages_fetched += 1
                pages.append((link, text))
        if not pages:
            # Single-page foundation sites describe grants on the homepage.
            pages = [(homepage, home_text)]

        extracted_here = 0
        for page_url, page_text in pages:
            try:
                programs = extract_grant_programs(page_text, page_url, org_profile)
            except WebDiscoveryLLMUnavailable as exc:
                report.skipped_llm_unavailable = True
                report.lines.append(f"LLM became unavailable mid-run: {exc}")
                llm_down = True
                break
            except Exception as exc:  # provider hiccup — skip the page, keep crawling
                logger.warning("Extraction failed for %s: %s", page_url, exc)
                report.lines.append(f"{funder.name}: extraction failed for {page_url}: {exc}")
                continue
            extracted_here += len(programs)
            for program in programs:
                candidates.append(_candidate_from_program(program, funder, page_url))
        report.programs_extracted += extracted_here
        report.lines.append(
            f"{funder.name}: {len(pages)} page(s), {extracted_here} program(s)"
        )

    report.candidates = candidates
    if dry_run or not candidates:
        return report

    result = ingest_verified_opportunities(
        project,
        candidates,
        source_type=Opportunity.SourceType.FUNDER,
        opportunity_type=Opportunity.OpportunityType.GRANT,
    )
    report.saved = result["saved"]
    report.rejected = result["rejected"]
    if result["rejected_names"]:
        report.lines.append("Gate rejected: " + ", ".join(result["rejected_names"]))
    return report
