from dataclasses import dataclass

from openoutreach.funding.models import Opportunity
from openoutreach.signals.models import OrganizationContact, PartnerOrganization


STRENGTH_POINTS = {
    OrganizationContact.RelationshipStrength.UNKNOWN: 0,
    OrganizationContact.RelationshipStrength.WEAK: 1,
    OrganizationContact.RelationshipStrength.DEVELOPING: 2,
    OrganizationContact.RelationshipStrength.ESTABLISHED: 3,
    OrganizationContact.RelationshipStrength.STRONG: 4,
}


@dataclass(frozen=True)
class RelationshipHealth:
    score: int
    level: str
    strengths: list[str]
    gaps: list[str]
    highest_leverage_action: str


@dataclass(frozen=True)
class RelationshipContext:
    related_contacts: list[OrganizationContact]
    related_partners: list[PartnerOrganization]
    relationship_label: str
    compact_status: str
    recommended_action: str


@dataclass(frozen=True)
class RelationshipPathway:
    relationship_name: str
    pathway: list[str]
    rationale: str
    expected_opportunity_categories: list[str]
    expected_partnership_outcomes: list[str]


@dataclass(frozen=True)
class RelationshipImpact:
    name: str
    impact_level: str
    score: int
    rationale: str
    opportunities_unlocked: list[str]


@dataclass(frozen=True)
class RelationshipNetworkIndicator:
    label: str
    status: str
    rationale: str


@dataclass(frozen=True)
class RelationshipOverview:
    total_contacts: int
    total_partners: int
    strong_relationships: int
    developing_relationships: int
    active_partner_count: int
    key_contacts: list[OrganizationContact]
    key_partners: list[PartnerOrganization]
    relationship_gaps: list[str]
    recommended_actions: list[str]
    health: RelationshipHealth
    opportunity_pathways: list[RelationshipPathway]
    relationship_impacts: list[RelationshipImpact]
    missing_relationships: list[RelationshipImpact]
    opportunity_mappings: list[RelationshipPathway]
    network_health: list[RelationshipNetworkIndicator]


SECTOR_RELATIONSHIPS = {
    "youth": {
        "terms": ["youth", "student", "students", "school", "afterschool", "teen", "young adult"],
        "missing": [
            ("School District Partner", ["student referrals", "youth services funding", "school partnership evidence"]),
            ("Youth Coalition", ["coalition grants", "program referrals", "community credibility"]),
            ("Community Foundation Youth Program Officer", ["youth development grants", "warm funder introductions"]),
        ],
    },
    "workforce": {
        "terms": [
            "workforce", "job", "jobs", "career", "employment", "training", "credential",
            "skills", "employer", "placement",
        ],
        "missing": [
            ("Regional Workforce Board", ["workforce funding programs", "employer coalitions", "training grants"]),
            ("Chamber of Commerce", ["employer introductions", "sponsorships", "workforce convenings"]),
            ("Employer Coalition", ["placement pathways", "mentors", "job-readiness credibility"]),
        ],
    },
    "health": {
        "terms": ["health", "healthcare", "clinic", "hospital", "wellness", "mental health", "public health"],
        "missing": [
            ("Public Health Department", ["public health grants", "referral pathways", "community health initiatives"]),
            ("Hospital System", ["community benefit funding", "clinical referrals", "health equity partnerships"]),
            ("Health Foundation", ["health grants", "evaluation support", "population health credibility"]),
        ],
    },
    "food": {
        "terms": ["food", "hunger", "pantry", "meal", "meals", "nutrition", "agriculture", "grocery"],
        "missing": [
            ("Regional Food Bank", ["collaborative grants", "food access initiatives", "distribution partnerships"]),
            ("Agricultural Network", ["fresh food partnerships", "nutrition programs", "local sourcing"]),
            ("Hunger Coalition", ["coalition funding", "policy visibility", "community referrals"]),
        ],
    },
    "environment": {
        "terms": [
            "environment", "environmental", "climate", "river", "watershed",
            "conservation", "sustainability", "green", "stewardship",
        ],
        "missing": [
            ("Watershed Organization", ["conservation grants", "stewardship projects", "place-based evidence"]),
            ("Conservation Network", ["environmental funders", "volunteer stewardship", "technical partners"]),
            ("Environmental Funder", ["environmental justice grants", "climate resilience funding"]),
        ],
    },
}


