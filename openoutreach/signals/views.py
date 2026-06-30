import os
import time

import stripe
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from openoutreach.core.models import Project
from openoutreach.funding.models import Opportunity, OpportunityTask
from openoutreach.funding.readiness import build_funding_readiness
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.signals.celebrations import build_celebration_overview
from openoutreach.signals.dashboard import build_executive_dashboard
from openoutreach.signals.discovery import build_discovery_overview
from openoutreach.signals.documents import (
    build_document_evidence_health,
    build_document_vault_summary,
    build_evidence_library_summary,
    build_opportunity_document_summary,
)
from openoutreach.signals.ecosystem import build_ecosystem_overview
from openoutreach.signals.forms import (
    InterestSignupForm,
    OrganizationIntakeForm,
    PilotDiscoveryQuestionnaireForm,
    PilotFeedbackForm,
    QuestionForm,
)
from openoutreach.signals.notifications import (
    notify_interest_signup,
    send_interest_signup_confirmation,
    send_question_received_confirmation,
)
from openoutreach.signals.forecasting import build_pipeline_forecast
from openoutreach.signals.government import build_government_readiness
from openoutreach.signals.lifecycle import assign_opportunity_owner, transition_opportunity_lifecycle
from openoutreach.signals.matching import build_opportunity_matches
from openoutreach.signals.mission_brief import recommended_next_steps
from openoutreach.signals.models import InterestSignup, PilotProfile
from openoutreach.signals.opportunity_work import build_opportunity_workspace, ensure_default_tasks
from openoutreach.signals.opportunity_web import build_opportunity_web
from openoutreach.signals.partnerships import build_partnership_readiness
from openoutreach.signals.pilot import (
    build_pilot_context,
    create_pilot_profile_from_signup,
    get_or_create_project_pilot_profile,
)
from openoutreach.signals.readiness import (
    build_opportunity_pursuit_readiness,
    build_opportunity_pursuit_summary,
    build_readiness_overview,
)
from openoutreach.signals.relationships import (
    build_opportunity_relationship_context,
    build_relationship_overview,
)
from openoutreach.signals.resources import build_resource_readiness
from openoutreach.signals.score_transparency import (
    explain_forecast,
    explain_match_overview,
    explain_organization_completeness,
    explain_pursuit_readiness,
    explain_readiness,
    explain_relationship_health,
)
from openoutreach.signals.services import create_organization_intake
from openoutreach.signals.snapshot import build_opportunity_web_snapshot
from openoutreach.signals.workflow import build_workflow_guidance


MODULE_PLACEHOLDERS = {
    "programs": {
        "title": "Programs",
        "heading": "Program Portfolio",
        "summary": (
            "Programs will organize the organization's initiatives into a concise "
            "portfolio for funder alignment, outcomes review, and opportunity scoping."
        ),
    },
}


def _workflow_context(project, stage, primary_actions=()):
    return {"workflow": build_workflow_guidance(project, stage, primary_actions)}


WAITLIST_ROLES = (
    "Executive Director",
    "Development Director",
    "Program Director",
    "Founder",
    "Board Member",
    "Other",
)


def public_landing_page(request):
    signup_failed = False
    if request.method == "POST":
        form = InterestSignupForm(request.POST)
        if form.is_valid():
            signup = form.save()
            create_pilot_profile_from_signup(signup)
            notify_interest_signup(signup)
            send_interest_signup_confirmation(signup)
            return redirect("anansi-atlas-thanks")
        signup_failed = True
    else:
        form = InterestSignupForm()
    return render(
        request,
        "signals/public_landing.html",
        {
            "form": form,
            "signup_failed": signup_failed,
            "waitlist_roles": WAITLIST_ROLES,
        },
    )


def public_landing_thanks(request):
    return render(request, "signals/public_landing_thanks.html")


