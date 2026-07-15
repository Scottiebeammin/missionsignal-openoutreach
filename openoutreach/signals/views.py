import os
import time

import stripe
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from openoutreach.core.access import user_is_project_admin
from openoutreach.core.models import OrganizationMember, Project
from openoutreach.funding.models import Opportunity, OpportunityTask
from openoutreach.funding.readiness import build_funding_readiness
from openoutreach.signals.demo_guard import exclude_demo
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.signals.categories import OPPORTUNITY_FOCUS_CATEGORIES
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
from openoutreach.signals.feedback import (
    flag_opportunities,
    kind_for_category,
    not_a_fit_map,
    suppress_top_recommended,
    toggle_feedback,
)
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
from openoutreach.signals.lifecycle import (
    assign_opportunity_owner,
    expire_past_deadline_opportunities,
    transition_opportunity_lifecycle,
)
from openoutreach.signals.matching import build_opportunity_matches
from openoutreach.signals.mission_brief import recommended_next_steps
from openoutreach.signals.models import InterestSignup, MatchFeedback, PilotProfile
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


def client_project(request, pk):
    """Return the project the user owns — or, for staff, ANY project (view-as-client).

    Operators can open any client's portal to see exactly what the client sees; the
    view_as_client context processor shows a banner so the mode is always obvious.
    """
    qs = Project.objects.select_related("organization")
    if request.user.is_staff:
        return get_object_or_404(qs, pk=pk)
    return get_object_or_404(qs, pk=pk, users=request.user)


def _honeypot_tripped(request) -> bool:
    """True when the hidden anti-spam field was filled in — a bot did it, since
    real users never see the field. Named 'company_website' to look tempting."""
    return bool((request.POST.get("company_website") or "").strip())


def public_landing_page(request):
    signup_failed = False
    if request.method == "POST":
        if _honeypot_tripped(request):
            # Silently accept so the bot moves on; nothing is saved.
            return redirect("anansi-atlas-thanks")
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
            "annual_url": os.getenv("STRIPE_ANNUAL_URL", ""),
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
    if _honeypot_tripped(request):
        return redirect("anansi-atlas-question-thanks")   # silently drop the bot
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
            # Fail CLOSED — no invented numbers; the frontend hides the widget.
            return JsonResponse({"claimed": 0, "remaining": 0, "total": _FOUNDING_SEAT_TOTAL, "live": False})
        try:
            stripe.api_key = secret_key
            subs = stripe.Subscription.list(price=price_id, status="active", limit=100)
            claimed = len(subs.data)
        except Exception:
            if _seat_cache is None:
                # Never had a real number — hide rather than fabricate.
                return JsonResponse({"claimed": 0, "remaining": 0, "total": _FOUNDING_SEAT_TOTAL, "live": False})
            claimed = _seat_cache[0]
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
            # Fire the full data treatment in the background — live federal grants
            # (Grants.gov) + grounded AI research — so we don't make the user wait.
            import threading
            from openoutreach.signals.research import auto_ingest_for_new_project as _auto
            threading.Thread(target=_auto, args=(project,), daemon=True).start()
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
    project = client_project(request, pk)
    return render(request, "signals/project_intake_success.html", {"project": project})


def _beneficiary_choices():
    from openoutreach.signals.forms import BENEFICIARY_CHOICES
    return BENEFICIARY_CHOICES


@login_required
def project_analysis_detail(request, pk):
    project = client_project(request, pk)
    return render(
        request,
        "signals/project_analysis_detail.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": getattr(project, "funding_criteria", None),
            "is_account_admin": user_is_project_admin(request.user, project),
            "focus_category_options": OPPORTUNITY_FOCUS_CATEGORIES,
            "beneficiary_options": [label for _val, label in _beneficiary_choices()],
            "website_check": project.organization.website_check,
        },
    )


