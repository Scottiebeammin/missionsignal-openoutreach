from dataclasses import dataclass


@dataclass(frozen=True)
class EcosystemStatus:
    name: str
    status: str
    detail: str
    href_name: str


@dataclass(frozen=True)
class EcosystemRoadmap:
    completed: list[str]
    coming_soon: list[str]
    future: list[str]


@dataclass(frozen=True)
class EcosystemOverview:
    score: int
    level: str
    statuses: list[EcosystemStatus]
    summary_items: list[str]
    roadmap: EcosystemRoadmap


def _has_values(values) -> bool:
    return any(str(value).strip() for value in values or [])


def _level(score: int) -> str:
    if score >= 85:
        return "Advanced"
    if score >= 70:
        return "Competitive"
    if score >= 50:
        return "Developing"
    return "Emerging"


def build_ecosystem_overview(project, funding_readiness, government_readiness) -> EcosystemOverview:
    organization = project.organization
    score = 20

    if organization.organization_summary or organization.mission:
        score += 15
    if project.programs:
        score += 10
    if organization.city or organization.county or organization.state or organization.service_area_notes:
        score += 10
    if _has_values(organization.beneficiaries):
        score += 8
    if _has_values(organization.outcomes_and_impact):
        score += 8
    if organization.budget_range:
        score += 7
    if _has_values(organization.current_funding_sources):
        score += 5
    if _has_values(organization.existing_partnerships):
        score += 5
    score += round((funding_readiness.readiness_score + government_readiness.readiness_score) / 20)
    score = max(0, min(score, 100))

    statuses = [
        EcosystemStatus(
            "Mission Brief",
            "Complete",
            "Organization identity, mission, geography, programs, and data gaps are available.",
            "project-mission-brief",
        ),
        EcosystemStatus(
            "FundingSignal",
            "Complete",
            "Funding readiness, funder types, local government lanes, checklist, and actions are available.",
            "project-funding",
        ),
        EcosystemStatus(
            "GovernmentSignal",
            "Complete",
            "Government readiness, public-sector lanes, entity types, checklist, and actions are available.",
            "project-government",
        ),
        EcosystemStatus(
            "ResourceSignal",
            "Coming Soon",
            "Future module for non-funding resources, technical assistance, in-kind support, and capacity help.",
            "project-resources",
        ),
        EcosystemStatus(
            "PartnershipSignal",
            "Coming Soon",
            "Future module for partner discovery, coalition mapping, and referral ecosystem analysis.",
            "project-partnerships",
        ),
    ]
    roadmap = EcosystemRoadmap(
        completed=["Mission Brief", "FundingSignal", "GovernmentSignal"],
        coming_soon=["ResourceSignal", "PartnershipSignal"],
        future=["Opportunity Discovery Engine", "Monitoring Systems", "AI Opportunity Agents"],
    )
    return EcosystemOverview(
        score=score,
        level=_level(score),
        statuses=statuses,
        summary_items=["Funding", "Government", "Resources", "Partnerships", "Capacity"],
        roadmap=roadmap,
    )
