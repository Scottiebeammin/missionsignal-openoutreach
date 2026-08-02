"""Atlas Grant Builder V1.1 — real application import and question mapping.

The load-bearing tests here are about fidelity and trust: the funder's wording
must survive verbatim, a person must be able to correct the parser, and the
three buckets (known / missing / suggested) must never blur into each other.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import DocumentVaultItem, EvidenceLibraryItem, Opportunity
from openoutreach.grants.models import (
    GrantAnswerLibraryItem,
    GrantApplication,
    GrantApplicationImport,
    GrantApplicationSection,
    GrantAttachmentRequirement,
)
from openoutreach.grants.services import imports
from openoutreach.grants.services.application_parser import (
    detect_attachments,
    detect_character_limit,
    detect_page_limit,
    detect_required,
    detect_word_limit,
    parse_application,
)
from openoutreach.grants.services.applications import start_grant_application
from openoutreach.grants.services.context_builder import build_grant_context
from openoutreach.grants.services.draft_generator import SectionDraft
from openoutreach.grants.services.question_analysis import Suggestion, analyze_question
from openoutreach.grants.services import completeness, grant_coach

pytestmark = pytest.mark.django_db


SAMPLE_APPLICATION = """
GENERAL INSTRUCTIONS

All responses must use 12-point font.
The budget must equal the amount requested.
Organization must operate in Orange County.

SECTION 1: ORGANIZATION INFORMATION

1. Describe your organization's mission and history.
   Maximum 2,000 characters.

2. What is your organization's annual operating budget?

SECTION 2: PROGRAM DESCRIPTION

3. Describe the program for which funding is requested.
   Limit response to 500 words.

4. How many people will this program serve? (optional)

REQUIRED ATTACHMENTS