@login_required
@require_POST
def project_focus_area_update(request, pk):
    """Add or remove an area of support from Settings.

    Seat-authority gated (account admin or staff) — these areas drive
    opportunity matching. Removals are remembered as exclusions so the
    analyzer never re-infers them from mission/website text, then the
    deterministic analysis re-runs so matches reflect the change immediately.
    """
    project = client_project(request, pk)
    if not user_is_project_admin(request.user, project):
        return HttpResponseForbidden("Only your account admin can edit areas of support.")
    action = request.POST.get("action", "")
    value = request.POST.get("value", "").strip()[:100]
    if value and action in {"add", "remove"}:
        organization = project.organization
        canonical = next(
            (c for c in OPPORTUNITY_FOCUS_CATEGORIES if c.casefold() == value.casefold()), value,
        )
        focus = list(organization.focus_areas or [])
        excluded = list(organization.excluded_focus_areas or [])
        if action == "add":
            if canonical.casefold() not in {f.casefold() for f in focus}:
                focus.append(canonical)
            excluded = [e for e in excluded if e.casefold() != canonical.casefold()]
        else:
            focus = [f for f in focus if f.casefold() != canonical.casefold()]
            if canonical.casefold() not in {e.casefold() for e in excluded}:
                excluded.append(canonical)
        organization.focus_areas = focus
        organization.excluded_focus_areas = excluded
        organization.save(update_fields=["focus_areas", "excluded_focus_areas"])
        analyze_project(project, mode="deterministic")
    return redirect("project-analysis-detail", pk=pk)


@login_required
@require_POST
def project_beneficiary_update(request, pk):
    """Add or remove a beneficiary group from Settings — mirrors the areas-of-
    support editor. Removals persist as exclusions so the analyzer never
    re-infers them; re-runs analysis so matching reflects the change."""
    from openoutreach.signals.forms import BENEFICIARY_CHOICES

    project = client_project(request, pk)
    if not user_is_project_admin(request.user, project):
        return HttpResponseForbidden("Only your account admin can edit who you serve.")
    action = request.POST.get("action", "")
    value = request.POST.get("value", "").strip()[:100]
    if value and action in {"add", "remove"}:
        organization = project.organization
        # Accept either the stored value ("youth") or the display label
        # ("Youth & Young People") and always store the canonical value.
        canonical = next(
            (val for val, label in BENEFICIARY_CHOICES
             if value.casefold() in (val.casefold(), label.casefold())),
            value,
        )
        beneficiaries = list(organization.beneficiaries or [])
        excluded = list(organization.excluded_beneficiaries or [])
        if action == "add":
            if canonical.casefold() not in {b.casefold() for b in beneficiaries}:
                beneficiaries.append(canonical)
            excluded = [e for e in excluded if e.casefold() != canonical.casefold()]
        else:
            beneficiaries = [b for b in beneficiaries if b.casefold() != canonical.casefold()]
            if canonical.casefold() not in {e.casefold() for e in excluded}:
                excluded.append(canonical)
        organization.beneficiaries = beneficiaries
        organization.excluded_beneficiaries = excluded
        organization.save(update_fields=["beneficiaries", "excluded_beneficiaries"])
        analyze_project(project, mode="deterministic")
    return redirect("project-analysis-detail", pk=pk)


@login_required
def project_foundation_dashboard(request, pk):
    """Ecosystem → Foundations: IRS-grounded private-foundation intelligence.

    Same build-out as the Funding page — matched foundations as pathway cards
    (trackable into the opportunity pipeline) plus the verified grant receipts
    to organizations like this one.
    """
    from openoutreach.signals.foundations import build_foundation_overview

    project = client_project(request, pk)
    sort = request.GET.get("sort", "fit")
    overview = build_foundation_overview(project, sort=sort)
    return render(
        request,
        "signals/project_foundation_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "overview": overview,
        },
    )


@login_required
@require_POST
def project_foundation_track(request, pk, funder_id):
    """Wire a foundation back into the opportunity field: idempotently create
    the project-scoped Opportunity for this funder and open its workspace."""
    from openoutreach.funding.models import Funder

    project = client_project(request, pk)
    funder = get_object_or_404(Funder, pk=funder_id, active=True)
    external_id = f"funder:{funder.pk}"
    opportunity = Opportunity.objects.filter(project=project, external_id=external_id).first()
    if opportunity is None:
        from django.utils import timezone as _tz

        opportunity = Opportunity.objects.create(
            project=project,
            name=f"{funder.name} — Foundation Grant",
            opportunity_type=Opportunity.OpportunityType.GRANT,
            source_type=Opportunity.SourceType.FUNDER,
            source_name=funder.name,
            external_id=external_id,
            geography=list(funder.geography or []),
            focus_areas=list(funder.focus_areas or []),
            beneficiaries=list(funder.beneficiaries or []),
            eligibility_notes=funder.eligibility_notes,
            source_urls=list(funder.source_urls or ([funder.website] if funder.website else [])),
            verification_status=funder.verification_status,
            notes="Pursued from the Foundations tab.",
            # The client chose to pursue — land it on the Pipeline board's
            # active column, with an honest history entry for the jump.
            lifecycle_status=Opportunity.LifecycleStatus.PURSUING,
            lifecycle_status_history=[{
                "from": "",
                "to": Opportunity.LifecycleStatus.PURSUING.value,
                "actor": request.user.username,
                "updated_at": _tz.now().isoformat(),
                "note": "Pursued from the Foundations tab.",
            }],
        )
        ensure_default_tasks(opportunity)
    return redirect("project-pipeline", pk=project.pk)