TYPE_PATHWAYS = {
    PartnerOrganization.PartnerType.GOVERNMENT_PARTNER: {
        "bridge": "Public Agency",
        "opportunities": ["city grants", "service contracts", "RFP visibility"],
        "outcomes": ["public-sector credibility", "local agency alignment", "contract readiness"],
    },
    PartnerOrganization.PartnerType.FUNDING_PARTNER: {
        "bridge": "Program Officer",
        "opportunities": ["foundation grants", "warm introductions", "restricted program funding"],
        "outcomes": ["funder trust", "proposal feedback", "stronger funding fit"],
    },
    PartnerOrganization.PartnerType.ACADEMIC_PARTNER: {
        "bridge": "Education Partner",
        "opportunities": ["credential pathways", "training grants", "student referral partnerships"],
        "outcomes": ["program credibility", "shared facilities", "participant pathways"],
    },
    PartnerOrganization.PartnerType.CORPORATE_PARTNER: {
        "bridge": "Employer Coalition",
        "opportunities": ["sponsorships", "mentors", "workforce funding programs"],
        "outcomes": ["career exposure", "placement credibility", "employer validation"],
    },
    PartnerOrganization.PartnerType.COMMUNITY_PARTNER: {
        "bridge": "Community Coalition",
        "opportunities": ["collaborative grants", "referral pathways", "neighborhood implementation"],
        "outcomes": ["community trust", "resident reach", "shared service delivery"],
    },
    PartnerOrganization.PartnerType.SERVICE_PARTNER: {
        "bridge": "Capacity Partner",
        "opportunities": ["technical assistance", "capacity-building programs", "readiness support"],
        "outcomes": ["stronger evidence", "better operations", "grant readiness"],
    },
}


def _level(score: int) -> str:
    if score >= 85:
        return "Strong"
    if score >= 70:
        return "Established"
    if score >= 50:
        return "Developing"
    return "Needs Attention"


def _relationship_score(contacts: list[OrganizationContact], partners: list[PartnerOrganization]) -> RelationshipHealth:
    active_contacts = [contact for contact in contacts if contact.status == OrganizationContact.Status.ACTIVE]
    active_partners = [partner for partner in partners if partner.status == PartnerOrganization.Status.ACTIVE]
    partner_types = {partner.partner_type for partner in active_partners}
    all_strengths = [item.relationship_strength for item in active_contacts + active_partners]
    strength_points = sum(STRENGTH_POINTS.get(strength, 0) for strength in all_strengths)
    possible_points = max(len(all_strengths) * 4, 1)

    score = 20
    score += min(len(active_contacts) * 5, 25)
    score += min(len(active_partners) * 6, 24)
    score += min(len(partner_types) * 4, 16)
    score += round((strength_points / possible_points) * 15)
    score = max(0, min(score, 100))

    strengths = []
    gaps = []
    if active_contacts:
        strengths.append("Active contacts are documented")
    else:
        gaps.append("No active contacts documented")
    if active_partners:
        strengths.append("Active partners are documented")
    else:
        gaps.append("No active partners documented")
    if len(partner_types) >= 4:
        strengths.append("Partner diversity is developing")
    else:
        gaps.append("Partner diversity is limited")
    if any(strength == OrganizationContact.RelationshipStrength.STRONG for strength in all_strengths):
        strengths.append("Strong relationships exist")
    else:
        gaps.append("No strong relationships documented")
    if not any(
        contact.contact_type in {
            OrganizationContact.ContactType.FUNDER,
            OrganizationContact.ContactType.PROGRAM_OFFICER,
        }
        for contact in active_contacts
    ):
        gaps.append("Funder and program officer contacts are missing")
    if not any(
        contact.contact_type == OrganizationContact.ContactType.GOVERNMENT_CONTACT
        for contact in active_contacts
    ):
        gaps.append("Government contacts are missing")

    if "Funder and program officer contacts are missing" in gaps:
        action = "Add funder and program officer contacts for priority opportunities."
    elif "Government contacts are missing" in gaps:
        action = "Add local government contacts tied to active public-sector opportunities."
    elif "No strong relationships documented" in gaps:
        action = "Identify which developing relationships can be strengthened this quarter."
    elif "Partner diversity is limited" in gaps:
        action = "Add partners across community, government, academic, and corporate lanes."
    else:
        action = "Use strong contacts to support introductions, references, and opportunity pursuit."

    return RelationshipHealth(
        score=score,
        level=_level(score),
        strengths=strengths[:5],
        gaps=gaps[:6],
        highest_leverage_action=action,
    )


