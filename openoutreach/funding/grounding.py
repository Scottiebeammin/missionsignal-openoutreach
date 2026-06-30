"""The grounding gate — every researched opportunity must trace to a real URL.

Federal grants come from an authoritative API (`grants_gov.py`) and need no gate.
Everything else — state/local government, corporate giving pages, foundation
sites, social announcements — arrives via grounded web research and is only as
trustworthy as its source. This module is the single chokepoint that decides
whether a researched opportunity is allowed to be saved:

  REJECT   – no source URL, or a URL on an RFC-2606 reserved placeholder domain
             (example.com / .test / .invalid / .localhost). This is the
             hallucination signature (the `.example.org` funders we found).
  REVIEW   – has a real-looking URL that didn't respond to an automated check
             (many gov/corporate sites hard-block bots, so we don't drop these —
             we save them flagged for a human to confirm).
  VERIFIED – has a real URL that responded.

Nothing reaches the Opportunity table without passing through `ingest_verified_opportunities`.
"""
import re
import urllib.error
import urllib.request

from django.utils import timezone

from openoutreach.funding.models import Opportunity

# RFC 2606 / 6761 reserved domains — can never be a real funder/opportunity site.
_RESERVED_RE = re.compile(
    r"(^|\.)(example\.(com|org|net)|example|test|invalid|localhost)(\.|/|$)", re.I
)
_UA = "Mozilla/5.0 (compatible; AnansiAtlasGrounding/1.0)"

# Outcomes
REJECTED = "rejected"   # no URL or reserved/fake domain → never saved
REVIEW = "review"       # real-looking URL, unreachable → save as needs_review
VERIFIED = "verified"   # real URL that responded


def is_reserved_domain(url: str) -> bool:
    return bool(url) and bool(_RESERVED_RE.search(url))


def is_reachable(url: str, timeout: int = 8) -> bool:
    """True if the URL responds with a non-error status. HEAD, then GET fallback."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status < 400
        except urllib.error.HTTPError as e:
            if method == "HEAD":
                continue
            return e.code < 400
        except Exception:
            if method == "HEAD":
                continue
            return False
    return False


def verify_source_url(url: str) -> str:
    """Classify a candidate source URL: REJECTED / REVIEW / VERIFIED."""
    if not url or not url.strip():
        return REJECTED
    if is_reserved_domain(url):
        return REJECTED
    return VERIFIED if is_reachable(url) else REVIEW


def ingest_verified_opportunities(project, candidates, *, source_type, opportunity_type=None) -> dict:
    """Save only opportunities whose source URL passes the grounding gate.

    `candidates` is an iterable of dicts:
        {name, source_url, source_name?, deadline?(date), description?, external_id?}
    Returns a summary with saved/rejected counts and the rejected names (so callers
    can log exactly what was dropped — no silent truncation).
    """
    opportunity_type = opportunity_type or Opportunity.OpportunityType.GRANT
    saved = rejected = 0
    rejected_names: list[str] = []
    seen: set[str] = set()

    for c in candidates:
        name = (c.get("name") or "").strip()
        url = (c.get("source_url") or "").strip()
        if not name:
            continue
        verdict = verify_source_url(url)
        if verdict == REJECTED:
            rejected += 1
            rejected_names.append(name)
            continue

        external_id = (c.get("external_id") or f"web:{url}").strip()
        if external_id in seen:
            continue
        seen.add(external_id)

        Opportunity.objects.update_or_create(
            project=project,
            external_id=external_id,
            defaults={
                "name": name[:500],
                "opportunity_type": opportunity_type,
                "source_type": source_type,
                "source_name": (c.get("source_name") or "")[:500],
                "deadline": c.get("deadline"),
                "notes": (c.get("description") or "")[:2000],
                "source_urls": [url],
                "source_notes": f"Grounded research ({verdict}).",
                # Researched data always lands in review — the gate verifies the URL is
                # real, not that the opportunity fits. A human confirms fit/accuracy.
                "verification_status": Opportunity.VerificationStatus.NEEDS_REVIEW,
                "last_reviewed_at": timezone.now(),
            },
        )
        saved += 1

    return {
        "saved": saved,
        "rejected": rejected,
        "rejected_names": rejected_names,
    }
