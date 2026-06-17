from dataclasses import dataclass, field

from openoutreach.funding.models import (
    Funder,
    GovernmentEntity,
    PartnerOrganization,
    ResourceProvider,
)


@dataclass(frozen=True)
class OpportunityMatch:
    name: str
    score: int
    level: str
    opportunity_type: str
    category: str
    reasons: list[str]


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
    def top_matches(self) -> list[OpportunityMatch]:
        return self.matches[:5]


@dataclass(frozen=True)
class MatchOverview:
    overall_score: int
    total_matches: int
    categories: list[MatchCategory]
    top_recommended: list[OpportunityMatch] = field(default_factory=list)

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


def _category_count(categories: list[MatchCategory], label: str) -> int:
    for category in categories:
        if category.label == label:
            return category.count
    return 0


def match_level(score: int) -> str:
    if score >= 85:
        return "Excellent Match"
    if score >= 70:
        return "Strong Match"
    if score >= 50:
        return "Moderate Match"
    return "Weak Match"


def _has_values(values) -> bool:
    return any(str(value).strip() for value in values or [])


def _clean_values(values) -> list[str]:
    return [str(value).strip() for value in values or [] if str(value).strip()]


def _title_reason(value: str, suffix: str) -> str:
    return f"{' '.join(word.capitalize() for word in value.split())} {suffix}"


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
    combined_text = "\n".join(
        _clean_values([
            organization.mission,
            project.programs,
            organization.organization_summary,
            organization.organization_type,
        ])
        + focus_areas
        + beneficiaries
        + _clean_values(organization.capabilities)
        + _clean_values(organization.outcomes_and_impact)
    ).casefold()
    return {
        "organization_type": str(organization.organization_type or "").strip(),
        "geography": geography,
        "focus_areas": focus_areas,
        "beneficiaries": beneficiaries,
        "programs": project.programs,
        "combined_text": combined_text,
    }


def _aligned(profile_values: list[str], record_values: list[str], text: str = "") -> list[str]:
    matches = []
    record_text = "\n".join(record_values).casefold()
    for value in profile_values:
        candidate = value.casefold()
        if not candidate:
            continue
        if candidate in record_text or candidate in text:
            matches.append(value)
            continue
        for record_value in record_values:
            record_candidate = record_value.casefold()
            if candidate in record_candidate or record_candidate in candidate:
                matches.append(value)
                break
    return matches


def _keyword_alignment(keywords: list[str], text: str) -> list[str]:
    return [keyword for keyword in keywords if keyword.casefold() in text]


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
    score = 20
    reasons = []
    combined_record_text = "\n".join(
        [name, opportunity_type, compatibility_text]
        + _clean_values(geography)
        + _clean_values(focus_areas)
        + _clean_values(beneficiaries)
        + _clean_values(program_terms)
    ).casefold()

    geography_matches = _aligned(profile["geography"], _clean_values(geography), combined_record_text)
    if geography_matches:
        score += 25
        reasons.append(_title_reason(geography_matches[0], "geography alignment"))

    focus_matches = _aligned(profile["focus_areas"], _clean_values(focus_areas), combined_record_text)
    keyword_focus = _keyword_alignment(["workforce", "digital equity", "career", "youth", "technology"], combined_record_text)
    if focus_matches or keyword_focus:
        score += 25
        reasons.append(_title_reason((focus_matches or keyword_focus)[0], "alignment"))

    beneficiary_matches = _aligned(profile["beneficiaries"], _clean_values(beneficiaries), combined_record_text)
    keyword_beneficiaries = _keyword_alignment(["youth", "students", "young adults", "job seekers"], combined_record_text)
    if beneficiary_matches or keyword_beneficiaries:
        score += 20
        reasons.append(_title_reason((beneficiary_matches or keyword_beneficiaries)[0], "beneficiary alignment"))

    profile_text = profile["combined_text"]
    program_matches = _keyword_alignment(
        ["workforce", "career", "training", "digital", "technology", "mentoring", "job placement"],
        profile_text + "\n" + combined_record_text,
    )
    if program_matches:
        score += 20
        reasons.append(_title_reason(program_matches[0], "program alignment"))

    organization_type = profile["organization_type"]
    if organization_type and organization_type.casefold() in compatibility_text.casefold():
        score += 10
        reasons.append(_title_reason(organization_type, "compatibility"))
    elif organization_type and "nonprofit" in organization_type.casefold():
        score += 6
        reasons.append("Nonprofit compatibility")

    score = max(0, min(score, 100))
    if not reasons:
        reasons.append("General mission adjacency")
    return OpportunityMatch(
        name=name,
        score=score,
        level=match_level(score),
        opportunity_type=opportunity_type,
        category=category,
        reasons=reasons[:4],
    )


def _sort_matches(matches: list[OpportunityMatch]) -> list[OpportunityMatch]:
    return sorted(matches, key=lambda match: (-match.score, match.name))


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
    )
