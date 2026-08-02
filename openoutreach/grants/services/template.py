"""The standard Atlas grant template.

V1 ships one reusable 14-section template. The shape is deliberately data-driven
(a list of ``SectionSpec``) rather than hardcoded into models or views, so a
future version can add, remove, reorder, or swap in a funder's real questions by
supplying a different section list to ``sections_for()`` — no schema change.

Each spec declares:

- ``fact_keys``      which organization/opportunity facts the drafter may use
- ``requirements``   what has to be TRUE for Atlas to write this section well
                     (resolved against real data in ``context_builder``)
- ``library_category`` where an approved answer lands in the Answer Library
"""
from __future__ import annotations

from dataclasses import dataclass, field

from openoutreach.grants.models import GrantAnswerLibraryItem


@dataclass(frozen=True)
class SectionSpec:
    key: str
    title: str
    question: str
    guidance: tuple[str, ...]
    library_category: str
    fact_keys: tuple[str, ...] = ()
    requirements: tuple[str, ...] = ()
    required: bool = True
    word_limit: int | None = None
    character_limit: int | None = None
    # Extra instruction handed to the drafting agent for this section only.
    drafting_note: str = ""
    order: int = 0


_CATEGORY = GrantAnswerLibraryItem.Category


STANDARD_TEMPLATE: tuple[SectionSpec, ...] = (
    SectionSpec(
        key="organization_overview",
        title="Organization Overview",
        question="Describe your organization, including its mission, structure, and the work it does.",
        guidance=(
            "Who the organization is and what it exists to do",
            "Legal status and organization type",
            "Geographic service area",
            "Primary programs currently operating",
            "Who the organization serves",
        ),
        library_category=_CATEGORY.ORGANIZATION_OVERVIEW,
        fact_keys=(
            "organization.name", "organization.mission", "organization.summary",
            "organization.type", "organization.nonprofit_status", "organization.location",
            "organization.service_geographies", "organization.focus_areas",
            "organization.beneficiaries", "project.programs",
        ),
        requirements=("nonprofit_status", "service_area"),
        order=10,
    ),
    SectionSpec(
        key="organizational_history",
        title="Organizational History",
        question="Provide a brief history of your organization, including when it was founded and how it has grown.",
        guidance=(
            "Founding year and founding purpose",
            "How the work has evolved since then",
            "Major milestones or growth in reach",
            "Track record relevant to this request",
        ),
        library_category=_CATEGORY.ORGANIZATION_HISTORY,
        fact_keys=(
            "organization.name", "organization.summary", "organization.year_founded",
            "organization.mission", "project.programs", "evidence.past_performance",
        ),
        requirements=("year_founded", "past_performance"),
        order=20,
    ),
    SectionSpec(
        key="mission",
        title="Mission",
        question="State your organization's mission.",
        guidance=(
            "The mission in the organization's own words",
            "Who it serves and toward what change",
            "Kept short — most funders cap this tightly",
        ),
        library_category=_CATEGORY.MISSION,
        fact_keys=("organization.name", "organization.mission", "organization.beneficiaries"),
        word_limit=120,
        order=30,
    ),
    SectionSpec(
        key="statement_of_need",
        title="Statement of Need",
        question=(
            "Describe the problem your organization seeks to address and provide evidence "
            "demonstrating the need."
        ),
        guidance=(
            "The population affected",
            "The geographic area",
            "The size of the problem, with a supporting figure",
            "Evidence for the claim, and where it came from",
            "The service gap that currently exists",
            "Why this organization is positioned to respond",
        ),
        library_category=_CATEGORY.STATEMENT_OF_NEED,
        fact_keys=(
            "organization.mission", "organization.beneficiaries", "organization.location",
            "organization.service_geographies", "organization.focus_areas",
            "evidence.community_need", "opportunity.focus_areas", "opportunity.beneficiaries",
        ),
        requirements=("community_need_data", "service_area"),
        drafting_note=(
            "A statement of need is only credible with a real, sourced figure. If no "
            "community-need data is supplied, say so explicitly instead of estimating."
        ),
        order=40,
    ),
    SectionSpec(
        key="population_served",
        title="Population Served",
        question="Describe the population your organization serves, including demographics and how many people you reach.",
        guidance=(
            "Who is served, described concretely",
            "Number of people served annually",
            "Demographics relevant to this funder",
            "How participants are reached or referred",
        ),
        library_category=_CATEGORY.POPULATION_SERVED,
        fact_keys=(
            "organization.beneficiaries", "organization.service_geographies",
            "organization.location", "evidence.people_served", "project.programs",
        ),
        requirements=("people_served_annually",),
        order=50,
    ),
    SectionSpec(
        key="program_description",
        title="Program / Project Description",
        question="Describe the program or project for which you are requesting funding.",
        guidance=(
            "What the program actually does, activity by activity",
            "Who delivers it and where",
            "How participants move through it",
            "How it connects to this funder's priorities",
        ),
        library_category=_CATEGORY.PROGRAM_DESCRIPTION,
        fact_keys=(
            "project.name", "project.programs", "project.program_summaries",
            "organization.capabilities", "organization.focus_areas",
            "opportunity.name", "opportunity.focus_areas", "opportunity.eligibility_notes",
        ),
        order=60,
    ),
    SectionSpec(
        key="goals_and_objectives",
        title="Goals and Objectives",
        question="State the goals and measurable objectives of the proposed program.",
        guidance=(
            "Goals stated as the change being pursued",
            "Objectives that are specific and measurable",
            "A target number or percentage for each objective",
            "A timeframe tied to the grant period",
        ),
        library_category=_CATEGORY.GOALS,
        fact_keys=(
            "project.programs", "organization.outcomes", "evidence.outcome_metrics",
            "opportunity.focus_areas",
        ),
        requirements=("measurable_outcomes",),
        drafting_note=(
            "Objectives must be measurable. Where no baseline or target exists in the "
            "supplied facts, mark the number as information needed rather than choosing one."
        ),
        order=70,
    ),
    SectionSpec(
        key="implementation_plan",
        title="Implementation Plan",
        question="Describe how the program will be implemented, including timeline and key activities.",
        guidance=(
            "Major activities in sequence",
            "Who is responsible for each",
            "Timeline across the grant period",
            "Key milestones the funder can check against",
        ),
        library_category=_CATEGORY.IMPLEMENTATION_PLAN,
        fact_keys=(
            "project.programs", "organization.capabilities", "opportunity.deadline",
            "documents.available",
        ),
        requirements=("staffing",),
        order=80,
    ),
    SectionSpec(
        key="outcomes_and_measurement",
        title="Outcomes and Measurement",
        question="Describe the expected outcomes and how you will measure and evaluate them.",
        guidance=(
            "Outcomes expected, stated as participant-level change",
            "The measure or instrument used for each",
            "How data is collected and how often",
            "Who reviews results and how they are used",
        ),
        library_category=_CATEGORY.OUTCOMES,
        fact_keys=(
            "organization.outcomes", "evidence.outcome_metrics", "evidence.evaluation",
            "project.programs",
        ),
        requirements=("measurable_outcomes", "evaluation_approach"),
        order=90,
    ),
    SectionSpec(
        key="organizational_capacity",
        title="Organizational Capacity",
        question="Describe your organization's capacity to carry out the proposed work.",
        guidance=(
            "Staffing and key roles delivering the work",
            "Relevant experience running comparable programs",
            "Systems, facilities, and infrastructure in place",
            "Board and leadership oversight",
        ),
        library_category=_CATEGORY.ORGANIZATIONAL_CAPACITY,
        fact_keys=(
            "organization.capabilities", "organization.summary", "project.programs",
            "evidence.past_performance", "documents.available", "evidence.leadership",
        ),
        requirements=("staffing", "leadership"),
        order=100,
    ),
    SectionSpec(
        key="partnerships",
        title="Partnerships",
        question="Describe the partnerships and collaborations that support this work.",
        guidance=(
            "Named partner organizations",
            "What each partner actually contributes",
            "How long the relationship has existed",
            "Whether letters of support are available",
        ),
        library_category=_CATEGORY.PARTNERSHIPS,
        fact_keys=(
            "organization.partnerships", "evidence.partner_letters", "project.programs",
        ),
        requirements=("partnerships",),
        order=110,
    ),
    SectionSpec(
        key="sustainability",
        title="Sustainability",
        question="Describe how the program will be sustained beyond this grant period.",
        guidance=(
            "Other funding currently supporting the work",
            "Plans for diversifying revenue",
            "What continues if this grant is not renewed",
            "Earned revenue, in-kind, or partner contributions",
        ),
        library_category=_CATEGORY.SUSTAINABILITY,
        fact_keys=(
            "organization.funding_sources", "organization.partnerships",
            "evidence.sustainability", "organization.budget_range",
        ),
        requirements=("funding_history", "sustainability_plan"),
        order=120,
    ),
    SectionSpec(
        key="budget_narrative",
        title="Budget Narrative",
        question="Provide a narrative explanation of the proposed budget.",
        guidance=(
            "The amount requested and what it covers",
            "Major cost categories, explained",
            "How the request relates to the total program budget",
            "Other committed or pending funding for the same work",
        ),
        library_category=_CATEGORY.BUDGET_NARRATIVE,
        fact_keys=(
            "organization.budget_range", "organization.funding_sources",
            "opportunity.funding_amount", "application.requested_amount",
            "documents.budget",
        ),
        requirements=("operating_budget", "program_budget"),
        drafting_note=(
            "Never state a dollar figure, line item, or personnel cost that is not "
            "present in the supplied facts. Budget invention is the fastest way to "
            "lose a funder's trust."
        ),
        order=130,
    ),
    SectionSpec(
        key="additional_information",
        title="Additional Information",
        question="Provide any additional information you would like the funder to consider.",
        guidance=(
            "Anything material the standard sections did not cover",
            "Recent recognition, awards, or coverage",
            "Context specific to this funder's priorities",
        ),
        library_category=_CATEGORY.OTHER,
        fact_keys=("organization.summary", "evidence.past_performance", "opportunity.notes"),
        required=False,
        order=140,
    ),
)


