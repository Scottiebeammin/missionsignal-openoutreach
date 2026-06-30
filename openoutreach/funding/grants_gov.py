"""Live federal-grant ingestion from the public Grants.gov Search2 API.

No API key, no paid dependency — just the authoritative federal source. Every
opportunity it creates carries a real grants.gov detail URL and real close date,
so nothing here can be a hallucination. Foundation/private grants are a separate
(grounded-research) track; this module is federal-only.
"""
import json
import logging
import urllib.request
from datetime import date, datetime

from django.utils import timezone

from openoutreach.funding.exceptions import GrantsGovError
from openoutreach.funding.models import Opportunity

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.grants.gov/v1/api/search2"
DETAIL_URL = "https://www.grants.gov/search-results-detail/{id}"
_UA = "Mozilla/5.0 (compatible; AnansiAtlasGrantsPull/1.0)"


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
                    "status": status,
                    "source_urls": [n["url"]],
                    "source_references": [
                        {"system": "grants.gov", "id": n["gid"], "number": n["number"]}
                    ],
                    "source_notes": f"Pulled live from Grants.gov (keyword: {kw}).",
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
