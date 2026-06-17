from dataclasses import dataclass, field

from openoutreach.funding.models import (
    Funder,
    GovernmentEntity,
    PartnerOrganization,
    ResourceProvider,
)


MATCH_WEIGHTS = {
    "geography": 30,
    "focus": 25,
    "beneficiary": 20,
    "program": 15,
    "organization_type": 10,
}


@dataclass(frozen=True)
class OpportunityMatch:
    name: str
    score: int
    level: str
    opportunity_type: str
    category: str
    reasons: list[str]
    match_factors: list[str]
    missing_factors: list[str]
    improvement_suggestions: list[str]
    geography_relevance: int

    @property
    def matching_factor_count(self) -> int:
        return len(self.match_factors)


@dataclass(frozen=True)
class MatchCategory:
    label: str
    matches: list[OpportunityMatch]

    @property
    def count(self) -> int:
        return len(self.matches)

    @property
    def average_score(self) -> int:
        if not self.matches:
            return 0
        return round(sum(match.score for match in self.matches) / len(self.matches))

    @property
    def highest_score(self) -> int:
        if not self.matches:
            return 0
        return max(match.score for match in self.matches)

    @property
    def lowest_score(self) -> int:
        if not self.matches:
            return 0
        return min(match.score for match in self.matches)

    @property
    def top_matches(self) -> list[OpportunityMatch]:
        return self.matches[:5]


@dataclass(frozen=True)
class MatchOverview:
    overall_score: int
    total_matches: int
    categories: list[MatchCategory]
    top_recommended: list[OpportunityMatch] = field(default_factory=list)
    readiness_signals: list[str] = field(default_factory=list)

    @property
    def funding_count(self) -> int:
        return _category_count(self.categories, "Funding Matches")

    @property
    def government_count(self) -> int:
        return _category_count(self.categories, "Government Matches")

    @property
    def resource_count(self) -> int:
        return _category_count(self.categories, "Resource Matches")

    @property
    def partnership_count(self) -> int:
        return _category_count(self.categories, "Partnership Matches")

    @property
    def highest_score(self) -> int:
        scores = [match.score for category in self.categories for match in category.matches]
        return max(scores) if scores else 0

    @property
    def strongest_category(self) -> str:
        if not self.categories:
            return "No matches yet"
        best = sorted(
            self.categories,
            key=lambda category: (-category.average_score, -category.highest_score, category.label),
        )[0]
        return best.label.replace(" Matches", "")


def _category_count(categories: list[MatchCategory], label: str) -> int:
    for category in categories:
        if category.label == label:
            return category.count
    return 0


def match_level(score: int) -> str:
    if score >= 90:
        return "Excellent Match"
    if score >= 75:
        return "Strong Match"
    if score >= 60:
        return "Moderate Match"
    return "Weak Match"


def _has_values(values) -> bool:
    return any(str(value).strip() for value in values or [])


def _clean_values(values) -> list[str]:
    return [str(value).strip() for value in values or [] if str(value).strip()]


def _display(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split())


def _profile(project, funding_criteria=None) -> dict:
    organization = project.organization
    geography = _clean_values([
        organization.city,
        organization.county,
        organization.state,
        organization.service_area_notes,
    ])
    focus_areas = _clean_values(organization.focus_areas)
    beneficiaries = _clean_values(organization.beneficiaries)
    if funding_criteria:
        focus_areas.extend(_clean_values(funding_criteria.focus_areas))
        focus_areas.extend(_clean_values(funding_criteria.program_areas))
        focus_areas.extend(_clean_values(funding_criteria.funding_use_categories))
        beneficiaries.extend(_clean_values(funding_criteria.beneficiaries))
    program_terms = _clean_values([
        project.programs,
        organization.mission,
        organization.organization_summary,
        *_clean_values(organization.capabilities),
    ])
    combined_text = "\n".join(
        program_terms
        + focus_areas
        + beneficiaries
        + _clean_values(organization.outcomes_and_impact)
        + _clean_values(organization.existing_partnerships)
        + _clean_values(organization.current_funding_sources)
        + [organization.organization_type or ""]
    ).casefold()
    return {
        "organization_type": str(organization.organization_type or "").strip(),
        "geography": geography,
        "focus_areas": focus_areas,
        "beneficiaries": beneficiaries,
        "program_terms": program_terms,
        "combined_text": combined_text,
        "has_outcomes": _has_values(organization.outcomes_and_impact),
        "has_partnerships": _has_values(organization.existing_partnerships),
        "has_budget": bool(organization.budget_range.strip()),
        "has_geography": _has_values(geography),
        "has_beneficiaries": _has_values(beneficiaries),
    }


