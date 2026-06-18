from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreExplanation:
    label: str
    score: int | str
    level: str
    contributors: list[str]
    gaps: list[str]
    highest_leverage_action: str


def _dedupe(values, limit: int = 6) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        clean = str(value or "").strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            unique.append(clean)
        if len(unique) >= limit:
            break
    return unique


def explain_readiness(readiness) -> ScoreExplanation:
    contributors = _dedupe(
        [
            "Mission defined" if "Mission complete" in readiness.strengths else "",
            "Programs defined" if "Programs complete" in readiness.strengths else "",
            "Outcomes available" if any("Outcomes can support credibility" in item for item in readiness.strengths) else "",
            "Documents available" if readiness.document_readiness_score >= 65 else "",
            "Evidence available" if readiness.evidence_readiness_score >= 65 else "",
            "Partnerships available" if "Partnerships complete" in readiness.strengths else "",
        ]
        + readiness.strengths,
    )
    return ScoreExplanation(
        label="Readiness Score",
        score=readiness.overall_score,
        level=readiness.level,
        contributors=contributors or ["Readiness inputs are being gathered."],
        gaps=_dedupe(readiness.gaps) or ["No major readiness gaps detected."],
        highest_leverage_action=readiness.recommended_actions[0] if readiness.recommended_actions else "Maintain readiness.",
    )


def explain_organization_completeness(completeness) -> ScoreExplanation:
    return ScoreExplanation(
        label="Organization Completeness",
        score=completeness.score,
        level=completeness.level,
        contributors=_dedupe([f"{area} complete" for area in completeness.completed_areas])
        or ["Organization profile areas are being gathered."],
        gaps=_dedupe([f"{area} missing" for area in completeness.missing_areas])
        or ["No organization completeness gaps detected."],
        highest_leverage_action=f"Complete {completeness.highest_leverage_missing_area}."
        if completeness.highest_leverage_missing_area != "No missing area detected"
        else "Maintain complete organization profile data.",
    )


def explain_pursuit_readiness(pursuit_readiness) -> ScoreExplanation:
    return ScoreExplanation(
        label="Opportunity Pursuit Readiness",
        score=pursuit_readiness.score,
        level=pursuit_readiness.level,
        contributors=_dedupe(pursuit_readiness.why_ready) or ["Pursuit readiness inputs are being gathered."],
        gaps=_dedupe(pursuit_readiness.why_not_ready) or ["No major pursuit readiness gaps detected."],
        highest_leverage_action=pursuit_readiness.highest_leverage_improvement,
    )


def explain_match_overview(match_overview) -> ScoreExplanation:
    contributors = [
        f"{category.label.replace(' Matches', '')}: {category.count} opportunities, {category.average_score} average score"
        for category in match_overview.categories
        if category.count
    ]
    gaps = [f"{gap.label} appears across {gap.count} matches" for gap in match_overview.top_gaps]
    return ScoreExplanation(
        label="Match Score",
        score=match_overview.overall_score,
        level=match_overview.strongest_category,
        contributors=_dedupe(contributors) or ["No match contributors available yet."],
        gaps=_dedupe(gaps) or ["No match gaps detected."],
        highest_leverage_action=match_overview.highest_leverage_improvement,
    )


def explain_forecast(forecast) -> ScoreExplanation:
    lifecycle = {item.label: item for item in forecast.by_lifecycle_stage}
    submitted = lifecycle.get("Submitted")
    pursuing = lifecycle.get("Pursuing")
    qualified = lifecycle.get("Qualified")
    contributors = [
        f"Submitted Opportunities: {submitted.count if submitted else 0}",
        f"Pursuing Opportunities: {pursuing.count if pursuing else 0}",
        f"Qualified Opportunities: {qualified.count if qualified else 0}",
    ]
    if forecast.highest_value_opportunity:
        contributors.append(f"Highest Value Opportunity: {forecast.highest_value_opportunity.name}")
    if forecast.highest_confidence_opportunity:
        contributors.append(f"Largest Opportunity Contributor: {forecast.highest_confidence_opportunity.name}")
    gaps = []
    if not submitted or submitted.count == 0:
        gaps.append("No submitted opportunities contributing at the submitted stage weight.")
    if not pursuing or pursuing.count == 0:
        gaps.append("No pursuing opportunities contributing at the pursuing stage weight.")
    if forecast.forecast_confidence == "Low":
        gaps.append("Forecast confidence is low because too few opportunities have high-confidence values.")
    return ScoreExplanation(
        label="Forecast Health",
        score=f"${forecast.weighted_forecast_value:,.0f}",
        level=f"{forecast.forecast_confidence} confidence",
        contributors=_dedupe(contributors),
        gaps=_dedupe(gaps) or ["No major forecast gaps detected."],
        highest_leverage_action="Move qualified opportunities into pursuit and keep estimated values current.",
    )


def explain_relationship_health(relationships) -> ScoreExplanation:
    return ScoreExplanation(
        label="Relationship Health",
        score=relationships.health.score,
        level=relationships.health.level,
        contributors=_dedupe(relationships.health.strengths) or ["Relationship contributors are being gathered."],
        gaps=_dedupe(relationships.relationship_gaps) or ["No relationship health gaps detected."],
        highest_leverage_action=relationships.health.highest_leverage_action,
    )