def ask_question(request):
    """Handle the public 'Ask a Question / Request Info' form.

    Saves an InterestSignup tagged as a QUESTION, alerts info@anansiatlas.com,
    and sends the asker a short confirmation. GET just bounces to the form anchor.
    """
    if request.method != "POST":
        return redirect("/#ask")
    form = QuestionForm(request.POST)
    if form.is_valid():
        signup = form.save(commit=False)
        signup.interest_type = InterestSignup.InterestType.QUESTION
        signup.save()
        notify_interest_signup(signup)
        send_question_received_confirmation(signup)
        return redirect("anansi-atlas-question-thanks")
    # Re-render the landing page with the question form errors surfaced.
    return render(
        request,
        "signals/public_landing.html",
        {
            "form": InterestSignupForm(),
            "question_form": form,
            "question_failed": True,
            "waitlist_roles": WAITLIST_ROLES,
        },
    )


def question_thanks(request):
    return render(request, "signals/question_thanks.html")


# Simple in-process cache: (count, timestamp)
_seat_cache = None  # (claimed_count, timestamp) or None
_SEAT_CACHE_TTL = 300  # 5 minutes
_FOUNDING_SEAT_TOTAL = 20


def founding_seat_count(request):
    """Return live claimed/remaining seat count from Stripe, cached 5 min."""
    global _seat_cache
    now = time.monotonic()
    if _seat_cache and (now - _seat_cache[1]) < _SEAT_CACHE_TTL:
        claimed = _seat_cache[0]
    else:
        secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        price_id = os.getenv("STRIPE_FOUNDING_PRICE_ID", "")
        if not secret_key or not price_id:
            return JsonResponse({"claimed": 1, "remaining": 19, "total": _FOUNDING_SEAT_TOTAL, "live": False})
        try:
            stripe.api_key = secret_key
            subs = stripe.Subscription.list(price=price_id, status="active", limit=100)
            claimed = len(subs.data) + 1  # founder seat offset
        except Exception:
            claimed = _seat_cache[0] if _seat_cache else 4
        _seat_cache = (claimed, now)
    remaining = max(0, _FOUNDING_SEAT_TOTAL - claimed)
    return JsonResponse({"claimed": claimed, "remaining": remaining, "total": _FOUNDING_SEAT_TOTAL, "live": True})


def pilot_onboarding(request):
    form = InterestSignupForm(initial={"interest_type": "founding_atlas_partners"})
    return render(request, "signals/pilot_onboarding.html", {"form": form})


@login_required
def project_intake(request):
    # Admins don't need to fill out intake
    if request.user.is_staff:
        return redirect("/admin/")
    # Already has a project — go to portal
    if Project.objects.filter(users=request.user).exists():
        return redirect("portal")
    if request.method == "POST":
        form = OrganizationIntakeForm(request.POST)
        if form.is_valid():
            project = create_organization_intake(user=request.user, **form.cleaned_data)
            # Run analysis immediately so focus_areas/beneficiaries/FundingCriteria
            # are populated before the user ever reaches the Snapshot page.
            try:
                analyze_project(project, mode="deterministic")
            except Exception:
                pass  # analysis failure must never block onboarding
            # Fire AI research in the background — LLM call can take 30-120s,
            # so we don't make the user wait.
            import threading
            from openoutreach.signals.research import research_project as _research
            threading.Thread(target=_research, args=(project,), daemon=True).start()
            # Send welcome email to the user and an operator alert, both non-fatal.
            from openoutreach.signals.notifications import notify_new_intake, send_intake_welcome
            try:
                send_intake_welcome(request.user, project)
                notify_new_intake(request.user, project)
            except Exception:
                pass
            return redirect("project-intake-success", pk=project.pk)
    else:
        form = OrganizationIntakeForm()
    return render(request, "signals/project_intake.html", {"form": form})


@login_required
def project_intake_success(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    return render(request, "signals/project_intake_success.html", {"project": project})


@login_required
def project_analysis_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    return render(
        request,
        "signals/project_analysis_detail.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": getattr(project, "funding_criteria", None),
        },
    )