@login_required
@require_POST
def project_website_scan(request, pk):
    """Scan the org website and flag profile claims not visible on the site."""
    from openoutreach.signals.website_verification import verify_website_claims

    project = client_project(request, pk)
    verify_website_claims(project.organization, project)
    return redirect("project-analysis-detail", pk=pk)


@login_required
@require_POST
def run_project_analysis(request, pk):
    project = client_project(request, pk)
    analyze_project(project, mode="deterministic")
    return redirect("project-analysis-detail", pk=project.pk)


@login_required
def project_mission_brief(request, pk):
    project = client_project(request, pk)
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
    project = client_project(request, pk)
    funding_criteria = getattr(project, "funding_criteria", None)
    next_steps = recommended_next_steps(project.organization, funding_criteria)
    members = (
        OrganizationMember.objects.filter(project=project)
        .select_related("user")
        .order_by("-is_admin", "created_at")
    )
    # A freshly-minted invite link is shown once (pop from session) so the admin
    # can copy and send it — the link itself is never persisted.
    invite_link = request.session.pop("pending_invite_link", "")
    is_admin = user_is_project_admin(request.user, project)
    return render(
        request,
        "signals/project_organization_workspace.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "recommended_next_steps": next_steps[:5],
            "members": members,
            "is_account_admin": is_admin,
            "current_user_id": request.user.pk,
            "invite_link": invite_link,
        },
    )


@login_required
@require_POST
def project_invite_teammate(request, pk):
    """Account admin mints a signed invite link to send to a teammate."""
    from openoutreach.signals.invites import make_invite_token

    project = client_project(request, pk)
    if not user_is_project_admin(request.user, project):
        return HttpResponseForbidden("Only your account admin can invite teammates.")
    token = make_invite_token(project.pk)
    request.session["pending_invite_link"] = request.build_absolute_uri(
        reverse("project-invite", kwargs={"token": token})
    )
    return redirect("project-organization", pk=pk)


@login_required
@require_POST
def project_remove_seat(request, pk, member_id):
    """Account admin removes a teammate seat (never an admin seat or themselves)."""
    project = client_project(request, pk)
    if not user_is_project_admin(request.user, project):
        return HttpResponseForbidden("Only your account admin can remove teammates.")
    member = get_object_or_404(OrganizationMember, pk=member_id, project=project)
    if member.is_admin or member.user_id == request.user.pk:
        return HttpResponseForbidden("You can't remove an admin seat or yourself.")
    project.users.remove(member.user)
    member.delete()
    return redirect("project-organization", pk=pk)


@login_required
def project_pilot_workspace(request, pk):
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    from datetime import date as _date

    from openoutreach.funding.relevance import (
        is_off_geography, is_research_grant, opportunity_relevance, org_keywords,
    )

    project = client_project(request, pk)
    funding_criteria = getattr(project, "funding_criteria", None)
    readiness = build_funding_readiness(project, funding_criteria)
    # Recommended grant pathways: same relevance ranking the Pathways page uses.
    grants = list(
        Opportunity.objects.filter(project=project, opportunity_type=Opportunity.OpportunityType.GRANT)
        .exclude(status=Opportunity.Status.EXPIRED)
    )
    keywords = org_keywords(project.organization)
    for o in grants:
        o.relevance = 0 if (is_off_geography(o, project.organization) or is_research_grant(o)) else opportunity_relevance(o, keywords)
    grants.sort(key=lambda o: (-o.relevance, o.deadline or _date.max, o.name))
    recommended_grants = [o for o in grants if o.relevance > 0][:6]
    return render(
        request,
        "signals/project_funding_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "readiness": readiness,
            "recommended_grants": recommended_grants,
        },
    )


