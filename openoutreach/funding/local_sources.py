"""State, county and city funding sources — the layer Grants.gov cannot see.

Grants.gov is federal-only. The money a small community nonprofit is most likely
to win is administered one or two levels down: a state pass-through like Florida
DOE's 21st Century Community Learning Centers, a county commission's mini-grants,
a city's community investment program. None of it is posted federally and none of
it has an API, so this module works the way `web_discovery` does — fetch the real
page, extract only what that page says, and persist through the grounding gate.

Two things make this different from foundation discovery:

1. **The seed list is curated, not derived.** Foundation discovery starts from the
   Funder table. There is no equivalent table of government grant portals, and
   `find_grant_links` is useless on a municipal site — it scrapes the global
   navigation and returns parking permits. So sources are registered explicitly
   below, each one a URL that was fetched and confirmed to serve a grant page.

2. **It degrades honestly without an LLM.** `extract_grant_programs` needs a key in
   SiteConfig. When one is present we extract individual programs; when it isn't we
   still record the program page itself — a real, reachable, correctly-attributed
   funding page — rather than silently producing nothing. Either way the row lands
   as `needs_review`, because the gate verifies the URL is real, not that the
   opportunity fits.

Sources are matched to an organization by geography, so registering Georgia or
Texas sources later needs no code change here.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from openoutreach.funding.grounding import ingest_verified_opportunities
from openoutreach.funding.models import Opportunity
from openoutreach.funding.web_discovery import (
    WebDiscoveryLLMUnavailable,
    extract_grant_programs,
    fetch_page,
)

logger = logging.getLogger(__name__)

STATE = "state"
COUNTY = "county"
CITY = "city"


@dataclass(frozen=True)
class LocalSource:
    """One government funding page, scoped to who it applies to.

    `url` must be a page that has actually been fetched — see the module test,
    which fails if a registered URL stops serving a page. `blocked` records a
    source we know exists and cannot currently reach, so the gap is visible in
    the code and in the command output instead of being silently absent.
    """

    key: str
    name: str
    level: str
    url: str
    state: str
    county: str = ""
    city: str = ""
    focus: str = ""
    blocked: str = ""
    notes: str = ""

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocked)


LOCAL_SOURCES: list[LocalSource] = [
    # ---- Florida — state -----------------------------------------------------
    LocalSource(
        key="fl-doe-21cclc",
        name="Florida DOE — 21st Century Community Learning Centers",
        level=STATE,
        url="https://www.fldoe.org/schools/family-community/activities-programs/21st-century-community-learning-center/",
        state="Florida",
        focus="after-school and out-of-school-time academic enrichment",
        # fldoe.org robots.txt is "Disallow:" — crawling is explicitly permitted —
        # but the edge WAF returns 403 to every non-browser client regardless of
        # User-Agent. Not a UA problem and not fixable from urllib; it needs a real
        # browser engine in the ingest path. Registered anyway so the single most
        # relevant state program for an after-school provider is visible as a known
        # gap rather than quietly missing.
        blocked="WAF returns 403 to all non-browser HTTP clients (robots.txt permits crawling)",
        notes="21st CCLC is the flagship out-of-school-time pass-through. 2026-27 RFP closed 2026-05-11.",
    ),
    # ---- Florida — Orange County --------------------------------------------
    LocalSource(
        key="occ-ccc-grants",
        name="Orange County Citizens' Commission for Children — Grant Funding",
        level=COUNTY,
        url="https://www.orangecountyfl.net/familieshealthsocialsvcs/CitizensCommissionforChildren/grantfunding.aspx",
        state="Florida",
        county="Orange",
        focus="children, youth and family services",
    ),
    LocalSource(
        key="occ-neighborhood-grants",
        name="Orange County — Neighborhood Grants",
        level=COUNTY,
        url="https://www.orangecountyfl.net/NeighborsHousing/NeighborhoodRevitalization/NeighborhoodGrants.aspx",
        state="Florida",
        county="Orange",
        focus="neighborhood safety, health and connection projects",
    ),
    # ---- Florida — City of Orlando ------------------------------------------
    LocalSource(
        key="orlando-community-investment",
        name="City of Orlando — Community Investment Program",
        level=CITY,
        url="https://www.orlando.gov/Our-Government/Get-Involved/Non-Profits-and-Community-Organizations/Community-Investment-Grant",
        state="Florida",
        county="Orange",
        city="Orlando",
        focus="services to residents inside Orlando city limits",
    ),
    LocalSource(
        key="orlando-nonprofit-hub",
        name="City of Orlando — For Non-Profits and Community Organizations",
        level=CITY,
        url="https://www.orlando.gov/Our-Government/Get-Involved/Non-Profits-and-Community-Organizations",
        state="Florida",
        county="Orange",
        city="Orlando",
        focus="city programs open to nonprofit organizations",
    ),
]


def _norm(value: str) -> str:
    return (value or "").strip().casefold()


def sources_for_organization(organization, *, include_blocked: bool = False) -> list[LocalSource]:
    """Sources whose jurisdiction contains this organization.

    State sources apply to any org in that state; county sources need the county
    to match; city sources need the city. An org that has not told us its county
    still gets state-level sources rather than nothing.
    """
    state, county, city = (
        _norm(getattr(organization, "state", "")),
        _norm(getattr(organization, "county", "")),
        _norm(getattr(organization, "city", "")),
    )
    if not state:
        return []
    matched = []
    for source in LOCAL_SOURCES:
        if _norm(source.state) != state:
            continue
        if source.level == COUNTY and _norm(source.county) != county:
            continue
        if source.level == CITY and _norm(source.city) != city:
            continue
        if source.is_blocked and not include_blocked:
            continue
        matched.append(source)
    return matched


def _org_profile(project) -> str:
    org = project.organization
    parts = [org.name, org.mission or ""]
    if org.focus_areas:
        parts.append("Focus areas: " + ", ".join(str(a) for a in org.focus_areas))
    if org.beneficiaries:
        parts.append("Serves: " + ", ".join(str(b) for b in org.beneficiaries))
    return " | ".join(p for p in parts if p)[:1200]


def _candidate_id(url: str, title: str) -> str:
    digest = hashlib.sha1(f"{url}|{title.lower()}".encode()).hexdigest()[:12]
    return f"localgov:{digest}"


def _page_level_candidate(source: LocalSource, page_text: str) -> dict:
    """The no-LLM fallback: the program page itself, as one opportunity.

    Deliberately carries no deadline. A date scraped off a 90,000-character
    municipal page is as likely to be a council meeting as an application
    deadline, and a wrong deadline on a client's board is worse than none.
    """
    return {
        "name": source.name,
        "source_url": source.url,
        "source_name": source.name.split(" — ")[0],
        "deadline": None,
        "description": (
            f"{source.level.title()}-level funding source"
            + (f" for {source.focus}" if source.focus else "")
            + ". Page fetched and confirmed live; individual programs, deadlines and "
            "amounts are on the source page and still need to be read and confirmed. "
            "(Recorded without program-level extraction because no LLM is configured "
            "in Site Configuration.)"
        ),
        "external_id": _candidate_id(source.url, source.name),
    }


def _program_candidates(source: LocalSource, programs: list[dict]) -> list[dict]:
    candidates = []
    for program in programs:
        title = (program.get("title") or "").strip()
        if not title:
            continue
        notes = [program.get("description") or ""]
        if program.get("amount_text"):
            notes.append(f"Amount: {program['amount_text']}")
        if program.get("eligibility_text"):
            notes.append(f"Eligibility: {program['eligibility_text']}")
        if program.get("deadline_text"):
            notes.append(f"Deadline as written: {program['deadline_text']}")
        notes.append(f"Source: {source.name}.")
        candidates.append({
            "name": title,
            "source_url": source.url,
            "source_name": source.name.split(" — ")[0],
            "deadline": program.get("deadline"),
            "description": " | ".join(n.strip() for n in notes if n.strip()),
            "external_id": _candidate_id(source.url, title),
        })
    return candidates


@dataclass
class LocalDiscoveryReport:
    matched: int = 0
    fetched: int = 0
    unreachable: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    saved: int = 0
    rejected: int = 0
    rejected_names: list[str] = field(default_factory=list)
    extraction: str = "none"   # "programs" | "page-level" | "none"
    candidates: list[dict] = field(default_factory=list)


def discover_local_for_project(project, *, dry_run: bool = False,
                               sources: list[LocalSource] | None = None) -> LocalDiscoveryReport:
    """Fetch this organization's state/county/city funding pages and persist what they say."""
    organization = project.organization
    selected = sources if sources is not None else sources_for_organization(organization)
    report = LocalDiscoveryReport(matched=len(selected))

    for blocked_source in sources_for_organization(organization, include_blocked=True):
        if blocked_source.is_blocked:
            report.blocked.append(f"{blocked_source.name} — {blocked_source.blocked}")

    use_llm = True
    profile = _org_profile(project)
    candidates: list[dict] = []

    for source in selected:
        if source.is_blocked:
            continue
        page_text = fetch_page(source.url)
        if not page_text:
            report.unreachable.append(f"{source.name} ({source.url})")
            continue
        report.fetched += 1

        if use_llm:
            try:
                programs = extract_grant_programs(page_text, source.url, profile)
                found = _program_candidates(source, programs)
                if found:
                    candidates.extend(found)
                    report.extraction = "programs"
                    continue
                # LLM ran and found nothing it could quote — record the page so the
                # source is still on the board rather than vanishing.
                candidates.append(_page_level_candidate(source, page_text))
                report.extraction = report.extraction or "page-level"
                continue
            except WebDiscoveryLLMUnavailable:
                use_llm = False
                logger.info("No LLM configured — falling back to page-level local sources.")

        candidates.append(_page_level_candidate(source, page_text))
        if report.extraction != "programs":
            report.extraction = "page-level"

    report.candidates = candidates
    if dry_run or not candidates:
        return report

    summary = ingest_verified_opportunities(
        project,
        candidates,
        source_type=Opportunity.SourceType.GOVERNMENT,
    )
    report.saved = summary.get("saved", 0)
    report.rejected = summary.get("rejected", 0)
    report.rejected_names = summary.get("rejected_names", [])
    return report