@login_required
@require_POST
def run_project_analysis(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    analyze_project(project, mode="deterministic")
    return redirect("project-analysis-detail", pk=project.pk)


@login_required
def project_mission_brief(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    return render(
        request,
        "signals/project_mission_brief.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "recommended_next_steps": recommended_next_steps(
                project.organization, funding_criteria,
            ),
        },
    )


@login_required
def project_organization_workspace(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    next_steps = recommended_next_steps(project.organization, funding_criteria)
    return render(
        request,
        "signals/project_organization_workspace.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "recommended_next_steps": next_steps[:5],
        },
    )


@login_required
def project_pilot_workspace(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    profile = get_or_create_project_pilot_profile(project)
    return render(
        request,
        "signals/project_pilot_workspace.html",
        {
            "project": project,
            "organization": project.organization,
            "pilot": build_pilot_context(profile),
        },
    )


@login_required
def project_pilot_questionnaire(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    profile = get_or_create_project_pilot_profile(project)
    if request.method == "POST":
        form = PilotDiscoveryQuestionnaireForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.lifecycle_status = PilotProfile.LifecycleStatus.QUESTIONNAIRE_COMPLETED
            profile.snapshot_status = PilotProfile.SnapshotStatus.REVIEWING_ORGANIZATION
            profile.save()
            return redirect("project-pilot-workspace", pk=project.pk)
    else:
        form = PilotDiscoveryQuestionnaireForm(instance=profile)
    return render(
        request,
        "signals/project_pilot_questionnaire.html",
        {
            "project": project,
            "organization": project.organization,
            "pilot": build_pilot_context(profile),
            "form": form,
        },
    )


@login_required
def project_pilot_feedback(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    profile = get_or_create_project_pilot_profile(project)
    feedback = getattr(profile, "feedback", None)
    if request.method == "POST":
        form = PilotFeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.pilot = profile
            feedback.save()
            profile.lifecycle_status = PilotProfile.LifecycleStatus.PILOT_COMPLETE
            profile.save(update_fields=["lifecycle_status", "updated_at"])
            return redirect("project-pilot-workspace", pk=project.pk)
    else:
        form = PilotFeedbackForm(instance=feedback)
    return render(
        request,
        "signals/project_pilot_feedback.html",
        {
            "project": project,
            "organization": project.organization,
            "pilot": build_pilot_context(profile),
            "form": form,
        },
    )


@login_required
def project_funding_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    readiness = build_funding_readiness(project, funding_criteria)
    return render(
        request,
        "signals/project_funding_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "readiness": readiness,
        },
    )


@login_required
def project_government_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    readiness = build_government_readiness(project, funding_criteria)
    return render(
        request,
        "signals/project_government_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "readiness": readiness,
        },
    )


@login_required
def project_executive_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    funding_readiness = build_funding_readiness(project, funding_criteria)
    government_readiness = build_government_readiness(project, funding_criteria)
    resource_readiness = build_resource_readiness(project, funding_criteria)
    partnership_readiness = build_partnership_readiness(project, funding_criteria)
    match_overview = build_opportunity_matches(project, funding_criteria)
    discovery_overview = build_discovery_overview(project, funding_criteria)
    ecosystem = build_ecosystem_overview(
        project, funding_readiness, government_readiness, resource_readiness,
        partnership_readiness, match_overview, discovery_overview,
    )
    dashboard = build_executive_dashboard(
        project, ecosystem, funding_readiness, government_readiness, resource_readiness,
        partnership_readiness, match_overview, discovery_overview,
    )
    forecast = dashboard.forecast
    relationships = dashboard.relationships
    opportunity_web = build_opportunity_web(project, discovery_overview)
    try:
        pilot = build_pilot_context(project.pilot_profile)
    except PilotProfile.DoesNotExist:
        pilot = None
    return render(
        request,
        "signals/project_executive_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "dashboard": dashboard,
            "opportunity_web": opportunity_web,
            "pilot": pilot,
            "score_transparency": {
                "readiness": explain_readiness(dashboard.readiness),
                "completeness": explain_organization_completeness(dashboard.readiness.organization_completeness),
                "match": explain_match_overview(match_overview),
                "forecast": explain_forecast(forecast),
                "relationship": explain_relationship_health(relationships),
            },
            **_workflow_context(project, "understand", dashboard.executive_actions[:2]),
        },
    )