@login_required
def project_government_dashboard(request, pk):
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    # Verified grants matched to THIS org — the confirmed, source-linked ones a
    # client can act on with confidence. Leads the dashboard: trust over volume.
    from openoutreach.funding.models import Opportunity as _Opp
    _active_opps = _Opp.objects.filter(project=project).exclude(
        status__in=[_Opp.Status.EXPIRED, _Opp.Status.ARCHIVED]
    )
    verified_grants_count = sum(1 for o in _active_opps if o.is_confirmed)
    # Founding-partner welcome: a warm, branded moment on the dashboard for
    # founding partners (and pilots). Reuses the numbers already on the page.
    is_founding = request.user.groups.filter(name="Founding Partners").exists()
    founding_welcome = None
    if is_founding or pilot:
        from openoutreach.signals.foundations import build_foundation_overview
        member = OrganizationMember.objects.filter(user=request.user, project=project).first()
        first = (member.contact_name.split(" ")[0] if member and member.contact_name
                 else request.user.first_name) or "there"
        foundations = build_foundation_overview(project)
        founding_welcome = {
            "first_name": first,
            "org_name": dashboard.organization_name,
            "verified_grants": verified_grants_count,
            "opportunities": dashboard.match_health.total_matches,
            "excellent": dashboard.match_health.excellent_matches,
            "readiness": dashboard.readiness.overall_score,
            "readiness_level": dashboard.readiness.level,
            # The proof: real 990-PF grants to orgs like this one.
            "grant_total": foundations.receipt_total_display,
            "grant_count": f"{foundations.receipt_count:,}" if foundations.receipt_count else 0,
            "funder_count": foundations.receipt_foundation_count,
            "county": foundations.county,
        }
    return render(
        request,
        "signals/project_executive_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "dashboard": dashboard,
            "opportunity_web": opportunity_web,
            "pilot": pilot,
            "founding_welcome": founding_welcome,
            "verified_grants_count": verified_grants_count,
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
    funding_criteria = getattr(project, "funding_criteria", None)
    match_overview = build_opportunity_matches(project, funding_criteria)
    # Drop reference matches the org marked "not a fit" from the recommendation
    # shelf (category inventories below stay complete), then pair each surviving
    # match with its feedback kind so the card button can post the right key.
    suppress_top_recommended(match_overview, not_a_fit_map(project))
    top_recommended_cards = [
        (match, kind_for_category(match.category)) for match in match_overview.top_recommended
    ]
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
            "top_recommended_cards": top_recommended_cards,
            "show_all": request.GET.get("all") == "1",
            "match_limit": ":1000" if request.GET.get("all") == "1" else ":10",
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
    funding_criteria = getattr(project, "funding_criteria", None)
    discovery = build_discovery_overview(project, funding_criteria)
    match_overview = build_opportunity_matches(project, funding_criteria)
    actions = list(match_overview.highest_leverage_actions)

    # Ranked opportunity list: top 10 recommended + the full set behind "see all".
    # Rank by priority (high→low), then soonest real deadline, then name. Expired/
    # archived are excluded from the active recommendations.
    from datetime import date as _date
    from openoutreach.funding.models import Opportunity
    from openoutreach.funding.relevance import org_keywords, opportunity_relevance, is_off_geography, is_research_grant
    _prio = {
        Opportunity.PriorityLevel.HIGH: 0,
        Opportunity.PriorityLevel.MEDIUM: 1,
        Opportunity.PriorityLevel.LOW: 2,
    }
    ranked = list(
        Opportunity.objects.filter(project=project).exclude(
            status__in=[Opportunity.Status.EXPIRED, Opportunity.Status.ARCHIVED]
        )
    )
    # Score each opportunity against what THIS org does + who it serves, so only
    # relevant ones rise to the top (off-topic grants score 0 and drop out).
    keywords = org_keywords(project.organization)
    for o in ranked:
        # Foreign/overseas grants are disqualified outright (relevance 0), even if the
        # topic overlaps — a Central Florida nonprofit can't use a "...in Brazil" grant.
        o.relevance = 0 if (is_off_geography(o, project.organization) or is_research_grant(o)) else opportunity_relevance(o, keywords)
        # Trust tier: confirmed = human-verified AND backed by a real source link.
        o.confirmed = o.is_confirmed
        o.source_url = o.real_source_url()
    # Verified-with-source opportunities rank above AI-suggested ones at equal relevance.
    ranked.sort(key=lambda o: (-o.relevance, 0 if o.confirmed else 1, _prio.get(o.priority_level, 3), o.deadline or _date.max, o.name))

    # "Not a fit" feedback: flagged opportunities never make the top-10 shelf (the
    # next best match refills the slot) but stay in "see all" with a muted tag.
    feedback_map = not_a_fit_map(project)
    flag_opportunities(ranked, feedback_map)

    # Top 10 = most relevant matches only (relevance > 0). Off-topic ones still live
    # in "see all" but never masquerade as recommendations.
    relevant = [o for o in ranked if o.relevance > 0]
    top_pool = [o for o in relevant if not o.not_a_fit] or [o for o in ranked if not o.not_a_fit]
    top = top_pool[:10]

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
            "top_opportunities": top,
            "all_opportunities": ranked,
            "opportunity_total": len(ranked),
            "relevant_total": len(relevant),
            "confirmed_total": sum(1 for o in ranked if o.confirmed),
            **_workflow_context(project, "prioritize", actions[:2]),
        },
    )