def _overlap(profile_values: list[str], record_values: list[str], record_text: str) -> list[str]:
    matches = []
    for value in profile_values:
        candidate = value.casefold()
        if not candidate:
            continue
        if candidate in record_text:
            matches.append(value)
            continue
        for record_value in record_values:
            record_candidate = record_value.casefold()
            if candidate in record_candidate or record_candidate in candidate:
                matches.append(value)
                break
    return matches


def _keyword_matches(keywords: list[str], text: str) -> list[str]:
    return [keyword for keyword in keywords if keyword.casefold() in text]


def _factor_score(matches: list[str], weight: int, *, partial: int = 0) -> int:
    if len(matches) >= 2:
        return weight
    if len(matches) == 1:
        return max(partial, round(weight * 0.75))
    return partial


def _missing_profile_factors(profile: dict) -> list[str]:
    missing = []
    if not profile["has_outcomes"]:
        missing.append("Outcomes Evidence")
    if not profile["has_partnerships"]:
        missing.append("Partnership Evidence")
    if not profile["has_budget"]:
        missing.append("Budget Context")
    if not profile["has_geography"]:
        missing.append("Service Geography")
    if not profile["has_beneficiaries"]:
        missing.append("Beneficiary Detail")
    return missing


def _improvement_suggestions(profile: dict, score: int) -> list[str]:
    if score >= 75:
        return []
    suggestions = []
    if not profile["has_outcomes"]:
        suggestions.append("Adding outcomes data")
    if not profile["has_geography"]:
        suggestions.append("Defining service geography")
    if not profile["has_partnerships"]:
        suggestions.append("Adding partnership information")
    if not profile["has_beneficiaries"]:
        suggestions.append("Expanding beneficiary information")
    if not profile["has_budget"]:
        suggestions.append("Adding budget context")
    if suggestions:
        return suggestions
    return ["Adding stronger evidence for this opportunity category"]


def _readiness_signals(profile: dict) -> list[str]:
    signals = []
    if not profile["has_outcomes"]:
        signals.append("Outcomes")
    if not profile["has_partnerships"]:
        signals.append("Partnerships")
    if not profile["has_budget"]:
        signals.append("Budget")
    if not profile["has_geography"]:
        signals.append("Geography")
    if not profile["has_beneficiaries"]:
        signals.append("Beneficiaries")
    return signals or ["Outcomes", "Partnerships", "Budget", "Geography", "Beneficiaries"]


def _score_record(
    *,
    profile: dict,
    name: str,
    opportunity_type: str,
    category: str,
    geography: list[str],
    focus_areas: list[str],
    beneficiaries: list[str],
    program_terms: list[str],
    compatibility_text: str = "",
) -> OpportunityMatch:
    record_geography = _clean_values(geography)
    record_focus = _clean_values(focus_areas)
    record_beneficiaries = _clean_values(beneficiaries)
    record_program_terms = _clean_values(program_terms)
    record_text = "\n".join(
        [name, opportunity_type, compatibility_text]
        + record_geography
        + record_focus
        + record_beneficiaries
        + record_program_terms
    ).casefold()

    geography_matches = _overlap(profile["geography"], record_geography, record_text)
    focus_matches = _overlap(profile["focus_areas"], record_focus, record_text)
    focus_matches += _keyword_matches(
        ["workforce development", "digital equity", "career readiness", "youth development", "technology"],
        record_text,
    )
    beneficiary_matches = _overlap(profile["beneficiaries"], record_beneficiaries, record_text)
    beneficiary_matches += _keyword_matches(
        ["youth", "students", "young adults", "job seekers", "low-income residents"],
        record_text,
    )
    program_matches = _keyword_matches(
        ["workforce", "career", "training", "digital", "technology", "mentoring", "job placement"],
        profile["combined_text"] + "\n" + record_text,
    )
    organization_type = profile["organization_type"]
    organization_type_match = bool(
        organization_type
        and (
            organization_type.casefold() in record_text
            or "nonprofit" in organization_type.casefold()
        )
    )

    geography_score = _factor_score(geography_matches, MATCH_WEIGHTS["geography"])
    focus_score = _factor_score(focus_matches, MATCH_WEIGHTS["focus"])
    beneficiary_score = _factor_score(beneficiary_matches, MATCH_WEIGHTS["beneficiary"])
    program_score = _factor_score(program_matches, MATCH_WEIGHTS["program"])
    organization_score = MATCH_WEIGHTS["organization_type"] if organization_type_match else 0
    score = max(0, min(
        geography_score + focus_score + beneficiary_score + program_score + organization_score,
        100,
    ))

    match_factors = []
    reasons = []
    if geography_matches:
        match_factors.append("Geography Alignment")
        reasons.append(f"{_display(geography_matches[0])} geography alignment")
    if focus_matches:
        first_focus = _display(focus_matches[0])
        match_factors.append(f"{first_focus} Alignment")
        reasons.append(f"{first_focus} alignment")
    if beneficiary_matches:
        first_beneficiary = _display(beneficiary_matches[0])
        match_factors.append(f"{first_beneficiary} Alignment")
        reasons.append(f"{first_beneficiary} beneficiary alignment")
    if program_matches:
        first_program = _display(program_matches[0])
        match_factors.append(f"{first_program} Program Alignment")
        reasons.append(f"{first_program} program alignment")
    if organization_type_match:
        match_factors.append("Organization Type Alignment")
        reasons.append(f"{_display(organization_type)} compatibility")
    if not reasons:
        reasons.append("General mission adjacency")

    missing_factors = _missing_profile_factors(profile)
    return OpportunityMatch(
        name=name,
        score=score,
        level=match_level(score),
        opportunity_type=opportunity_type,
        category=category,
        reasons=reasons[:5],
        match_factors=match_factors[:5],
        missing_factors=missing_factors[:4],
        improvement_suggestions=_improvement_suggestions(profile, score),
        geography_relevance=geography_score,
    )