@login_required
def project_readiness_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    funding_readiness = build_funding_readiness(project, funding_criteria)
    government_readiness = build_government_readiness(project, funding_criteria)
    resource_readiness = build_resource_readiness(project, funding_criteria)
    partnership_readiness = build_partnership_readiness(project, funding_criteria)
    readiness = build_readiness_overview(
        project, funding_readiness, government_readiness, resource_readiness, partnership_readiness,
    )
    pursuit_summary = build_opportunity_pursuit_summary(project)
    return render(
        request,
        "signals/project_readiness_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "readiness": readiness,
            "pursuit_summary": pursuit_summary,
            "score_transparency": {
                "readiness": explain_readiness(readiness),
                "completeness": explain_organization_completeness(readiness.organization_completeness),
            },
            **_workflow_context(project, "prepare", readiness.recommended_actions[:2]),
        },
    )


@login_required
def project_relationships_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    relationships = build_relationship_overview(project)
    return render(
        request,
        "signals/project_relationships_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "relationships": relationships,
            "score_transparency": {
                "relationship": explain_relationship_health(relationships),
            },
            **_workflow_context(project, "connect", (relationships.health.highest_leverage_action,)),
        },
    )


@login_required
def project_opportunity_web(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    discovery = build_discovery_overview(project, funding_criteria)
    return render(
        request,
        "signals/project_opportunity_web.html",
        {
            "project": project,
            "organization": project.organization,
            "web": build_opportunity_web(project, discovery),
            **_workflow_context(project, "understand"),
        },
    )


def _build_snapshot_ctx(project):
    """Shared snapshot data builder used by both authenticated and public views."""
    funding_criteria = getattr(project, "funding_criteria", None)
    funding_readiness = build_funding_readiness(project, funding_criteria)
    government_readiness = build_government_readiness(project, funding_criteria)
    resource_readiness = build_resource_readiness(project, funding_criteria)
    partnership_readiness = build_partnership_readiness(project, funding_criteria)
    discovery = build_discovery_overview(project, funding_criteria)
    match_overview = build_opportunity_matches(project, funding_criteria)
    readiness = build_readiness_overview(
        project, funding_readiness, government_readiness, resource_readiness, partnership_readiness,
    )
    web = build_opportunity_web(project, discovery)
    snapshot = build_opportunity_web_snapshot(
        project, web, readiness, funding_readiness, partnership_readiness,
        discovery, build_document_evidence_health(project), match_overview,
    )
    try:
        from openoutreach.signals.narratives import enhance_snapshot
        enhance_snapshot(project, snapshot)
    except Exception:
        pass
    return snapshot, web


@login_required
def project_snapshot(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    snapshot, web = _build_snapshot_ctx(project)

    from openoutreach.core.models import OrganizationMember
    member = OrganizationMember.objects.filter(user=request.user, project=project).first()
    first_visit = member and not member.has_toured

    return render(
        request,
        "signals/project_snapshot.html",
        {
            "project": project,
            "organization": project.organization,
            "snapshot": snapshot,
            "web": web,
            "first_visit": first_visit,
            **_workflow_context(project, "understand", snapshot.recommended_next_actions[:2]),
        },
    )


@login_required
def project_documents_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    return render(
        request,
        "signals/project_documents_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "document_summary": build_document_vault_summary(project),
            **_workflow_context(project, "prepare"),
        },
    )


@login_required
def project_evidence_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    return render(
        request,
        "signals/project_evidence_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "evidence_summary": build_evidence_library_summary(project),
            **_workflow_context(project, "prepare"),
        },
    )


