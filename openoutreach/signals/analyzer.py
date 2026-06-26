import re

from pydantic import BaseModel, Field

from openoutreach.signals.categories import CATEGORY_KEYWORDS, OPPORTUNITY_FOCUS_CATEGORIES


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
    # Enrichment sources — populated before analysis runs
    website_text: str = ""     # raw text scraped from the org's homepage
    intake_notes: str = ""     # free-text "how can we help" from intake form
    focus_area_selections: list[str] = Field(default_factory=list)   # checkbox picks at intake
    beneficiary_selections: list[str] = Field(default_factory=list)  # checkbox picks at intake


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


# Map every canonical focus area → its detection keywords
_FOCUS_RULES: dict[str, tuple[str, ...]] = {
    category.casefold(): terms
    for category, terms in CATEGORY_KEYWORDS.items()
}
_FOCUS_RULES.update({
    "economic mobility": ("economic mobility", "small business", "entrepreneur", "financial literacy"),
    "environment": ("environment", "climate", "conservation", "sustainability", "green"),
    "girls": ("girls", "girl", "young women", "women and girls"),
    "stem": ("stem", "science", "technology", "engineering", "mathematics", "coding"),
    "financial empowerment": ("financial empowerment", "financial literacy", "asset building", "savings"),
    "civic engagement": ("civic", "voting", "civic engagement", "leadership"),
    "language access": ("language access", "english learner", "bilingual", "translation"),
    "early childhood": ("early childhood", "early learning", "preschool", "childcare", "head start"),
    "substance use": ("substance use", "addiction", "recovery", "sobriety", "treatment"),
    "domestic violence": ("domestic violence", "gender-based violence", "dv", "survivor"),
    "human trafficking": ("human trafficking", "trafficking", "exploitation"),
    "maternal health": ("maternal health", "maternal", "prenatal", "postpartum"),
    "oral health": ("oral health", "dental", "dentistry"),
    "nutrition": ("nutrition", "obesity", "healthy eating", "food access"),
    "physical activity": ("physical activity", "exercise", "sports", "recreation"),
    "financial services": ("credit union", "cdfi", "microfinance", "financial access"),
})

_BENEFICIARY_RULES: dict[str, tuple[str, ...]] = {
    "youth": ("youth", "young people", "children", "teen", "student", "kids", "adolescent"),
    "girls and young women": ("girls", "young women", "female youth"),
    "job seekers": ("job seeker", "employment", "workforce", "career", "unemployed"),
    "small businesses": ("small business", "entrepreneur", "startup"),
    "families": ("families", "family", "household", "parents"),
    "seniors": ("senior", "older adult", "aging", "elder", "65+"),
    "veterans": ("veteran", "military", "service member"),
    "people experiencing homelessness": ("homeless", "unhoused", "housing insecure"),
    "immigrants and refugees": ("immigrant", "refugee", "new american", "asylum seeker"),
    "people with disabilities": ("disability", "disabled", "accessibility"),
    "LGBTQ+ individuals": ("lgbtq", "queer", "transgender", "nonbinary"),
    "justice-involved individuals": ("reentry", "formerly incarcerated", "justice-involved"),
    "low-income residents": ("low-income", "under-resourced", "poverty", "underserved"),
    "communities of color": ("communities of color", "bipoc", "black community", "latino", "hispanic"),
    "rural residents": ("rural", "rural community", "remote community"),
    "communities": ("community", "communities", "residents", "neighborhood"),
}

_CAPABILITY_RULES: dict[str, tuple[str, ...]] = {
    "training": ("training", "workshop", "education", "coaching", "instruction"),
    "direct service delivery": ("service", "program", "support", "provide", "deliver"),
    "technical assistance": ("technical assistance", "coaching", "advising", "consultation"),
    "community outreach": ("outreach", "community engagement", "canvassing", "awareness"),
    "research": ("research", "study", "analysis", "evaluation", "data"),
    "advocacy": ("advocacy", "policy", "systemic change", "legislation"),
    "case management": ("case management", "wraparound", "care coordination"),
    "mentoring": ("mentor", "mentoring", "mentorship"),
    "job placement": ("job placement", "hiring", "employment", "internship"),
}