- IRS determination letter
- Board roster
- Project budget
- Most recent audited financial statements
"""


@pytest.fixture
def application(db):
    """A grant draft on a modestly-populated organization."""
    user = get_user_model().objects.create_user(username="import-ed", password="x")
    organization = Organization.objects.create(
        name="Empowered Futures",
        website="https://empoweredfutures.example.org",
        mission="Prepare Orange County teens for their first job.",
        organization_summary="Founded in 2015, Empowered Futures runs job-readiness programs.",
        city="Orlando", county="Orange", state="Florida",
        beneficiaries=["youth"], focus_areas=["workforce development"],
        existing_partnerships=["Orange County Public Schools"],
        budget_range="$250,000-$500,000",
    )
    organization.users.add(user)
    project = Project.objects.create(
        organization=organization, name="Workforce Initiative",
        programs="After-school job readiness workshops and paid internships.",
    )
    project.users.add(user)
    opportunity = Opportunity.objects.create(
        project=project, name="Community Impact Grant",
        source_name="Example Foundation",
        focus_areas=["workforce development"],
        geography=["Orange County"],
    )
    app, _ = start_grant_application(project, opportunity, user=user)
    return app


def _import(application, text=SAMPLE_APPLICATION):
    parsed = parse_application(text)
    batch = imports.create_import(application, text, parsed, user=application.created_by)
    rows = [
        {
            "text": q.text, "label": q.label, "section_group": q.section_group,
            "instructions": q.instructions, "question_type": q.question_type,
            "required": q.required, "word_limit": q.word_limit,
            "character_limit": q.character_limit, "page_limit_note": q.page_limit_note,
            "order": q.order,
        }
        for q in parsed.questions
    ]
    attachments = [{"title": a.title, "document_type": a.document_type} for a in parsed.attachments]
    return batch, imports.save_imported_questions(batch, rows, attachments), parsed


# ── Parsing ──────────────────────────────────────────────────────────────────

def test_parses_clean_numbered_questions():
    parsed = parse_application(SAMPLE_APPLICATION)

    texts = [q.text for q in parsed.questions]
    assert "Describe your organization's mission and history." in texts
    assert "Describe the program for which funding is requested." in texts
    assert parsed.question_count == 4


def test_preserves_section_headings():
    parsed = parse_application(SAMPLE_APPLICATION)

    groups = {q.text: q.section_group for q in parsed.questions}
    assert groups["Describe your organization's mission and history."] == "ORGANIZATION INFORMATION"
    assert groups["Describe the program for which funding is requested."] == "PROGRAM DESCRIPTION"


def test_question_wording_is_never_rewritten():
    parsed = parse_application("1. Describe, in your own words, why this matters.")

    assert parsed.questions[0].text == "Describe, in your own words, why this matters."


@pytest.mark.parametrize("text,expected", [
    ("Maximum 500 words", 500),
    ("500-word maximum", 500),
    ("Please limit to 1,200 words", 1200),
    ("(250 words)", 250),
    ("Word limit: 300", 300),
    ("no limit mentioned", None),
])
def test_word_limit_detection(text, expected):
    assert detect_word_limit(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("Limit response to 2,500 characters", 2500),
    ("Maximum 2000 characters", 2000),
    ("(1500 characters)", 1500),
    ("Character limit: 800", 800),
    ("nothing here", None),
])
def test_character_limit_detection(text, expected):
    assert detect_character_limit(text) == expected


def test_character_limit_is_not_read_as_a_word_limit():
    assert detect_word_limit("Maximum 2,500 characters") is None
    assert detect_character_limit("Maximum 2,500 characters") == 2500


@pytest.mark.parametrize("text,expected", [
    ("Not to exceed 1 page", "maximum 1 page"),
    ("Maximum 2 pages", "maximum 2 pages"),
    ("no page guidance", ""),
])
def test_page_limit_detection(text, expected):
    assert detect_page_limit(text) == expected


def test_required_and_optional_detection():
    assert detect_required("Describe your mission.") is True
    assert detect_required("Describe your mission. (optional)") is False
    assert detect_required("This attachment is required.") is True
    assert detect_required("Include a logic model if applicable") is False


def test_limits_land_on_the_parsed_questions():
    parsed = parse_application(SAMPLE_APPLICATION)
    by_text = {q.text: q for q in parsed.questions}

    assert by_text["Describe your organization's mission and history."].character_limit == 2000
    assert by_text["Describe the program for which funding is requested."].word_limit == 500


def test_attachment_detection():
    parsed = parse_application(SAMPLE_APPLICATION)

    titles = {a.title for a in parsed.attachments}
    assert "IRS determination letter" in titles
    assert "Board roster" in titles
    assert "Project budget" in titles
    assert "Audited financial statements" in titles


def test_attachment_detection_requires_asking_context():
    """A narrative that merely mentions a budget is not an attachment requirement."""
    assert detect_attachments("Our annual budget grew last year to a new high.") == []
    assert detect_attachments("Please attach your most recent annual budget.") != []


def test_question_type_classification():
    parsed = parse_application(SAMPLE_APPLICATION)
    by_text = {q.text: q.question_type for q in parsed.questions}

    assert by_text["Describe your organization's mission and history."] == "narrative"
    assert by_text["What is your organization's annual operating budget?"] == "currency"
    assert by_text["How many people will this program serve? (optional)"] == "numeric"


def test_application_level_instructions_are_kept_separate():
    parsed = parse_application(SAMPLE_APPLICATION)

    joined = " ".join(parsed.application_instructions)
    assert "12-point font" in joined
    assert "budget must equal" in joined
    # …and they did not become questions.
    assert not any("12-point font" in q.text for q in parsed.questions)


def test_empty_input_is_low_confidence_and_produces_nothing():
    parsed = parse_application("")

    assert parsed.question_count == 0
    assert parsed.confidence == "low"
    assert parsed.notes


def test_messy_text_is_flagged_rather_than_silently_split():
    messy = (
        "we want to know about your work and what you do with young people in the county "
        "and also anything else you think is relevant to our foundation's giving priorities"
    )
    parsed = parse_application(messy)

    assert parsed.confidence == "low"
    assert parsed.notes


def test_unnumbered_prompts_are_still_detected_but_noted():
    parsed = parse_application(
        "Describe your mission.\n\nExplain how you measure outcomes.\n\nList your key partners."
    )

    assert parsed.question_count == 3
    assert any("numbering" in note for note in parsed.notes)


# ── Saving the reviewed import ───────────────────────────────────────────────

def test_saving_creates_sections_with_the_exact_wording(application):
    _batch, created, _parsed = _import(application)

    assert len(created) == 4
    first = application.sections.get(section_key="q1")
    assert first.original_question == "Describe your organization's mission and history."
    assert first.funder_question == first.original_question
    assert first.source_type == GrantApplicationSection.SourceType.IMPORTED
    assert first.character_limit == 2000
    assert first.section_group == "ORGANIZATION INFORMATION"


def test_imported_keys_never_collide_with_template_keys(application):
    _batch, created, _parsed = _import(application)

    template_keys = {"organization_overview", "mission", "statement_of_need"}
    assert not template_keys & {section.section_key for section in created}


def test_attachments_become_a_checklist(application):
    _batch, _created, _parsed = _import(application)

    titles = set(
        GrantAttachmentRequirement.objects.filter(application=application)
        .values_list("title", flat=True)
    )
    assert "IRS determination letter" in titles
    assert all(
        not item.confirmed
        for item in GrantAttachmentRequirement.objects.filter(application=application)
    )


def test_attachment_links_to_an_existing_vault_document(application):
    DocumentVaultItem.objects.create(
        project=application.project, title="IRS letter 2015",
        document_type=DocumentVaultItem.DocumentType.IRS_DETERMINATION_LETTER,
        status=DocumentVaultItem.Status.AVAILABLE,
    )
    _import(application)

    requirement = GrantAttachmentRequirement.objects.get(
        application=application, document_type="irs_determination_letter",
    )
    assert requirement.linked_document is not None
    assert requirement.is_satisfied is True


def test_reimport_replaces_previous_questions_but_keeps_approved_ones(application):
    _batch, created, _parsed = _import(application)
    keeper = created[0]
    keeper.approved_response = "A human approved this."
    keeper.status = GrantApplicationSection.Status.APPROVED
    keeper.save()

    _import(application, "1. A completely different question?")

    assert GrantApplicationSection.objects.filter(pk=keeper.pk).exists()
    remaining = application.sections.filter(source_type="imported")
    assert "A completely different question?" in [s.original_question for s in remaining]


# ── Review-screen corrections ────────────────────────────────────────────────

def test_review_form_edits_delete_add_and_reorder(client, application):
    parsed = parse_application(SAMPLE_APPLICATION)
    batch = imports.create_import(application, SAMPLE_APPLICATION, parsed, user=application.created_by)
    client.force_login(application.created_by)

    post = {
        # Edited wording + corrected limit, moved to position 2.
        "q-0-text": "Describe your organization's mission and history in full.",
        "q-0-order": "2", "q-0-required": "1", "q-0-character_limit": "1500",
        "q-0-question_type": "narrative", "q-0-section_group": "Organization Information",
        # Deleted.
        "q-1-text": "What is your organization's annual operating budget?",
        "q-1-order": "3", "q-1-delete": "1",
        # Added by hand, first.
        "q-2-text": "A question the parser missed entirely?",
        "q-2-order": "1", "q-2-question_type": "narrative",
        "application_instructions": "All responses must use 12-point font.",
    }
    response = client.post(
        reverse("project-grant-import-review", kwargs={
            "pk": application.project_id, "application_id": application.pk, "batch_id": batch.pk,
        }),
        post, follow=True,
    )

    assert response.status_code == 200
    sections = list(application.sections.filter(source_type="imported").order_by("imported_order"))
    assert [s.original_question for s in sections] == [
        "A question the parser missed entirely?",
        "Describe your organization's mission and history in full.",
    ]
    assert sections[1].character_limit == 1500
    batch.refresh_from_db()
    assert batch.status == GrantApplicationImport.Status.SAVED
    assert "12-point font" in " ".join(batch.application_instructions)


def test_review_rejects_an_empty_question_set(client, application):
    parsed = parse_application(SAMPLE_APPLICATION)
    batch = imports.create_import(application, SAMPLE_APPLICATION, parsed, user=application.created_by)
    client.force_login(application.created_by)

    client.post(
        reverse("project-grant-import-review", kwargs={
            "pk": application.project_id, "application_id": application.pk, "batch_id": batch.pk,
        }),
        {"q-0-text": "", "q-0-order": "1"},
    )

    assert application.sections.filter(source_type="imported").count() == 0


# ── Knowledge mapping: the three buckets ─────────────────────────────────────

def test_known_facts_come_only_from_real_records(application):
    _batch, created, _parsed = _import(application)
    context = build_grant_context(application)

    analysis = analyze_question(created[0], context)

    labels = analysis.known_labels
    assert "Organization Mission" in labels
    # Everything in this bucket must be a Fact carrying a real stored value.
    for fact in analysis.known_facts:
        assert fact.value.strip()
        assert context.fact(fact.key) is not None


def test_missing_information_is_named_with_somewhere_to_fix_it(application):
    _batch, created, _parsed = _import(application)
    context = build_grant_context(application)
    program_question = application.sections.get(section_key="q4")

    analysis = analyze_question(program_question, context)

    assert analysis.missing_information
    item = analysis.missing_information[0]
    assert item.label and item.hint and item.add_url_name


def test_suggestions_are_a_separate_type_from_facts(application):
    _batch, created, _parsed = _import(application)
    context = build_grant_context(application)

    analysis = analyze_question(created[0], context)

    assert analysis.writing_suggestions
    assert all(isinstance(s, Suggestion) for s in analysis.writing_suggestions)
    # A suggestion can never be mistaken for a fact: different type, no value.
    assert not any(hasattr(s, "value") for s in analysis.writing_suggestions)
    fact_labels = set(analysis.known_labels)
    assert not fact_labels & {s.text for s in analysis.writing_suggestions}


def test_relevant_answer_library_item_is_surfaced(application):
    _batch, created, _parsed = _import(application)
    GrantAnswerLibraryItem.objects.create(
        organization=application.project.organization,
        category=GrantAnswerLibraryItem.Category.MISSION,
        title="Standard mission answer",
        answer="Empowered Futures prepares Orange County teens for their first job.",
    )
    context = build_grant_context(application)

    analysis = analyze_question(created[0], context)

    assert [m.item.title for m in analysis.relevant_answer_library_items] == ["Standard mission answer"]


def test_stale_numbers_in_a_saved_answer_are_flagged(application):
    _batch, created, _parsed = _import(application)
    GrantAnswerLibraryItem.objects.create(
        organization=application.project.organization,
        category=GrantAnswerLibraryItem.Category.MISSION,
        title="Older mission answer",
        answer="We serve 275 participants annually across Orange County.",
    )
    context = build_grant_context(application)

    analysis = analyze_question(created[0], context)

    match = analysis.relevant_answer_library_items[0]
    assert "275" in match.stale_numbers
    assert match.has_warning is True


def test_a_supported_number_is_not_flagged_as_stale(application):
    EvidenceLibraryItem.objects.create(
        project=application.project, title="Youth served annually",
        evidence_type=EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC,
        metric_name="Youth served annually", metric_value="425",
        status=EvidenceLibraryItem.Status.AVAILABLE,
    )
    _batch, created, _parsed = _import(application)
    GrantAnswerLibraryItem.objects.create(
        organization=application.project.organization,
        category=GrantAnswerLibraryItem.Category.MISSION,
        title="Current mission answer",
        answer="We serve 425 participants annually.",
    )
    context = build_grant_context(application)

    analysis = analyze_question(created[0], context)

    assert analysis.relevant_answer_library_items[0].stale_numbers == []


# ── Generation gate ──────────────────────────────────────────────────────────

def test_gate_opens_when_atlas_has_enough(application):
    _batch, created, _parsed = _import(application)
    context = build_grant_context(application)

    analysis = analyze_question(created[0], context)

    assert analysis.can_generate_draft is True
    assert analysis.gate_reason


def test_gate_closes_for_a_non_narrative_field(application):
    _batch, _created, _parsed = _import(application)
    context = build_grant_context(application)
    budget_question = application.sections.get(section_key="q2")

    analysis = analyze_question(budget_question, context)

    assert budget_question.question_type == GrantApplicationSection.QuestionType.CURRENCY
    assert analysis.can_generate_draft is False
    assert "fill it in directly" in analysis.gate_reason


def test_generate_is_refused_when_the_gate_is_closed(client, application):
    _batch, _created, _parsed = _import(application)
    client.force_login(application.created_by)

    with patch("openoutreach.grants.services.draft_generator._agent") as agent:
        client.post(reverse("project-grant-section-generate", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "q2",
        }))

    agent.assert_not_called()
    assert application.sections.get(section_key="q2").draft_response == ""


def test_draft_for_an_imported_question_records_sources(client, application):
    _batch, _created, _parsed = _import(application)
    client.force_login(application.created_by)
    draft = SectionDraft(
        response="Empowered Futures prepares Orange County teens for their first job.",
        sources_used=["Organization Mission"], missing_information=[],
    )

    with patch("openoutreach.grants.services.draft_generator._agent"), \
         patch("openoutreach.grants.services.draft_generator._run", return_value=draft):
        client.post(reverse("project-grant-section-generate", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "q1",
        }))

    section = application.sections.get(section_key="q1")
    assert section.draft_response.startswith("Empowered Futures")
    assert section.approved_response == ""
    assert any(entry["label"] == "Organization Mission" for entry in section.source_fields)


def test_placeholder_is_preserved_and_flags_the_section(client, application):
    _batch, _created, _parsed = _import(application)
    client.force_login(application.created_by)
    draft = SectionDraft(
        response="We served [Information needed: 2025 participant count] young people.",
        sources_used=[], missing_information=[],
    )

    with patch("openoutreach.grants.services.draft_generator._agent"), \
         patch("openoutreach.grants.services.draft_generator._run", return_value=draft):
        client.post(reverse("project-grant-section-generate", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "q3",
        }))

    section = application.sections.get(section_key="q3")
    assert "[Information needed:" in section.draft_response


def test_ai_still_cannot_overwrite_an_approved_imported_answer(client, application):
    _batch, _created, _parsed = _import(application)
    client.force_login(application.created_by)
    save_url = reverse("project-grant-section-save", kwargs={
        "pk": application.project_id, "application_id": application.pk, "section_key": "q1",
    })
    client.post(save_url, {"intent": "approve", "response": "The approved wording."})

    with patch("openoutreach.grants.services.draft_generator._agent"), \
         patch("openoutreach.grants.services.draft_generator._run",
               return_value=SectionDraft(response="A new AI draft.", sources_used=[], missing_information=[])):
        client.post(reverse("project-grant-section-generate", kwargs={
            "pk": application.project_id, "application_id": application.pk, "section_key": "q1",
        }))

    section = application.sections.get(section_key="q1")
    assert section.approved_response == "The approved wording."
    assert section.status == GrantApplicationSection.Status.APPROVED
    assert section.draft_response == "A new AI draft."


def test_unsupported_number_warning_still_fires_on_imported_questions(application):
    _batch, created, _parsed = _import(application)
    section = created[0]
    section.approved_response = "We served 9,412 youth last year."
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()
    context = build_grant_context(application)

    review = grant_coach.review_imported_question(section, context)

    assert "9412" in review.unsupported_numbers
    evidence = next(d for d in review.dimensions if d.name == "Evidence")
    assert evidence.label == grant_coach.NEEDS_ATTENTION_LABEL


# ── Grant Coach dimensions ───────────────────────────────────────────────────

def test_coach_reports_five_labelled_dimensions(application):
    _batch, created, _parsed = _import(application)
    section = created[0]
    section.approved_response = (
        "Empowered Futures prepares Orange County teens for their first job through "
        "after-school workforce development workshops and paid internships."
    )
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()
    context = build_grant_context(application)

    review = grant_coach.review_imported_question(section, context)

    names = [d.name for d in review.dimensions]
    assert names == ["Answered the Question", "Evidence", "Specificity", "Funder Alignment", "Readability"]
    assert all(d.label in {"Strong", "Moderate", "Needs Attention", "Incomplete"} for d in review.dimensions)


def test_coach_flags_an_answer_that_dodges_the_question(application):
    _batch, created, _parsed = _import(application)
    section = created[0]
    section.approved_response = "We are passionate about various innovative community initiatives."
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()
    context = build_grant_context(application)

    review = grant_coach.review_imported_question(section, context)

    answered = next(d for d in review.dimensions if d.name == "Answered the Question")
    assert answered.label in {"Needs Attention", "Moderate"}
    specificity = next(d for d in review.dimensions if d.name == "Specificity")
    assert specificity.label == "Needs Attention"


# ── Completeness ─────────────────────────────────────────────────────────────

def test_completion_is_measured_against_imported_questions(application):
    _batch, created, _parsed = _import(application)

    # Four imported questions replace the 14-section template as the yardstick.
    answerable = application.answerable_sections()
    assert len(answerable) == 4
    assert application.completion_percent() == 0

    for section in created:
        section.approved_response = "Answered."
        section.status = GrantApplicationSection.Status.APPROVED
        section.save()
    assert application.completion_percent() == 100


def test_optional_imported_question_does_not_penalise_completion(application):
    _batch, created, _parsed = _import(application)
    required = [s for s in created if s.required]
    for section in required:
        section.approved_response = "Answered."
        section.status = GrantApplicationSection.Status.APPROVED
        section.save()

    assert any(not s.required for s in created)
    assert application.completion_percent() == 100


def test_review_counts_required_questions_and_attachments(application):
    _batch, created, _parsed = _import(application)
    context = build_grant_context(application)

    review = completeness.build_application_review(application, context)

    labels = {metric.label: metric for metric in review.metrics}
    assert "Required Questions Complete" in labels
    assert labels["Required Questions Complete"].value.endswith("/ 3")
    assert any("not confirmed yet" in issue.message for issue in review.issues)


def test_limit_violation_is_reported_as_an_issue(application):
    _batch, created, _parsed = _import(application)
    section = application.sections.get(section_key="q1")   # 2,000-character limit
    section.approved_response = "x" * 2100
    section.status = GrantApplicationSection.Status.APPROVED
    section.save()
    context = build_grant_context(application)

    review = completeness.build_application_review(application, context)

    assert any("character limit" in issue.message for issue in review.issues)


# ── Permissions ──────────────────────────────────────────────────────────────

def _rival():
    user = get_user_model().objects.create_user(username="rival-import", password="x")
    organization = Organization.objects.create(
        name="Rival Org", website="https://rival.example.org", mission="Something else",
    )
    organization.users.add(user)
    project = Project.objects.create(
        organization=organization, name="Rival Project", programs="Other programs",
    )
    project.users.add(user)
    return project, user


def test_another_organization_cannot_open_the_import_screen(client, application):
    _project, rival = _rival()
    client.force_login(rival)

    response = client.get(reverse("project-grant-import", kwargs={
        "pk": application.project_id, "application_id": application.pk,
    }))

    assert response.status_code == 404


def test_another_organization_cannot_open_an_import_review(client, application):
    parsed = parse_application(SAMPLE_APPLICATION)
    batch = imports.create_import(application, SAMPLE_APPLICATION, parsed)
    rival_project, rival = _rival()
    client.force_login(rival)

    for pk in (application.project_id, rival_project.pk):
        response = client.get(reverse("project-grant-import-review", kwargs={
            "pk": pk, "application_id": application.pk, "batch_id": batch.pk,
        }))
        assert response.status_code == 404


def test_another_organization_cannot_toggle_an_attachment(client, application):
    _import(application)
    requirement = GrantAttachmentRequirement.objects.filter(application=application).first()
    _project, rival = _rival()
    client.force_login(rival)

    response = client.post(reverse("project-grant-attachment-toggle", kwargs={
        "pk": application.project_id, "application_id": application.pk,
        "requirement_id": requirement.pk,
    }))

    assert response.status_code == 404
    requirement.refresh_from_db()
    assert requirement.confirmed is False


# ── Pages render ─────────────────────────────────────────────────────────────

def test_import_screen_renders(client, application):
    client.force_login(application.created_by)

    response = client.get(reverse("project-grant-import", kwargs={
        "pk": application.project_id, "application_id": application.pk,
    }))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Import Application Questions" in content
    assert "Analyze Application" in content


def test_import_review_screen_renders_with_editable_questions(client, application):
    client.force_login(application.created_by)
    client.post(
        reverse("project-grant-import", kwargs={
            "pk": application.project_id, "application_id": application.pk,
        }),
        {"raw_text": SAMPLE_APPLICATION}, follow=True,
    )
    batch = GrantApplicationImport.objects.filter(application=application).first()

    response = client.get(reverse("project-grant-import-review", kwargs={
        "pk": application.project_id, "application_id": application.pk, "batch_id": batch.pk,
    }))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Application Review" in content
    assert "Describe your organization&#x27;s mission and history." in content
    assert "Save Application Questions" in content


def test_question_workspace_shows_the_three_buckets(client, application):
    _import(application)
    client.force_login(application.created_by)

    response = client.get(reverse("project-grant-section", kwargs={
        "pk": application.project_id, "application_id": application.pk, "section_key": "q1",
    }))

    content = response.content.decode()
    assert "Original funder question" in content
    assert "Known by Atlas" in content
    assert "Needs your input" in content
    assert "Suggested by Atlas" in content
    assert "Requirements" in content


def test_overview_shows_instructions_and_attachment_checklist(client, application):
    _import(application)
    client.force_login(application.created_by)

    response = client.get(reverse("project-grant-overview", kwargs={
        "pk": application.project_id, "application_id": application.pk,
    }))

    content = response.content.decode()
    assert "Application instructions" in content
    assert "12-point font" in content
    assert "Required attachments" in content
    assert "IRS determination letter" in content


# ── Regressions found by smoke-testing a realistic application ───────────────

def test_wrapped_continuation_line_is_not_split_into_a_new_question():
    """'…include local data / where available.' is one question, not two.

    Regression: 'where' matched the narrative-verb list, so a wrapped line was
    promoted to its own question.
    """
    parsed = parse_application(
        "4) Describe the problem this project addresses. Include local data\n"
        "   where available. Not to exceed 2 pages."
    )

    assert parsed.question_count == 1
    question = parsed.questions[0]
    assert "where available" in question.text
    assert question.page_limit_note == "maximum 2 pages"


def test_obligations_outside_an_instructions_heading_are_kept():
    """Regression: 'Before you begin: …' and 'All narrative responses must…'
    were dropped into unparsed instead of kept as application instructions."""
    parsed = parse_application(
        "Before you begin: applications must be submitted through the portal by October 15.\n"
        "All narrative responses must be single-spaced.\n\n"
        "1. Describe your mission."
    )

    joined = " ".join(parsed.application_instructions)
    assert "submitted through the portal" in joined
    assert "single-spaced" in joined
    assert parsed.question_count == 1


def test_contact_information_fields_are_classified_informational():
    """Regression: 'Legal name of organization:' fell through to 'unknown'."""
    parsed = parse_application(
        "1) Legal name of organization:\n\n2) Executive Director email:"
    )

    assert [q.question_type for q in parsed.questions] == ["informational", "informational"]


def test_informational_fields_are_excluded_from_completion(application):
    """A contact field is not an answer someone writes — it must not dilute completion."""
    text = "1) Legal name of organization:\n\n2) Describe your mission and history."
    _batch, created, _parsed = _import(application, text)

    answerable = application.answerable_sections()
    assert [s.question_type for s in created] == ["informational", "narrative"]
    assert len(answerable) == 1
    assert answerable[0].question_type == "narrative"