def _sort_matches(matches: list[OpportunityMatch]) -> list[OpportunityMatch]:
    return sorted(
        matches,
        key=lambda match: (-match.score, -match.matching_factor_count, -match.geography_relevance, match.name),
    )


def build_opportunity_matches(project, funding_criteria=None) -> MatchOverview:
    profile = _profile(project, funding_criteria)

    funding_matches = _sort_matches([
        _score_record(
            profile=profile,
            name=funder.name,
            opportunity_type=funder.get_funder_type_display(),
            category="Funding Matches",
            geography=funder.geography,
            focus_areas=funder.focus_areas,
            beneficiaries=funder.beneficiaries,
            program_terms=[],
            compatibility_text=f"{funder.eligibility_notes}\n{funder.notes}",
        )
        for funder in Funder.objects.filter(active=True)
    ])
    government_matches = _sort_matches([
        _score_record(
            profile=profile,
            name=entity.name,
            opportunity_type=entity.get_entity_type_display(),
            category="Government Matches",
            geography=entity.geography,
            focus_areas=entity.focus_areas,
            beneficiaries=[],
            program_terms=entity.opportunity_lanes,
            compatibility_text=f"{entity.department_or_office}\n{entity.notes}",
        )
        for entity in GovernmentEntity.objects.filter(active=True)
    ])
    resource_matches = _sort_matches([
        _score_record(
            profile=profile,
            name=provider.name,
            opportunity_type=provider.get_resource_type_display(),
            category="Resource Matches",
            geography=provider.geography,
            focus_areas=provider.focus_areas,
            beneficiaries=[],
            program_terms=provider.resource_categories,
            compatibility_text=f"{provider.eligibility_notes}\n{provider.notes}",
        )
        for provider in ResourceProvider.objects.filter(active=True)
    ])
    partnership_matches = _sort_matches([
        _score_record(
            profile=profile,
            name=partner.name,
            opportunity_type=partner.get_partner_type_display(),
            category="Partnership Matches",
            geography=partner.geography,
            focus_areas=partner.focus_areas,
            beneficiaries=partner.beneficiaries,
            program_terms=partner.collaboration_opportunities,
            compatibility_text=partner.notes,
        )
        for partner in PartnerOrganization.objects.filter(active=True)
    ])
    categories = [
        MatchCategory("Funding Matches", funding_matches),
        MatchCategory("Government Matches", government_matches),
        MatchCategory("Resource Matches", resource_matches),
        MatchCategory("Partnership Matches", partnership_matches),
    ]
    all_matches = _sort_matches([
        match
        for category in categories
        for match in category.matches
    ])
    overall_score = round(sum(match.score for match in all_matches) / len(all_matches)) if all_matches else 0
    return MatchOverview(
        overall_score=overall_score,
        total_matches=len(all_matches),
        categories=categories,
        top_recommended=all_matches[:8],
        readiness_signals=_readiness_signals(profile),
    )