def _matches(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    return [label for label, terms in rules.items() if any(term in text for term in terms)]


def _canonical_focus(values: list[str]) -> list[str]:
    """Normalize user-selected focus areas to canonical OPPORTUNITY_FOCUS_CATEGORIES labels."""
    result = []
    for value in values:
        folded = value.casefold().strip()
        matched = False
        for category in OPPORTUNITY_FOCUS_CATEGORIES:
            if folded == category.casefold():
                result.append(category)
                matched = True
                break
            keywords = CATEGORY_KEYWORDS.get(category, ())
            if any(kw in folded or folded in kw for kw in keywords):
                result.append(category)
                matched = True
                break
        if not matched and value.strip():
            result.append(value.strip())
    return list(dict.fromkeys(result))


def _unique(values) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _keywords(text: str, limit: int = 12) -> list[str]:
    excluded = {
        "about", "their", "there", "these", "those", "through", "with", "from",
        "that", "this", "will", "have", "into", "your", "program", "programs",
        "organization", "nonprofit", "provide", "support", "community",
    }
    words = re.findall(r"[a-z][a-z-]{3,}", text.casefold())
    return _unique(word for word in words if word not in excluded)[:limit]


def analyze_deterministically(data: OrganizationAnalyzerInput) -> OrganizationAnalyzerOutput:
    """Produce a repeatable analyzer result without external API calls.

    Uses mission + programs as the primary signal, then enriches from:
    - website_text (scraped homepage)
    - intake_notes (free-text focus description)
    - focus_area_selections / beneficiary_selections (explicit checkboxes)
    """
    # Primary corpus — structured intake fields
    primary = "\n".join([
        data.mission,
        data.programs,
        data.organization_type,
        "\n".join(data.outcomes_and_impact),
        "\n".join(data.current_funding_sources),
        "\n".join(data.existing_partnerships),
    ]).casefold()

    # Extended corpus — website + notes (lower authority, used for enrichment)
    extended = "\n".join([
        data.intake_notes,
        data.website_text[:4_000],  # cap website contribution
    ]).casefold()

    combined = primary + "\n" + extended

    # Focus areas: explicit selections win outright, then infer from text
    if data.focus_area_selections:
        focus_areas = _canonical_focus(data.focus_area_selections)
        # Also check text for any additional areas the user didn't tick
        inferred = _matches(combined, _FOCUS_RULES)
        for area in inferred:
            canonical = next(
                (c for c in OPPORTUNITY_FOCUS_CATEGORIES if c.casefold() == area),
                area,
            )
            if canonical not in focus_areas:
                focus_areas.append(canonical)
    else:
        raw = _matches(combined, _FOCUS_RULES)
        focus_areas = _canonical_focus(raw)

    # Beneficiaries: explicit selections win, then infer
    if data.beneficiary_selections:
        beneficiaries = _unique(data.beneficiary_selections)
        inferred_b = _matches(combined, _BENEFICIARY_RULES)
        for b in inferred_b:
            if b not in beneficiaries:
                beneficiaries.append(b)
    else:
        beneficiaries = _matches(combined, _BENEFICIARY_RULES)

    capabilities = _matches(combined, _CAPABILITY_RULES)
    geographies = _unique([data.city, data.county, data.state, data.service_area_notes])
    outcomes = _unique(data.outcomes_and_impact)
    warnings = []

    if not focus_areas:
        warnings.append("No clear focus areas could be inferred from the mission, programs, or website.")
    if not beneficiaries:
        warnings.append("No clear beneficiary groups could be inferred. Consider adding who you serve.")
    if not geographies:
        warnings.append("No location or service-area context was provided.")
    if not outcomes:
        warnings.append("Outcomes and impact were not provided.")
    if not data.budget_range:
        warnings.append("Budget range was not provided.")
    if not data.current_funding_sources:
        warnings.append("Current funding sources were not provided.")
    if not data.existing_partnerships:
        warnings.append("Existing partnerships were not provided.")

    confidence = max(0.35, 0.9 - 0.08 * len(warnings))
    search_keywords = _unique([
        *focus_areas,
        *beneficiaries,
        *_keywords(combined),
        *geographies[:3],
    ])
    summary = (
        f"{data.organization_name} serves {', '.join(beneficiaries[:3]) or 'the community'} "
        f"through {', '.join(focus_areas[:3]) or 'its programs'} in {', '.join(geographies[:2]) or 'its service area'}."
        if focus_areas or beneficiaries
        else f"{data.organization_name} advances {data.mission.strip()} through {data.programs.strip()}"
    )
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
