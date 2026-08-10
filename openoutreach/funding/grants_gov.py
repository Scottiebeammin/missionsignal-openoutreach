"""Live federal-grant ingestion from the public Grants.gov Search2 API.

No API key, no paid dependency — just the authoritative federal source. Every
opportunity it creates carries a real grants.gov detail URL and real close date,
so nothing here can be a hallucination. Foundation/private grants are a separate
(grounded-research) track; this module is federal-only.
"""
import html
import json
import logging
import re
import urllib.request
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from openoutreach.funding.exceptions import GrantsGovError
from openoutreach.funding.models import Opportunity

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.grants.gov/v1/api/search2"
FETCH_URL = "https://api.grants.gov/v1/api/fetchOpportunity"
DETAIL_URL = "https://www.grants.gov/search-results-detail/{id}"
_UA = "Mozilla/5.0 (compatible; AnansiAtlasGrantsPull/1.0)"

# Canonical US state names (plus DC/PR) — used to detect state-scoped federal
# grants from opportunity titles, and by signals.matching to recognize
# state-restricted geography lists.
US_STATES = frozenset({
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
    "District of Columbia", "Puerto Rico",
})


def search_grants(keyword: str, *, rows: int = 25, statuses: str = "forecasted|posted") -> list[dict]:
    """Query the Grants.gov Search2 API for one keyword. Returns raw opportunity hits."""
    payload = json.dumps({"keyword": keyword, "rows": rows, "oppStatuses": statuses}).encode()
    req = urllib.request.Request(
        SEARCH_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": _UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.load(resp)
    except Exception as exc:  # network / parse — expected, recoverable per-keyword
        raise GrantsGovError(f"Grants.gov request failed for '{keyword}': {exc}") from exc
    if data.get("errorcode") != 0:
        raise GrantsGovError(f"Grants.gov error for '{keyword}': {data.get('msg')}")
    return data.get("data", {}).get("oppHits", [])


def fetch_opportunity_details(gid: str) -> dict:
    """Fetch one opportunity's detail record (fetchOpportunity endpoint).

    Returns the synopsis (or forecast, for forecasted opportunities) dict — the
    part that carries `applicantTypes` and `applicantEligibilityDesc`. Returns
    {} on any failure: detail enrichment is best-effort, never fatal.
    """
    payload = json.dumps({"opportunityId": gid}).encode()
    req = urllib.request.Request(
        FETCH_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": _UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.load(resp)
    except Exception as exc:  # network / parse — expected, recoverable per-opportunity
        logger.warning("Grants.gov fetchOpportunity failed for %s: %s", gid, exc)
        return {}
    record = data.get("data") or {}
    return record.get("synopsis") or record.get("forecast") or {}


def normalize_applicant_types(raw) -> list[dict]:
    """Normalize fetchOpportunity applicantTypes to [{"id","description"}, ...]."""
    normalized = []
    for entry in raw or []:
        if isinstance(entry, dict):
            aid = str(entry.get("id", "")).strip()
            desc = str(entry.get("description", "")).strip()
            if aid or desc:
                normalized.append({"id": aid, "description": desc})
        elif str(entry).strip():
            normalized.append({"id": "", "description": str(entry).strip()})
    return normalized


def _parse_money(value) -> Decimal | None:
    """Grants.gov returns award figures as digit strings ("300000"). Return a
    Decimal, or None for missing/unparseable values — never raise, since a
    malformed amount must not cost us the whole opportunity."""
    if value in (None, "", "0"):
        return None
    try:
        amount = Decimal(str(value).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return amount if amount > 0 else None


def award_figures(details: dict) -> dict:
    """Pull the money fields off a fetchOpportunity synopsis.

    These ride along on the detail call we already make for applicantTypes, so
    capturing them costs no extra request. `amount` is the per-award ceiling —
    what one applicant could receive — falling back to the floor when a program
    publishes only a minimum. `estimated_funding` is the whole program's pot and
    is deliberately kept separate: summing program totals across opportunities
    would wildly overstate what any single organization could win.
    """
    ceiling = _parse_money(details.get("awardCeiling"))
    floor = _parse_money(details.get("awardFloor"))
    try:
        awards = int(str(details.get("numberOfAwards") or "").strip() or 0) or None
    except ValueError:
        awards = None
    return {
        "amount": ceiling or floor,
        "ceiling": ceiling,
        "floor": floor,
        "estimated_funding": _parse_money(details.get("estimatedFunding")),
        "number_of_awards": awards,
    }


def describe_award(figures: dict) -> str:
    """One human-readable clause for source_notes, or "" when nothing is known."""
    parts = []
    ceiling, floor = figures.get("ceiling"), figures.get("floor")
    if ceiling and floor and ceiling != floor:
        parts.append(f"Award range ${floor:,.0f}-${ceiling:,.0f}")
    elif ceiling or floor:
        parts.append(f"Award up to ${(ceiling or floor):,.0f}")
    if figures.get("estimated_funding"):
        parts.append(f"estimated program funding ${figures['estimated_funding']:,.0f}")
    if figures.get("number_of_awards"):
        parts.append(f"{figures['number_of_awards']} awards expected")
    return "; ".join(parts)


def detect_states(text: str) -> list[str]:
    """Return canonical US state names mentioned (whole-word) in text."""
    cleaned = html.unescape(text or "")
    return sorted(
        state for state in US_STATES
        if re.search(rf"\b{re.escape(state)}\b", cleaned, flags=re.IGNORECASE)
    )


def geography_for_hit(title: str) -> list[str]:
    """Honest geography for a federal grant: state-scoped if the title names
    specific states (e.g. "FY26 Florida Coastal Program"), else National —
    federal grants are nationally eligible unless restricted."""
    states = detect_states(title)
    return states if states else ["National"]


def _parse_date(value: str):
    """Grants.gov returns MM/DD/YYYY. Return a date or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def normalize_hit(hit: dict) -> dict:
    gid = str(hit.get("id", "")).strip()
    return {
        "external_id": f"grants.gov:{gid}",
        "gid": gid,
        "name": (hit.get("title") or "").strip(),
        "agency": (hit.get("agency") or hit.get("agencyCode") or "").strip(),
        "number": (hit.get("number") or "").strip(),
        "posted_date": _parse_date(hit.get("openDate")),
        "deadline": _parse_date(hit.get("closeDate")),
        "url": DETAIL_URL.format(id=gid) if gid else "",
    }


def keywords_for_project(project) -> list[str]:
    """Derive search keywords from the org's focus areas; fall back to its name."""
    org = getattr(project, "organization", None)
    focus = list(getattr(org, "focus_areas", []) or []) if org else []
    keywords = [str(k).strip() for k in focus if str(k).strip()]
    if not keywords and org and org.name:
        keywords = [org.name]
    return keywords


def ingest_grants_for_project(
    project, keywords: list[str] | None = None, *, rows_per_keyword: int = 25, dry_run: bool = False
) -> dict:
    """Pull live federal grants matching the project's focus areas into Opportunities.

    Deduped on external_id, so re-running refreshes existing rows instead of
    duplicating. Returns a summary dict.
    """
    keywords = keywords or keywords_for_project(project)
    if not keywords:
        return {"created": 0, "updated": 0, "skipped": 0, "keywords": [], "errors": ["no keywords"]}

    today = date.today()
    seen: set[str] = set()
    created = updated = skipped = 0
    errors: list[str] = []

    for kw in keywords:
        try:
            hits = search_grants(kw, rows=rows_per_keyword)
        except GrantsGovError as exc:
            logger.warning("%s", exc)
            errors.append(str(exc))
            continue

        for hit in hits:
            n = normalize_hit(hit)
            if not n["name"] or not n["gid"] or n["external_id"] in seen:
                skipped += 1
                continue
            seen.add(n["external_id"])

            status = (
                Opportunity.Status.EXPIRED
                if n["deadline"] and n["deadline"] < today
                else Opportunity.Status.ACTIVE
            )
            if dry_run:
                created += 1
                continue

            details = fetch_opportunity_details(n["gid"])
            applicant_types = normalize_applicant_types(details.get("applicantTypes"))
            eligibility_notes = (details.get("applicantEligibilityDesc") or "").strip()[:4000]
            figures = award_figures(details)
            award_note = describe_award(figures)
            source_notes = f"Pulled live from Grants.gov (keyword: {kw})."
            if award_note:
                source_notes = f"{source_notes} {award_note}."

            _, was_created = Opportunity.objects.update_or_create(
                project=project,
                external_id=n["external_id"],
                defaults={
                    "name": n["name"][:500],
                    "opportunity_type": Opportunity.OpportunityType.GRANT,
                    "source_type": Opportunity.SourceType.GOVERNMENT,
                    "source_name": n["agency"][:500],
                    "posted_date": n["posted_date"],
                    "deadline": n["deadline"],
                    "geography": geography_for_hit(n["name"]),
                    "applicant_types": applicant_types,
                    "eligibility_notes": eligibility_notes,
                    "funding_amount": figures["amount"],
                    "status": status,
                    "source_urls": [n["url"]],
                    "source_references": [
                        {
                            "system": "grants.gov",
                            "id": n["gid"],
                            "number": n["number"],
                            "award_ceiling": str(figures["ceiling"]) if figures["ceiling"] else "",
                            "award_floor": str(figures["floor"]) if figures["floor"] else "",
                            "estimated_funding": (
                                str(figures["estimated_funding"]) if figures["estimated_funding"] else ""
                            ),
                            "number_of_awards": figures["number_of_awards"] or "",
                        }
                    ],
                    "source_notes": source_notes,
                    "verification_status": Opportunity.VerificationStatus.VERIFIED,
                    "last_reviewed_at": timezone.now(),
                },
            )
            created += was_created
            updated += not was_created

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "keywords": keywords,
        "errors": errors,
    }
