"""'Not a fit' feedback loop — creation/toggling plus view-layer suppression.

Suppression deliberately lives at the VIEW layer, not in matching.py: the match
builders stay pure scorers, and each surface decides how a "not a fit" verdict
affects its own list (drop from top-N, tag in the full list). Helpers here are
the single vocabulary for both.

Keys: opportunities are keyed by ``str(opportunity.pk)``; reference matches
(funder/government/resource/partner) are keyed by record name, because those
surfaces render name-keyed OpportunityMatch dataclasses, not per-project rows.
"""
from __future__ import annotations

from openoutreach.signals.models import MatchFeedback

# OpportunityMatch.category label → MatchFeedback.Kind value.
CATEGORY_KIND = {
    "Funding Matches": MatchFeedback.Kind.FUNDER.value,
    "Government Matches": MatchFeedback.Kind.GOVERNMENT.value,
    "Resource Matches": MatchFeedback.Kind.RESOURCE.value,
    "Partnership Matches": MatchFeedback.Kind.PARTNER.value,
}


def kind_for_category(category_label: str) -> str:
    """Feedback kind for an OpportunityMatch.category label (funder fallback)."""
    return CATEGORY_KIND.get(category_label, MatchFeedback.Kind.FUNDER.value)


def toggle_feedback(project, kind: str, target_key: str, user=None, note: str = "") -> bool:
    """Create the not-a-fit verdict if absent, remove it if present.

    Returns True when the target is now flagged, False when the flag was lifted.
    """
    existing = MatchFeedback.objects.filter(
        project=project, kind=kind, target_key=target_key,
    ).first()
    if existing:
        existing.delete()
        return False
    MatchFeedback.objects.create(
        project=project,
        kind=kind,
        target_key=target_key,
        verdict=MatchFeedback.Verdict.NOT_A_FIT,
        note=note,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    return True


def not_a_fit_map(project) -> dict[str, set[str]]:
    """kind → set of target_keys marked not_a_fit for this project (one query)."""
    result: dict[str, set[str]] = {}
    rows = MatchFeedback.objects.filter(
        project=project, verdict=MatchFeedback.Verdict.NOT_A_FIT,
    ).values_list("kind", "target_key")
    for kind, target_key in rows:
        result.setdefault(kind, set()).add(target_key)
    return result


def flag_opportunities(opportunities, feedback_map: dict[str, set[str]]) -> None:
    """Annotate each Opportunity instance with ``not_a_fit`` (bool) in place."""
    hidden = feedback_map.get(MatchFeedback.Kind.OPPORTUNITY.value, set())
    for opportunity in opportunities:
        opportunity.not_a_fit = str(opportunity.pk) in hidden


def suppress_top_recommended(match_overview, feedback_map: dict[str, set[str]]) -> None:
    """Drop not-a-fit reference matches from MatchOverview.top_recommended.

    The dataclass is frozen, so the list is filtered in place via slice
    assignment; category lists are left untouched (full inventory stays
    browsable — only the recommendation shelf is curated).
    """
    match_overview.top_recommended[:] = [
        match
        for match in match_overview.top_recommended
        if match.name not in feedback_map.get(kind_for_category(match.category), set())
    ]
