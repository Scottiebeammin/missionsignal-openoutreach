import re

from pydantic import BaseModel, Field


class OrganizationAnalyzerInput(BaseModel):
    organization_name: str
    website: str
    mission: str
    programs: str
    organization_type: str = ""
    city: str = ""
    county: str = ""
    state: str = ""
    service_area_notes: str = ""
    outcomes_and_impact: list[str] = Field(default_factory=list)
    budget_range: str = ""
    current_funding_sources: list[str] = Field(default_factory=list)
    existing_partnerships: list[str] = Field(default_factory=list)


class FundingCriteriaAnalysis(BaseModel):
    focus_areas: list[str] = Field(default_factory=list)
    beneficiaries: list[str] = Field(default_factory=list)
    eligible_geographies: list[str] = Field(default_factory=list)
    program_areas: list[str] = Field(default_factory=list)
    funding_use_categories: list[str] = Field(default_factory=list)
    likely_funder_types: list[str] = Field(default_factory=list)
    likely_opportunity_types: list[str] = Field(default_factory=list)
    inclusion_criteria: str = ""


class OrganizationAnalyzerOutput(BaseModel):
    organization_summary: str
    focus_areas: list[str] = Field(default_factory=list)
    beneficiaries: list[str] = Field(default_factory=list)
    service_geographies: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    outcomes_and_impact: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    analysis_warnings: list[str] = Field(default_factory=list)
    analysis_confidence: float
    funding_criteria: FundingCriteriaAnalysis


_FOCUS_RULES = {
    "education": ("education", "school", "student", "learning", "training"),
    "workforce development": ("workforce", "career", "employment", "job"),
    "food security": ("food", "nutrition", "meal", "hunger"),
    "housing": ("housing", "homeless", "shelter"),
    "health": ("health", "wellness", "medical", "mental health"),
    "economic mobility": ("economic mobility", "small business", "entrepreneur"),
    "youth development": ("youth", "young people", "children", "teen"),
    "environment": ("environment", "climate", "conservation", "sustainability"),
}

_BENEFICIARY_RULES = {
    "youth": ("youth", "young people", "children", "teen", "student"),
    "job seekers": ("job seeker", "employment", "workforce", "career"),
    "small businesses": ("small business", "entrepreneur"),
    "families": ("families", "family"),
    "communities": ("community", "communities", "residents"),
}

_CAPABILITY_RULES = {
    "training": ("training", "workshop", "education", "coaching"),
    "direct service delivery": ("service", "program", "support", "provide"),
    "technical assistance": ("technical assistance", "coaching", "advising"),
    "community outreach": ("outreach", "community engagement"),
    "research": ("research", "study", "analysis"),
}


def _matches(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    return [label for label, terms in rules.items() if any(term in text for term in terms)]


def _unique(values) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _keywords(text: str, limit: int = 12) -> list[str]:
    excluded = {
        "about", "their", "there", "these", "those", "through", "with", "from",
        "that", "this", "will", "have", "into", "your", "program", "programs",
    }
    words = re.findall(r"[a-z][a-z-]{3,}", text.casefold())
    return _unique(word for word in words if word not in excluded)[:limit]


def analyze_deterministically(data: OrganizationAnalyzerInput) -> OrganizationAnalyzerOutput:
    """Produce a repeatable analyzer result without external API calls."""
    combined = "\n".join([
        data.mission,
        data.programs,
        data.organization_type,
        "\n".join(data.outcomes_and_impact),
        "\n".join(data.current_funding_sources),
        "\n".join(data.existing_partnerships),
    ]).casefold()
    focus_areas = _matches(combined, _FOCUS_RULES)
    beneficiaries = _matches(combined, _BENEFICIARY_RULES)
    capabilities = _matches(combined, _CAPABILITY_RULES)
    geographies = _unique([data.city, data.county, data.state, data.service_area_notes])
    outcomes = _unique(data.outcomes_and_impact)
    warnings = []

    if not focus_areas:
        warnings.append("No clear focus areas could be inferred from the mission and programs.")
    if not beneficiaries:
        warnings.append("No clear beneficiary groups could be inferred from the mission and programs.")
    if not geographies:
        warnings.append("No optional location or service-area context was provided.")
    if not outcomes:
        warnings.append("Outcomes and impact require supporting evidence and were not inferred in deterministic mode.")
    if not data.budget_range:
        warnings.append("Budget range was not provided.")
    if not data.current_funding_sources:
        warnings.append("Current funding sources were not provided.")
    if not data.existing_partnerships:
        warnings.append("Existing partnerships were not provided.")

    confidence = max(0.35, 0.9 - 0.12 * len(warnings))
    search_keywords = _unique([
        *focus_areas,
        *beneficiaries,
        *_keywords(combined),
        *geographies[:3],
    ])
    summary = f"{data.organization_name} advances {data.mission.strip()} through {data.programs.strip()}"
    inclusion_parts = _unique([
        *focus_areas,
        *beneficiaries,
        *geographies,
        data.organization_type,
        *outcomes,
    ])

    criteria = FundingCriteriaAnalysis(
        focus_areas=focus_areas,
        beneficiaries=beneficiaries,
        eligible_geographies=geographies,
        program_areas=focus_areas,
        funding_use_categories=capabilities,
        likely_funder_types=["government", "foundation", "corporate"],
        likely_opportunity_types=["program grant", "general operating support"],
        inclusion_criteria=", ".join(inclusion_parts),
    )
    return OrganizationAnalyzerOutput(
        organization_summary=summary,
        focus_areas=focus_areas,
        beneficiaries=beneficiaries,
        service_geographies=geographies,
        capabilities=capabilities,
        outcomes_and_impact=outcomes,
        search_keywords=search_keywords,
        analysis_warnings=warnings,
        analysis_confidence=confidence,
        funding_criteria=criteria,
    )
