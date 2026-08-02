"""Atlas Grant Builder — behaviour that has to hold.

The load-bearing tests here are the ones about trust: AI drafts are never
approved by default, approved answers cannot be silently overwritten, invented
figures are caught, and no query can reach another organization's data.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import (
    DocumentVaultItem,
    EvidenceLibraryItem,
    Opportunity,
)
from openoutreach.grants.models import (
    GrantAnswerLibraryItem,
    GrantApplication,
    GrantApplicationSection,
)
from openoutreach.grants.services import answer_library, completeness, grant_coach
from openoutreach.grants.services.applications import start_grant_application, sync_sections
from openoutreach.grants.services.context_builder import build_grant_context
from openoutreach.grants.services.draft_generator import SectionDraft
from openoutreach.grants.services.template import STANDARD_TEMPLATE, spec_for
from openoutreach.signals.demo import seed_missionsignal_demo

pytestmark = pytest.mark.django_db


@pytest.fixture
def grant_project(db):
    user, _organization, project = seed_missionsignal_demo()
    Opportunity.objects.update(project=project)
    opportunity = Opportunity.objects.get(name="Youth Opportunity Grant")
    return project, user, opportunity


@pytest.fixture
def application(grant_project):
    """A draft on the fully-populated demo organization."""
    project, user, opportunity = grant_project
    app, _created = start_grant_application(project, opportunity, user=user)
    return app


@pytest.fixture
def sparse_application(db):
    """A draft on a brand-new organization — mission and programs, nothing else.

    This is what a real client looks like on day one, and the only honest place
    to test gap detection: the demo seed already ships evidence and documents,
    so asserting "missing" against it would test the seeder, not the feature.
    """
    user = get_user_model().objects.create_user(username="new-ed", password="x")
    organization = Organization.objects.create(
        name="New Horizons Collective",
        website="https://newhorizons.example.org",
        mission="Prepare Orlando teens for their first job.",
        city="Orlando", county="Orange", state="Florida",
        beneficiaries=["youth"],
    )
    organization.users.add(user)
    project = Project.objects.create(
        organization=organization, name="Workforce Initiative",
        programs="After-school job readiness workshops.",
    )
    project.users.add(user)
    opportunity = Opportunity.objects.create(
        project=project, name="Community Impact Grant",
        source_name="Example Foundation",
        focus_areas=["workforce development"],
        geography=["Orange County"],
    )
    app, _created = start_grant_application(project, opportunity, user=user)
    return app


def _other_org_project():
    """A completely separate organization, project, and member."""
    user = get_user_model().objects.create_user(username="rival-ed", password="x")
    organization = Organization.objects.create(
        name="Rival Nonprofit", website="https://rival.example.org", mission="Different mission",
    )
    organization.users.add(user)
    project = Project.objects.create(
        organization=organization, name="Rival Initiative", programs="Different programs",
    )
    project.users.add(user)
    return project, user


# ── Starting and reopening ───────────────────────────────────────────────────

def test_start_grant_draft_creates_workspace_with_full_template(grant_project):
    project, user, opportunity = grant_project

    app, created = start_grant_application(project, opportunity, user=user)

    assert created is True
    assert app.title == opportunity.name
    assert app.status == GrantApplication.Status.DRAFTING
    assert app.sections.count() == len(STANDARD_TEMPLATE)
    assert app.sections.filter(section_key="statement_of_need").exists()
    # Nothing is written until a person or the drafter acts.
    assert all(
        section.status == GrantApplicationSection.Status.NOT_STARTED
        for section in app.sections.all()
    )


def test_starting_twice_continues_the_same_draft(grant_project):
    project, user, opportunity = grant_project

    first, created_first = start_grant_application(project, opportunity, user=user)
    second, created_second = start_grant_application(project, opportunity, user=user)

    assert created_first is True
    assert created_second is False
    assert first.pk == second.pk
    assert GrantApplication.objects.filter(project=project).count() == 1
    assert second.sections.count() == len(STANDARD_TEMPLATE)


def test_sync_sections_does_not_rewrite_existing_answers(application):
    section = application.sections.get(section_key="mission")
    section.approved_response = "A human wrote this."
    section.funder_question = "Funder's own wording."
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()

    sync_sections(application)

    section.refresh_from_db()
    assert section.approved_response == "A human wrote this."
    assert section.funder_question == "Funder's own wording."


def test_start_grant_draft_view_and_continue_button(client, grant_project):
    project, user, opportunity = grant_project
    client.force_login(user)

    response = client.post(
        reverse("project-grant-start", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    )
    assert response.status_code == 302

    workspace = client.get(
        reverse("project-opportunity-workspace",
                kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    )
    assert "Continue Grant Draft" in workspace.content.decode()


# ── Permissions / cross-organization isolation ───────────────────────────────

def test_another_organization_cannot_open_a_grant_draft(client, application):
    _rival_project, rival_user = _other_org_project()
    client.force_login(rival_user)

    response = client.get(
        reverse("project-grant-overview",
                kwargs={"pk": application.project_id, "application_id": application.pk}),
    )

    assert response.status_code == 404


def test_grant_draft_is_not_reachable_through_another_project_id(client, application):
    rival_project, rival_user = _other_org_project()
    client.force_login(rival_user)

    response = client.get(
        reverse("project-grant-overview",
                kwargs={"pk": rival_project.pk, "application_id": application.pk}),
    )

    assert response.status_code == 404


def test_answer_library_never_returns_another_organizations_answers(application):
    rival_project, rival_user = _other_org_project()
    GrantAnswerLibraryItem.objects.create(
        organization=rival_project.organization,
        category=GrantAnswerLibraryItem.Category.MISSION,
        title="Rival mission", answer="Their words, not yours.", created_by=rival_user,
    )

    ours = answer_library.library_for(application.project.organization)

    assert ours.count() == 0
    assert answer_library.library_for(rival_project.organization).count() == 1


def test_reuse_rejects_a_library_item_from_another_organization(client, application):
    rival_project, rival_user = _other_org_project()
    theirs = GrantAnswerLibraryItem.objects.create(
        organization=rival_project.organization,
        category=GrantAnswerLibraryItem.Category.MISSION,
        title="Rival mission", answer="Their words.", created_by=rival_user,
    )
    client.force_login(application.created_by)

    response = client.post(
        reverse("project-grant-library-reuse", kwargs={
            "pk": application.project_id, "application_id": application.pk, "item_id": theirs.pk,
        }),
        {"section_key": "mission"},
    )

    assert response.status_code == 404


# ── Prefill from existing Atlas data ─────────────────────────────────────────

def test_context_reuses_organization_and_project_data(application):
    context = build_grant_context(application)

    assert context.fact("organization.mission") is not None
    assert context.fact("project.programs") is not None
    assert "Orlando" in context.fact("organization.location").value
    # Labels are human-readable, not database field names.
    assert context.fact("organization.mission").label == "Organization Mission"
    assert "Organization Mission" in context.available_labels(["organization.mission"])


def test_a_populated_organization_needs_nothing_for_population_served(application):
    """The demo organization already records who it serves — no gap to report."""
    context = build_grant_context(application)

    assert context.missing_for(spec_for("population_served").requirements) == []


def test_missing_information_is_named_not_invented(sparse_application):
    context = build_grant_context(sparse_application)
    spec = spec_for("population_served")

    missing = context.missing_for(spec.requirements)

    assert [item.label for item in missing] == ["Number of people served annually"]
    assert missing[0].add_url_name == "project-evidence"
    assert missing[0].hint  # every gap tells the client how to close it


def test_evidence_library_resolves_the_missing_requirement(sparse_application):
    assert build_grant_context(sparse_application).resolved_requirements[
        "people_served_annually"
    ] is False

    EvidenceLibraryItem.objects.create(
        project=sparse_application.project,
        title="Youth served annually",
        evidence_type=EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC,
        metric_name="Youth served annually",
        metric_value="412",
        status=EvidenceLibraryItem.Status.AVAILABLE,
    )

    context = build_grant_context(sparse_application)

    assert context.resolved_requirements["people_served_annually"] is True
    assert context.missing_for(spec_for("population_served").requirements) == []
    assert "412" in context.supported_numbers


def test_document_vault_resolves_the_budget_requirement(sparse_application):
    assert build_grant_context(sparse_application).resolved_requirements["program_budget"] is False

    DocumentVaultItem.objects.create(
        project=sparse_application.project,
        title="FY2026 annual budget",
        document_type=DocumentVaultItem.DocumentType.ANNUAL_BUDGET,
        status=DocumentVaultItem.Status.AVAILABLE,
    )

    context = build_grant_context(sparse_application)

    assert context.resolved_requirements["program_budget"] is True


def test_requirement_coverage_reflects_how_much_atlas_actually_holds(application, sparse_application):
    populated = build_grant_context(application).requirement_coverage
    bare = build_grant_context(sparse_application).requirement_coverage

    assert 0 <= bare < populated <= 100


# ── Draft generation + anti-fabrication ──────────────────────────────────────

def _fake_draft(response, sources=(), missing=()):
    return SectionDraft(
        response=response, sources_used=list(sources), missing_information=list(missing),
    )


def test_generate_draft_saves_to_the_draft_column_and_records_sources(client, application):
    client.force_login(application.created_by)
    draft = _fake_draft("Draft body about the organization's mission.", ["Organization Mission"])

    with patch("openoutreach.grants.services.draft_generator._agent"), \
         patch("openoutreach.grants.services.draft_generator._run", return_value=draft):
        response = client.post(reverse("project-grant-section-generate", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
        }))

    assert response.status_code == 302
    section = application.sections.get(section_key="mission")
    assert section.draft_response == "Draft body about the organization's mission."
    assert section.approved_response == ""
    assert section.status != GrantApplicationSection.Status.APPROVED
    assert any(item["label"] == "Organization Mission" for item in section.source_fields)
    assert section.last_generated_at is not None


def test_the_drafting_prompt_carries_only_real_facts(application):
    section = application.sections.get(section_key="mission")
    spec = spec_for("mission")
    context = build_grant_context(application)
    captured = {}

    def _capture(_agent, prompt):
        captured["prompt"] = prompt
        return _fake_draft("ok")

    from openoutreach.grants.services import draft_generator

    with patch.object(draft_generator, "_agent"), patch.object(draft_generator, "_run", _capture):
        draft_generator.generate_section_draft(section, context, spec)

    prompt = captured["prompt"]
    assert application.project.organization.mission[:40] in prompt
    assert "ORGANIZATION FACTS" in prompt


def test_generation_flags_a_section_that_is_missing_information(client, sparse_application):
    client.force_login(sparse_application.created_by)
    draft = _fake_draft("We serve [Information needed: annual participant count] young people.")

    with patch("openoutreach.grants.services.draft_generator._agent"), \
         patch("openoutreach.grants.services.draft_generator._run", return_value=draft):
        client.post(reverse("project-grant-section-generate", kwargs={
            "pk": sparse_application.project_id, "application_id": sparse_application.pk,
            "section_key": "population_served",
        }))

    section = sparse_application.sections.get(section_key="population_served")
    assert section.status == GrantApplicationSection.Status.NEEDS_INFORMATION
    assert "Number of people served annually" in section.missing_information


def test_unsupported_figures_are_detected(application):
    context = build_grant_context(application)

    unsupported = grant_coach.unsupported_numbers(
        "We served 4,318 youth last year on a $2,500,000 budget.", context,
    )

    assert "4318" in unsupported
    assert "2500000" in unsupported


def test_a_figure_the_organization_supplied_is_not_flagged(application):
    EvidenceLibraryItem.objects.create(
        project=application.project,
        title="Youth served annually",
        evidence_type=EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC,
        metric_name="Youth served annually", metric_value="412",
        status=EvidenceLibraryItem.Status.AVAILABLE,
    )
    context = build_grant_context(application)

    assert grant_coach.unsupported_numbers("We served 412 youth last year.", context) == []


def test_information_needed_markers_are_not_treated_as_claims(application):
    context = build_grant_context(application)

    assert grant_coach.unsupported_numbers(
        "We served [Information needed: 2025 participant count] youth.", context,
    ) == []


def test_the_coach_reports_an_unsupported_claim_on_the_section(sparse_application):
    application = sparse_application
    section = application.sections.get(section_key="statement_of_need")
    section.approved_response = "Some 9,412 residents live below the poverty line."
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()
    context = build_grant_context(application)

    review = grant_coach.review_section(section, context, spec_for("statement_of_need"))

    kinds = {finding.kind for finding in review.findings}
    assert grant_coach.UNSUPPORTED_CLAIM in kinds
    assert grant_coach.MISSING_EVIDENCE in kinds


# ── Approval — AI never overwrites a person ──────────────────────────────────

def test_approving_moves_text_into_the_approved_column(client, application):
    client.force_login(application.created_by)

    client.post(
        reverse("project-grant-section-save", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
        }),
        {"intent": "approve", "response": "Our approved mission statement."},
    )

    section = application.sections.get(section_key="mission")
    assert section.status == GrantApplicationSection.Status.APPROVED
    assert section.approved_response == "Our approved mission statement."
    assert section.draft_response == ""
    assert section.approved_by == application.created_by
    assert section.approved_at is not None


def test_regenerating_never_touches_an_approved_answer(client, application):
    client.force_login(application.created_by)
    client.post(
        reverse("project-grant-section-save", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
        }),
        {"intent": "approve", "response": "The approved wording a human signed off."},
    )

    with patch("openoutreach.grants.services.draft_generator._agent"), \
         patch("openoutreach.grants.services.draft_generator._run",
               return_value=_fake_draft("A brand new AI draft.")):
        client.post(reverse("project-grant-section-generate", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
        }))

    section = application.sections.get(section_key="mission")
    assert section.approved_response == "The approved wording a human signed off."
    assert section.draft_response == "A brand new AI draft."
    assert section.current_text == "The approved wording a human signed off."
    # The status must survive too — otherwise regenerating silently un-approves
    # the section and quietly drops the application's completion.
    assert section.status == GrantApplicationSection.Status.APPROVED
    assert section.is_approved is True


def test_unapprove_returns_the_text_as_a_draft(client, application):
    client.force_login(application.created_by)
    save_url = reverse("project-grant-section-save", kwargs={
        "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
    })
    client.post(save_url, {"intent": "approve", "response": "Approved text."})

    client.post(save_url, {"intent": "unapprove"})

    section = application.sections.get(section_key="mission")
    assert section.status == GrantApplicationSection.Status.DRAFTED
    assert section.approved_response == ""
    assert section.draft_response == "Approved text."


# ── Answer Library ───────────────────────────────────────────────────────────

def test_only_an_approved_answer_can_be_saved_to_the_library(application):
    section = application.sections.get(section_key="mission")
    section.draft_response = "Unreviewed AI text."
    section.status = GrantApplicationSection.Status.DRAFTED
    section.save()

    with pytest.raises(ValueError):
        answer_library.save_section_to_library(section)


def test_saving_and_reusing_a_library_answer(client, application):
    client.force_login(application.created_by)
    client.post(
        reverse("project-grant-section-save", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
        }),
        {"intent": "approve", "response": "Our approved mission statement."},
    )
    client.post(
        reverse("project-grant-library-save", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
        }),
        {"title": "Standard mission"},
    )

    item = GrantAnswerLibraryItem.objects.get(title="Standard mission")
    assert item.organization == application.project.organization
    assert item.answer == "Our approved mission statement."
    assert item.category == GrantAnswerLibraryItem.Category.MISSION

    client.post(
        reverse("project-grant-library-reuse", kwargs={
            "pk": application.project_id, "application_id": application.pk, "item_id": item.pk,
        }),
        {"section_key": "organization_overview", "mode": "append"},
    )

    target = application.sections.get(section_key="organization_overview")
    assert "Our approved mission statement." in target.draft_response
    assert target.approved_response == ""
    item.refresh_from_db()
    assert item.answer == "Our approved mission statement."  # original untouched


def test_reuse_will_not_clobber_an_approved_section(client, application):
    client.force_login(application.created_by)
    item = GrantAnswerLibraryItem.objects.create(
        organization=application.project.organization,
        category=GrantAnswerLibraryItem.Category.MISSION,
        title="Library answer", answer="Library text.",
    )
    client.post(
        reverse("project-grant-section-save", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "mission",
        }),
        {"intent": "approve", "response": "Human approved text."},
    )

    client.post(
        reverse("project-grant-library-reuse", kwargs={
            "pk": application.project_id, "application_id": application.pk, "item_id": item.pk,
        }),
        {"section_key": "mission", "mode": "replace"},
    )

    section = application.sections.get(section_key="mission")
    assert section.approved_response == "Human approved text."
    assert section.draft_response == ""


def test_library_suggestions_are_offered_for_a_matching_section(application):
    GrantAnswerLibraryItem.objects.create(
        organization=application.project.organization,
        category=GrantAnswerLibraryItem.Category.ORGANIZATIONAL_CAPACITY,
        title="Capacity answer", answer="We have the staff and systems.",
    )
    section = application.sections.get(section_key="organizational_capacity")

    suggestions = answer_library.suggestions_for_section(section, spec_for("organizational_capacity"))

    assert [item.title for item in suggestions] == ["Capacity answer"]


# ── Limits, completion, status ───────────────────────────────────────────────

def test_word_and_character_limits_are_tracked(client, application):
    client.force_login(application.created_by)

    client.post(
        reverse("project-grant-section-save", kwargs={
            "pk": application.project_id, "application_id": application.pk,
            "section_key": "statement_of_need",
        }),
        {"intent": "save", "response": "one two three four five", "character_limit": "10"},
    )

    section = application.sections.get(section_key="statement_of_need")
    assert section.character_limit == 10
    assert section.character_count == 23
    assert section.over_character_limit is True
    assert section.limit_label == "23 / 10 characters"


def test_completion_is_derived_from_real_section_status(application):
    sections = list(application.sections.all())
    assert application.completion_percent(sections) == 0

    for section in sections:
        section.approved_response = "Approved."
        section.status = GrantApplicationSection.Status.APPROVED
        section.save()

    assert application.completion_percent(list(application.sections.all())) == 100


def test_a_draft_counts_less_than_an_approved_answer(application):
    sections = list(application.sections.all())
    for section in sections:
        section.draft_response = "Drafted."
        section.status = GrantApplicationSection.Status.DRAFTED
        section.save()

    assert application.completion_percent(list(application.sections.all())) == 50


def test_status_can_be_moved_through_the_grant_workflow(client, application):
    client.force_login(application.created_by)

    client.post(
        reverse("project-grant-status", kwargs={
            "pk": application.project_id, "application_id": application.pk,
        }),
        {"status": GrantApplication.Status.SUBMITTED},
    )

    application.refresh_from_db()
    assert application.status == GrantApplication.Status.SUBMITTED
    assert application.is_closed is True


def test_grant_details_are_parsed_into_typed_columns(client, application):
    client.force_login(application.created_by)

    client.post(
        reverse("project-grant-details", kwargs={
            "pk": application.project_id, "application_id": application.pk,
        }),
        {"funder_name": "Example Foundation", "deadline": "2026-10-15",
         "requested_amount": "$75,000"},
    )

    application.refresh_from_db()
    assert application.funder_name == "Example Foundation"
    assert application.deadline.isoformat() == "2026-10-15"
    assert application.requested_amount == Decimal("75000")
    assert application.requested_amount_display == "$75,000"


def test_an_unparseable_amount_does_not_break_the_workspace(client, application):
    client.force_login(application.created_by)

    response = client.post(
        reverse("project-grant-details", kwargs={
            "pk": application.project_id, "application_id": application.pk,
        }),
        {"funder_name": "Example Foundation", "requested_amount": "about fifty grand"},
        follow=True,
    )

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.funder_name == "Example Foundation"


def test_an_unknown_status_is_rejected(client, application):
    client.force_login(application.created_by)

    client.post(
        reverse("project-grant-status", kwargs={
            "pk": application.project_id, "application_id": application.pk,
        }),
        {"status": "totally_made_up"},
    )

    application.refresh_from_db()
    assert application.status == GrantApplication.Status.DRAFTING


# ── Review + export ──────────────────────────────────────────────────────────

def test_review_reports_real_issues_not_arbitrary_scores(application):
    section = application.sections.get(section_key="mission")
    section.approved_response = "We serve 8,412 youth."
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()
    context = build_grant_context(application)

    review = completeness.build_application_review(application, context)

    messages = " ".join(issue.message for issue in review.issues)
    assert "8412" in messages or "8,412" in messages
    # Metrics that cannot be honestly scored report a label, not a fake percentage.
    labelled = {metric.label: metric for metric in review.metrics}
    assert labelled["Funder Alignment"].score is None
    assert labelled["Application Completeness"].score == review.completion_percent


def test_review_flags_required_sections_that_are_drafted_but_unapproved(application):
    section = application.sections.get(section_key="mission")
    section.draft_response = "An AI draft nobody has approved."
    section.status = GrantApplicationSection.Status.DRAFTED
    section.save()
    context = build_grant_context(application)

    review = completeness.build_application_review(application, context)

    assert any("not yet approved" in issue.message for issue in review.issues)


def test_full_draft_view_renders_the_answers(client, application):
    client.force_login(application.created_by)
    section = application.sections.get(section_key="mission")
    section.approved_response = "Our approved mission statement."
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()

    response = client.get(reverse("project-grant-export", kwargs={
        "pk": application.project_id, "application_id": application.pk,
    }))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Our approved mission statement." in content
    assert "Copy Full Draft" in content


# ── Portal pages render ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "url_name", ["project-grant-overview", "project-grant-application",
                 "project-grant-missing", "project-grant-library", "project-grant-review"],
)
def test_every_workspace_page_renders(client, application, url_name):
    client.force_login(application.created_by)

    response = client.get(reverse(url_name, kwargs={
        "pk": application.project_id, "application_id": application.pk,
    }))

    assert response.status_code == 200
    assert "Atlas Grant Builder" in response.content.decode()


def test_section_workspace_shows_question_guidance_sources_and_missing(client, sparse_application):
    client.force_login(sparse_application.created_by)

    response = client.get(reverse("project-grant-section", kwargs={
        "pk": sparse_application.project_id, "application_id": sparse_application.pk,
        "section_key": "statement_of_need",
    }))

    content = response.content.decode()
    assert "Funder question" in content
    assert "Atlas guidance" in content
    assert "Sources used" in content
    assert "Information needed" in content


def test_grant_list_shows_the_empty_state_before_any_draft(client, grant_project):
    project, user, _opportunity = grant_project
    client.force_login(user)

    response = client.get(reverse("project-grants", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "No Grant Drafts" in content
    assert "Browse Opportunities" in content