@login_required
def project_celebrations_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    return render(
        request,
        "signals/project_celebrations_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "celebrations": build_celebration_overview(project),
        },
    )


@login_required
def project_ecosystem_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    funding_readiness = build_funding_readiness(project, funding_criteria)
    government_readiness = build_government_readiness(project, funding_criteria)
    resource_readiness = build_resource_readiness(project, funding_criteria)
    partnership_readiness = build_partnership_readiness(project, funding_criteria)
    match_overview = build_opportunity_matches(project, funding_criteria)
    discovery_overview = build_discovery_overview(project, funding_criteria)
    ecosystem = build_ecosystem_overview(
        project, funding_readiness, government_readiness, resource_readiness,
        partnership_readiness, match_overview, discovery_overview,
    )
    readiness = build_readiness_overview(
        project, funding_readiness, government_readiness, resource_readiness, partnership_readiness,
    )
    pursuit_summary = build_opportunity_pursuit_summary(project)
    forecast = build_pipeline_forecast(project)
    relationships = build_relationship_overview(project)
    return render(
        request,
        "signals/project_ecosystem_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "ecosystem": ecosystem,
            "funding_readiness": funding_readiness,
            "government_readiness": government_readiness,
            "resource_readiness": resource_readiness,
            "partnership_readiness": partnership_readiness,
            "readiness": readiness,
            "pursuit_summary": pursuit_summary,
            "forecast": forecast,
            "relationships": relationships,
            "score_transparency": {
                "readiness": explain_readiness(readiness),
                "completeness": explain_organization_completeness(readiness.organization_completeness),
                "match": explain_match_overview(match_overview),
                "forecast": explain_forecast(forecast),
                "relationship": explain_relationship_health(relationships),
            },
        },
    )


@login_required
def project_match_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    match_overview = build_opportunity_matches(project, funding_criteria)
    discovery = build_discovery_overview(project, funding_criteria)
    funding_readiness = build_funding_readiness(project, funding_criteria)
    government_readiness = build_government_readiness(project, funding_criteria)
    resource_readiness = build_resource_readiness(project, funding_criteria)
    partnership_readiness = build_partnership_readiness(project, funding_criteria)
    readiness = build_readiness_overview(
        project, funding_readiness, government_readiness, resource_readiness, partnership_readiness,
    )
    return render(
        request,
        "signals/project_match_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "match_overview": match_overview,
            "discovery": discovery,
            "readiness": readiness,
            "score_transparency": {
                "match": explain_match_overview(match_overview),
                "readiness": explain_readiness(readiness),
            },
            **_workflow_context(project, "prioritize", match_overview.highest_leverage_actions[:2]),
        },
    )


@login_required
def project_discovery_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    discovery = build_discovery_overview(project, funding_criteria)
    return render(
        request,
        "signals/project_discovery_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "discovery": discovery,
            **_workflow_context(project, "prioritize"),
        },
    )


@login_required
def project_opportunities_workspace(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    discovery = build_discovery_overview(project, funding_criteria)
    match_overview = build_opportunity_matches(project, funding_criteria)
    actions = list(match_overview.highest_leverage_actions)
    return render(
        request,
        "signals/project_opportunities_workspace.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "discovery": discovery,
            "match_overview": match_overview,
            "recommended_actions": actions[:5],
            "lifecycle": discovery.lifecycle_summary,
            **_workflow_context(project, "prioritize", actions[:2]),
        },
    )