@login_required
def project_pipeline_workspace(request, pk):
    project = client_project(request, pk)
    # Sweep any past-deadline opportunities the org never applied to into EXPIRED
    # before building the view, so the pipeline always reflects current deadlines.
    expire_past_deadline_opportunities(project)
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
    project = client_project(request, pk)
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
    project = client_project(request, pk)
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id, project=project)
    target_status = request.POST.get("target_status", "")
    transition_opportunity_lifecycle(opportunity, target_status, actor=request.user)
    ensure_default_tasks(opportunity)
    return redirect("project-pipeline", pk=pk)


@login_required
@require_POST
def assign_opportunity_owner_view(request, pk, opportunity_id):
    project = client_project(request, pk)
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id, project=project)
    owner_action = request.POST.get("owner_action", "")
    if owner_action == "assign_me":
        assign_opportunity_owner(opportunity, request.user)
    elif owner_action == "unassign":
        assign_opportunity_owner(opportunity, None)
    return redirect("project-pipeline", pk=pk)


@login_required
@require_POST
def toggle_opportunity_interest(request, pk, opportunity_id):
    """Mark/unmark an opportunity as 'interested' (tracked). While interested and not
    yet applied, the org gets a weekly reminder until they apply or un-track it."""
    from django.utils import timezone
    project = client_project(request, pk)
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id, project=project)
    if opportunity.is_interested:
        opportunity.is_interested = False
        opportunity.interest_marked_at = None
    else:
        opportunity.is_interested = True
        opportunity.interest_marked_at = timezone.now()
    opportunity.save(update_fields=["is_interested", "interest_marked_at", "updated_at"])
    from django.utils.http import url_has_allowed_host_and_scheme
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(referer)
    return redirect("project-opportunities", pk=pk)


@login_required
@require_POST
def project_match_feedback(request, pk):
    """Toggle a 'not a fit' verdict on a recommended match.

    Same staff-or-member gate as every project view (client_project). POSTing the
    same (kind, target_key) twice lifts the flag again. Redirects back to the
    posting page via the hidden ``next`` field (querystring preserved).
    """
    from django.utils.http import url_has_allowed_host_and_scheme

    project = client_project(request, pk)
    kind = request.POST.get("kind", "")
    target_key = request.POST.get("target_key", "").strip()[:300]
    if kind in MatchFeedback.Kind.values and target_key:
        toggle_feedback(
            project, kind, target_key, user=request.user,
            note=request.POST.get("note", "").strip(),
        )
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("project-opportunities", pk=pk)


@login_required
@require_POST
def update_opportunity_task_status(request, pk, opportunity_id, task_id):
    project = client_project(request, pk)
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id, project=project)
    task = get_object_or_404(OpportunityTask, pk=task_id, opportunity=opportunity)
    target_status = request.POST.get("target_status", "")
    valid_statuses = {value for value, _label in OpportunityTask.Status.choices}
    if target_status in valid_statuses:
        task.status = target_status
        task.save(update_fields=["status", "updated_at"])
    return redirect("project-opportunity-workspace", pk=pk, opportunity_id=opportunity.pk)


@login_required
def project_resource_dashboard(request, pk):
    project = client_project(request, pk)
    funding_criteria = getattr(project, "funding_criteria", None)
    readiness = build_resource_readiness(project, funding_criteria)
    # Surface the actual free/low-cost resource directory (TechSoup, AmeriCorps, etc.),
    # grouped by type — these are the real, verified supports for the org to act on.
    from openoutreach.funding.models import ResourceProvider
    resources = list(
        exclude_demo(ResourceProvider.objects.filter(active=True)).order_by("resource_type", "name")
    )
    return render(
        request,
        "signals/project_resource_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "readiness": readiness,
            "resources": resources,
        },
    )


@login_required
def project_partnership_dashboard(request, pk):
    project = client_project(request, pk)
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
    project = client_project(request, pk)
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


def privacy_policy(request):
    return render(request, "signals/seo/privacy.html")


def terms_of_service(request):
    return render(request, "signals/seo/terms.html")
