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