@login_required
def project_pipeline_workspace(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    discovery = build_discovery_overview(project, funding_criteria)
    forecast = build_pipeline_forecast(project)
    return render(
        request,
        "signals/project_pipeline_workspace.html",
        {
            "project": project,
            "organization": project.organization,
            "discovery": discovery,
            "lifecycle": discovery.lifecycle_summary,
            "forecast": forecast,
            "score_transparency": {
                "forecast": explain_forecast(forecast),
            },
            **_workflow_context(
                project,
                "execute",
                (
                    discovery.lifecycle_summary.highest_priority_active_opportunity.name
                    if discovery.lifecycle_summary.highest_priority_active_opportunity else ""
                ),
            ),
        },
    )


@login_required
def project_opportunity_workspace(request, pk, opportunity_id):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    opportunity = get_object_or_404(
        Opportunity.objects.select_related("source_organization", "assigned_owner"),
        pk=opportunity_id,
        project=project,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    workspace = build_opportunity_workspace(project, opportunity, funding_criteria)
    pursuit_readiness = build_opportunity_pursuit_readiness(project, opportunity)
    document_summary = build_opportunity_document_summary(project, opportunity)
    relationship_context = build_opportunity_relationship_context(project, opportunity)
    return render(
        request,
        "signals/project_opportunity_workspace.html",
        {
            "project": project,
            "organization": project.organization,
            "opportunity": opportunity,
            "workspace": workspace,
            "pursuit_readiness": pursuit_readiness,
            "document_summary": document_summary,
            "relationship_context": relationship_context,
            "score_transparency": {
                "pursuit": explain_pursuit_readiness(pursuit_readiness),
            },
        },
    )


@login_required
@require_POST
def update_opportunity_lifecycle(request, pk, opportunity_id):
    get_object_or_404(Project.objects.select_related("organization"), pk=pk, users=request.user)
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
    target_status = request.POST.get("target_status", "")
    transition_opportunity_lifecycle(opportunity, target_status, actor=request.user)
    ensure_default_tasks(opportunity)
    return redirect("project-pipeline", pk=pk)


@login_required
@require_POST
def assign_opportunity_owner_view(request, pk, opportunity_id):
    get_object_or_404(Project.objects.select_related("organization"), pk=pk, users=request.user)
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
    owner_action = request.POST.get("owner_action", "")
    if owner_action == "assign_me":
        assign_opportunity_owner(opportunity, request.user)
    elif owner_action == "unassign":
        assign_opportunity_owner(opportunity, None)
    return redirect("project-pipeline", pk=pk)


@login_required
@require_POST
def update_opportunity_task_status(request, pk, opportunity_id, task_id):
    get_object_or_404(Project.objects.select_related("organization"), pk=pk, users=request.user)
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
    task = get_object_or_404(OpportunityTask, pk=task_id, opportunity=opportunity)
    target_status = request.POST.get("target_status", "")
    valid_statuses = {value for value, _label in OpportunityTask.Status.choices}
    if target_status in valid_statuses:
        task.status = target_status
        task.save(update_fields=["status", "updated_at"])
    return redirect("project-opportunity-workspace", pk=pk, opportunity_id=opportunity.pk)


@login_required
def project_resource_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    readiness = build_resource_readiness(project, funding_criteria)
    return render(
        request,
        "signals/project_resource_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "readiness": readiness,
        },
    )


@login_required
def project_partnership_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    readiness = build_partnership_readiness(project, funding_criteria)
    return render(
        request,
        "signals/project_partnership_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "readiness": readiness,
        },
    )


@login_required
def project_module_placeholder(request, pk, module):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    module_config = MODULE_PLACEHOLDERS[module]
    return render(
        request,
        "signals/project_module_placeholder.html",
        {
            "project": project,
            "organization": project.organization,
            "module": module_config,
        },
    )


def seo_grant_research(request):
    return render(request, "signals/seo/grant_research.html")


def seo_funding_intelligence(request):
    return render(request, "signals/seo/funding_intelligence.html")


def seo_opportunity_mapping(request):
    return render(request, "signals/seo/opportunity_mapping.html")


def seo_readiness_assessment(request):
    return render(request, "signals/seo/readiness_assessment.html")


def resources_hub(request):
    return render(request, "signals/seo/resources.html")
