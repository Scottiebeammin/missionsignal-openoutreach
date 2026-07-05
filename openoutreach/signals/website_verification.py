"""
Website verification: check the claims in an organization's profile against
what its live website actually says.

Deterministic and explainable — no LLM. The site text (via website_scraper,
scanned deeper than the analyzer's enrichment cap) is searched for each claimed
program and area of support; anything not found is surfaced to the client
("Program X isn't visible on your website"), so profile and site stay in sync.
A claim counts as found when its full phrase appears, or when every significant
word of it does.
"""
import re

from django.utils import timezone

from openoutreach.signals.website_scraper import scrape_website_text

_STOPWORDS = {
    "and", "or", "the", "for", "of", "to", "in", "with", "our", "your",
    "program", "programs", "services", "service", "support", "initiative",
}
_SCAN_CHARS = 40_000  # deeper than the analyzer's 8k enrichment cap


def _significant_words(claim: str) -> list[str]:
    words = re.split(r"[^a-z0-9]+", claim.casefold())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


def _claim_found(claim: str, text: str) -> bool:
    phrase = " ".join(claim.casefold().split())
    if phrase and phrase in text:
        return True
    words = _significant_words(claim)
    return bool(words) and all(w in text for w in words)


def collect_claims(organization, project) -> list[dict]:
    """The profile statements worth checking: program names + areas of support."""
    claims = []
    for entry in (project.program_summaries or []):
        name = (entry.get("name") or "").strip() if isinstance(entry, dict) else str(entry).strip()
        if name:
            claims.append({"claim": name, "kind": "program"})
    if not claims and project.programs:
        for part in re.split(r"[·,;\n]", project.programs):
            if part.strip():
                claims.append({"claim": part.strip(), "kind": "program"})
    for area in (organization.focus_areas or []):
        claims.append({"claim": area, "kind": "focus area"})
    return claims


def verify_website_claims(organization, project) -> dict:
    """Scan the org website, compare against profile claims, persist the report.

    Report shape: {checked_at, url, status: ok|no_website|unreachable,
    found: [{claim, kind}], missing: [{claim, kind}]}.
    """
    checked_at = timezone.now().isoformat()
    url = organization.website
    if not url:
        report = {"checked_at": checked_at, "url": "", "status": "no_website", "found": [], "missing": []}
    else:
        text = " ".join(scrape_website_text(url, max_chars=_SCAN_CHARS).casefold().split())
        if not text:
            report = {"checked_at": checked_at, "url": url, "status": "unreachable", "found": [], "missing": []}
        else:
            found, missing = [], []
            for claim in collect_claims(organization, project):
                (found if _claim_found(claim["claim"], text) else missing).append(claim)
            report = {"checked_at": checked_at, "url": url, "status": "ok", "found": found, "missing": missing}
    organization.website_check = report
    organization.save(update_fields=["website_check"])
    return report