SECTIONS_BY_KEY: dict[str, SectionSpec] = {spec.key: spec for spec in STANDARD_TEMPLATE}


def sections_for(_opportunity=None) -> tuple[SectionSpec, ...]:
    """Return the section list for an opportunity.

    V1 always returns the standard template. The seam exists so funder-specific
    templates (parsed from a real application, see docs/grant_builder/README.md)
    can be returned here later without touching models, views, or the drafter.
    """
    return STANDARD_TEMPLATE


def spec_for(section_key: str) -> SectionSpec | None:
    return SECTIONS_BY_KEY.get(section_key)


@dataclass(frozen=True)
class RequirementSpec:
    """A fact Atlas must actually hold before a section can be written well."""

    key: str
    label: str
    hint: str
    # Named destination in the portal where the client can supply it.
    add_url_name: str = "project-organization"
    add_label: str = "Add Information"
    fields: tuple[str, ...] = field(default_factory=tuple)


REQUIREMENTS: dict[str, RequirementSpec] = {
    spec.key: spec
    for spec in (
        RequirementSpec(
            "nonprofit_status", "IRS / nonprofit status",
            "Funders confirm eligibility first. Record your determination letter or tax status.",
            add_url_name="project-documents", add_label="Add to Document Vault",
        ),
        RequirementSpec(
            "service_area", "Defined service area",
            "The county, city, or region you serve — this drives both eligibility and need.",
        ),
        RequirementSpec(
            "year_founded", "Year founded",
            "Add your founding year to your organization summary.",
        ),
        RequirementSpec(
            "past_performance", "Track record or prior results",
            "Past program results a funder can check. Add them to your Evidence Library.",
            add_url_name="project-evidence", add_label="Add Evidence",
        ),
        RequirementSpec(
            "community_need_data", "Local supporting statistic",
            "A sourced figure describing the need in your area — census, county health, school district.",
            add_url_name="project-evidence", add_label="Add Evidence",
        ),
        RequirementSpec(
            "people_served_annually", "Number of people served annually",
            "Record how many people you reach in a year as an outcome metric.",
            add_url_name="project-evidence", add_label="Add Evidence",
        ),
        RequirementSpec(
            "measurable_outcomes", "Two measurable program outcomes",
            "Outcomes with a number attached — completion rates, placements, score changes.",
            add_url_name="project-evidence", add_label="Add Evidence",
        ),
        RequirementSpec(
            "evaluation_approach", "Evaluation approach",
            "How you measure results: tools, cadence, and who reviews the data.",
            add_url_name="project-evidence", add_label="Add Evidence",
        ),
        RequirementSpec(
            "staffing", "Program staffing",
            "Who delivers the work — roles, headcount, or FTE.",
            add_url_name="project-evidence", add_label="Add Evidence",
        ),
        RequirementSpec(
            "leadership", "Leadership and board",
            "Executive leadership and board roster.",
            add_url_name="project-documents", add_label="Add to Document Vault",
        ),
        RequirementSpec(
            "partnerships", "Documented partnerships",
            "Named partners and what each contributes.",
        ),
        RequirementSpec(
            "funding_history", "Current funding sources",
            "What currently funds this work — funders look for a base to build on.",
        ),
        RequirementSpec(
            "sustainability_plan", "Sustainability plan",
            "What keeps the program running after this grant ends.",
            add_url_name="project-evidence", add_label="Add Evidence",
        ),
        RequirementSpec(
            "operating_budget", "Current annual operating budget",
            "Your annual operating budget or budget range.",
        ),
        RequirementSpec(
            "program_budget", "Program or annual budget document",
            "A budget document a funder can be pointed to.",
            add_url_name="project-documents", add_label="Add to Document Vault",
        ),
    )
}