def _strength_rank(value: str) -> int:
    return STRENGTH_POINTS.get(value, 0)


def _dedupe(values: list[str], limit: int = 5) -> list[str]:
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


def _project_text(project) -> str:
    organization = project.organization
    values = [
        organization.name,
        organization.mission,
        organization.organization_summary,
        project.programs,
        organization.organization_type,
        organization.city,
        organization.county,
        organization.state,
        *organization.focus_areas,
        *organization.beneficiaries,
        *organization.service_geographies,
        *organization.outcomes_and_impact,
        *organization.existing_partnerships,
    ]
    return "\n".join(str(value or "") for value in values).casefold()


def _sector_missing_relationships(project) -> list[tuple[str, list[str]]]:
    text = _project_text(project)
    scored = []
    for key, profile in SECTOR_RELATIONSHIPS.items():
        score = sum(1 for term in profile["terms"] if term in text)
        scored.append((score, key, profile["missing"]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if scored and scored[0][0] > 0:
        return scored[0][2]
    return [
        ("Community Foundation Program Officer", ["local grants", "funder introductions", "proposal feedback"]),
        ("Local Government Agency", ["public-sector funding", "service contracts", "RFP visibility"]),
        ("Anchor Institution Partner", ["credibility", "referrals", "collaborative opportunities"]),
    ]


def _impact_level(score: int) -> str:
    if score >= 85:
        return "High Impact"
    if score >= 65:
        return "Medium Impact"
    return "Low Impact"


def _relationship_terms(item) -> str:
    return " ".join([
        getattr(item, "organization_name", ""),
        getattr(item, "organization", ""),
        getattr(item, "partner_type", ""),
        getattr(item, "contact_type", ""),
        getattr(item, "notes", ""),
        getattr(item, "mission_alignment_notes", ""),
        getattr(item, "opportunity_notes", ""),
        getattr(item, "relationship_notes", ""),
    ]).casefold()


def _opportunities_for_terms(project, terms: str) -> list[str]:
    opportunities = []
    for opportunity in Opportunity.objects.exclude(status=Opportunity.Status.ARCHIVED):
        haystack = " ".join([
            opportunity.name,
            opportunity.source_name,
            opportunity.notes,
            opportunity.eligibility_notes,
            *opportunity.focus_areas,
            *opportunity.beneficiaries,
            *opportunity.geography,
        ]).casefold()
        if any(token and token in haystack for token in terms.split()):
            opportunities.append(opportunity.name)
        if len(opportunities) >= 3:
            break
    return opportunities or ["collaborative grants", "referral partnerships", "future opportunity introductions"]


def _relationship_impact_score(project, item) -> tuple[int, list[str]]:
    organization = project.organization
    text = _relationship_terms(item)
    score = 35
    factors = []
    if any(str(value).casefold() in text for value in organization.focus_areas or []):
        score += 18
        factors.append("mission alignment")
    if any(str(value).casefold() in text for value in organization.beneficiaries or []):
        score += 12
        factors.append("beneficiary alignment")
    geography = [organization.city, organization.county, organization.state, *organization.service_geographies]
    if any(str(value).casefold() in text for value in geography if value):
        score += 12
        factors.append("geographic alignment")
    strength = _strength_rank(item.relationship_strength)
    score += strength * 6
    if strength >= 3:
        factors.append("existing relationship strength")
    if isinstance(item, PartnerOrganization) and item.partner_type in TYPE_PATHWAYS:
        score += 8
        factors.append("partnership leverage")
    if isinstance(item, OrganizationContact) and item.contact_type in {
        OrganizationContact.ContactType.FUNDER,
        OrganizationContact.ContactType.PROGRAM_OFFICER,
        OrganizationContact.ContactType.GOVERNMENT_CONTACT,
        OrganizationContact.ContactType.CORPORATE_CONTACT,
    }:
        score += 8
        factors.append("ecosystem influence")
    return min(score, 98), _dedupe(factors, 4)


def _relationship_name(item) -> str:
    if isinstance(item, PartnerOrganization):
        return item.organization_name
    if item.organization:
        return f"{item.name} at {item.organization}"
    return item.name


def _relationship_pathways(project, partners: list[PartnerOrganization]) -> list[RelationshipPathway]:
    pathways = []
    for partner in partners:
        profile = TYPE_PATHWAYS.get(partner.partner_type, {
            "bridge": "Strategic Partner",
            "opportunities": ["collaborative grants", "referral partnerships", "shared program opportunities"],
            "outcomes": ["community trust", "mission reach", "implementation capacity"],
        })
        opportunity_categories = _dedupe(
            list(profile["opportunities"]) + [value for value in partner.opportunity_notes.replace(",", " ").split() if "grant" in value],
            4,
        )
        pathway = [
            partner.organization_name,
            profile["bridge"],
            opportunity_categories[0],
            "Opportunity pursuit",
        ]
        rationale = (
            partner.relationship_notes
            or partner.opportunity_notes
            or f"{partner.organization_name} can connect the mission to {', '.join(opportunity_categories[:2])}."
        )
        pathways.append(
            RelationshipPathway(
                relationship_name=partner.organization_name,
                pathway=pathway,
                rationale=rationale,
                expected_opportunity_categories=opportunity_categories,
                expected_partnership_outcomes=_dedupe(list(profile["outcomes"]), 4),
            )
        )
    return pathways[:5]


def _relationship_impacts(project, contacts: list[OrganizationContact], partners: list[PartnerOrganization]) -> list[RelationshipImpact]:
    candidates = []
    for item in [*partners, *contacts]:
        score, factors = _relationship_impact_score(project, item)
        opportunities = _opportunities_for_terms(project, _relationship_terms(item))
        rationale = f"Prioritized because of {', '.join(factors) or 'documented relationship context'}."
        candidates.append((
            -score,
            _relationship_name(item).casefold(),
            RelationshipImpact(
                name=_relationship_name(item),
                impact_level=_impact_level(score),
                score=score,
                rationale=rationale,
                opportunities_unlocked=_dedupe(opportunities, 3),
            ),
        ))
    candidates.sort(key=lambda row: (row[0], row[1]))
    return [item for _score, _name, item in candidates[:6]]


def _missing_relationship_impacts(project, active_contacts, active_partners) -> list[RelationshipImpact]:
    known_text = " ".join(
        [_relationship_terms(item) for item in [*active_contacts, *active_partners]]
    ).casefold()
    missing = []
    for name, unlocks in _sector_missing_relationships(project):
        if name.casefold() in known_text:
            continue
        score = 82 if any(term in name.casefold() for term in ["workforce", "school", "health", "food", "watershed"]) else 74
        missing.append(
            RelationshipImpact(
                name=name,
                impact_level=_impact_level(score),
                score=score,
                rationale=f"Missing relationship that could unlock {', '.join(unlocks[:2])}.",
                opportunities_unlocked=unlocks,
            )
        )
    return missing[:4]


def _network_health(active_contacts, active_partners) -> list[RelationshipNetworkIndicator]:
    contact_types = {contact.contact_type for contact in active_contacts}
    partner_types = {partner.partner_type for partner in active_partners}
    strong_items = [
        item for item in [*active_contacts, *active_partners]
        if item.relationship_strength == OrganizationContact.RelationshipStrength.STRONG
    ]
    indicators = [
        RelationshipNetworkIndicator(
            "Community Partnerships",
            "Strong" if PartnerOrganization.PartnerType.COMMUNITY_PARTNER in partner_types else "Developing",
            "Community partners strengthen trust, referrals, and implementation reach.",
        ),
        RelationshipNetworkIndicator(
            "Government Relationships",
            "Strong" if OrganizationContact.ContactType.GOVERNMENT_CONTACT in contact_types
            or PartnerOrganization.PartnerType.GOVERNMENT_PARTNER in partner_types else "Weak",
            "Government relationships can unlock grants, service contracts, and RFP visibility.",
        ),
        RelationshipNetworkIndicator(
            "Funding Relationships",
            "Strong" if OrganizationContact.ContactType.PROGRAM_OFFICER in contact_types
            or PartnerOrganization.PartnerType.FUNDING_PARTNER in partner_types else "Missing",
            "Funding relationships support warm introductions, fit feedback, and proposal credibility.",
        ),
        RelationshipNetworkIndicator(
            "Regional Coalitions",
            "Strong" if len(partner_types) >= 4 and strong_items else "Developing",
            "Coalitions expand reach and make collaborative opportunities more credible.",
        ),
    ]
    return indicators


def build_relationship_overview(project) -> RelationshipOverview:
    contacts = list(project.organization_contacts.all())
    partners = list(project.relationship_partners.all())
    active_contacts = [contact for contact in contacts if contact.status == OrganizationContact.Status.ACTIVE]
    active_partners = [partner for partner in partners if partner.status == PartnerOrganization.Status.ACTIVE]
    strong_relationships = sum(
        1
        for item in active_contacts + active_partners
        if item.relationship_strength == OrganizationContact.RelationshipStrength.STRONG
    )
    developing_relationships = sum(
        1
        for item in active_contacts + active_partners
        if item.relationship_strength == OrganizationContact.RelationshipStrength.DEVELOPING
    )
    key_contacts = sorted(
        active_contacts,
        key=lambda contact: (-_strength_rank(contact.relationship_strength), contact.name),
    )[:5]
    key_partners = sorted(
        active_partners,
        key=lambda partner: (-_strength_rank(partner.relationship_strength), partner.organization_name),
    )[:5]
    health = _relationship_score(contacts, partners)
    actions = [health.highest_leverage_action]
    if active_contacts:
        actions.append("Map known contacts to the highest-priority opportunities.")
    if active_partners:
        actions.append("Use active partners for referrals, letters, and delivery credibility.")
    actions.append("Review relationship gaps before pursuing large grants, contracts, or partnerships.")
    opportunity_pathways = _relationship_pathways(project, key_partners)
    relationship_impacts = _relationship_impacts(project, key_contacts, key_partners)
    missing_relationships = _missing_relationship_impacts(project, active_contacts, active_partners)
    return RelationshipOverview(
        total_contacts=len(contacts),
        total_partners=len(partners),
        strong_relationships=strong_relationships,
        developing_relationships=developing_relationships,
        active_partner_count=len(active_partners),
        key_contacts=key_contacts,
        key_partners=key_partners,
        relationship_gaps=health.gaps,
        recommended_actions=actions[:5],
        health=health,
        opportunity_pathways=opportunity_pathways,
        relationship_impacts=relationship_impacts,
        missing_relationships=missing_relationships,
        opportunity_mappings=opportunity_pathways,
        network_health=_network_health(active_contacts, active_partners),
    )


def build_opportunity_relationship_context(project, opportunity: Opportunity) -> RelationshipContext:
    source_name = ""
    if opportunity.source_organization:
        source_name = opportunity.source_organization.name
    elif opportunity.source_name:
        source_name = opportunity.source_name
    source_key = source_name.casefold()
    contacts = list(project.organization_contacts.filter(status=OrganizationContact.Status.ACTIVE))
    partners = list(project.relationship_partners.filter(status=PartnerOrganization.Status.ACTIVE))

    related_contacts = [
        contact
        for contact in contacts
        if source_key and (
            source_key in contact.organization.casefold()
            or contact.organization.casefold() in source_key
        )
    ]
    related_partners = [
        partner
        for partner in partners
        if source_key and (
            source_key in partner.organization_name.casefold()
            or partner.organization_name.casefold() in source_key
        )
    ]
    if not related_contacts:
        related_contacts = contacts[:2]
    if not related_partners:
        related_partners = partners[:2]

    all_strengths = [item.relationship_strength for item in related_contacts + related_partners]
    best_strength = max((_strength_rank(value) for value in all_strengths), default=0)
    if best_strength >= 4:
        label = "Strong Relationship"
    elif best_strength >= 2:
        label = "Developing Relationship"
    elif related_contacts or related_partners:
        label = "Known Contact"
    else:
        label = "No Contact"
    if label == "No Contact":
        action = "Identify a contact or partner before advancing this opportunity."
    elif label == "Known Contact":
        action = "Confirm the right contact and relationship owner."
    else:
        action = "Use this relationship context to support pursuit planning."
    return RelationshipContext(
        related_contacts=related_contacts[:4],
        related_partners=related_partners[:4],
        relationship_label=label,
        compact_status=label,
        recommended_action=action,
    )
