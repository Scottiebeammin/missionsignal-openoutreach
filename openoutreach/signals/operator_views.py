import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _operator_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


@_operator_required
def operator_dashboard(request):
    from openoutreach.core.models import Project
    from openoutreach.funding.models import Funder, Opportunity, PartnerOrganization

    # Find the InterestSignup model - try both possible locations
    try:
        from openoutreach.signals.models import InterestSignup
        recent_signups = InterestSignup.objects.order_by("-created_at")[:5]
        total_signups = InterestSignup.objects.count()
    except (ImportError, Exception):
        recent_signups = []
        total_signups = 0

    projects = Project.objects.select_related("organization").order_by("-created_at")
    total_projects = projects.count()

    # Projects with no opportunities (need research)
    from django.db.models import Count
    needs_research = projects.annotate(opp_count=Count("opportunity")).filter(opp_count=0)

    ctx = {
        "total_projects": total_projects,
        "total_signups": total_signups,
        "total_funders": Funder.objects.filter(active=True).count(),
        "total_opportunities": Opportunity.objects.count(),
        "recent_signups": recent_signups,
        "needs_research": needs_research[:5],
        "recent_projects": projects[:5],
    }
    return render(request, "signals/operator/dashboard.html", ctx)


@_operator_required
def operator_organizations(request):
    from openoutreach.core.models import Project
    from django.db.models import Count

    projects = (
        Project.objects.select_related("organization")
        .annotate(
            opp_count=Count("opportunity", distinct=True),
        )
        .order_by("-created_at")
    )

    ctx = {"projects": projects}
    return render(request, "signals/operator/organizations.html", ctx)


@_operator_required
def operator_org_detail(request, pk):
    from openoutreach.core.models import Project
    from openoutreach.funding.models import Funder, Opportunity, PartnerOrganization, GovernmentEntity, ResourceProvider
    from django.db.models import Count

    project = get_object_or_404(Project.objects.select_related("organization"), pk=pk)

    opportunities = Opportunity.objects.filter(project=project).order_by("-created_at")
    opp_by_type = {}
    for opp in opportunities:
        t = opp.get_opportunity_type_display()
        opp_by_type[t] = opp_by_type.get(t, 0) + 1

    try:
        from openoutreach.signals.models import OrganizationAnalysisRun
        last_analysis = OrganizationAnalysisRun.objects.filter(project=project).order_by("-created_at").first()
    except Exception:
        last_analysis = None

    ctx = {
        "project": project,
        "org": project.organization,
        "opportunities": opportunities[:10],
        "opp_by_type": opp_by_type,
        "opp_count": opportunities.count(),
        "last_analysis": last_analysis,
    }
    return render(request, "signals/operator/org_detail.html", ctx)


@_operator_required
@require_POST
def operator_run_research(request, pk):
    from openoutreach.core.models import Project
    from openoutreach.signals.research import research_project

    project = get_object_or_404(Project.objects.select_related("organization"), pk=pk)
    try:
        counts = research_project(project)
        parts = [f"{v} {k}" for k, v in counts.items() if v]
        messages.success(request, f"Research complete for {project.organization.name}: {', '.join(parts)}")
    except Exception as e:
        messages.error(request, f"Research failed: {e}")
    return redirect("operator-org-detail", pk=pk)


@_operator_required
@require_POST
def operator_run_analysis(request, pk):
    from openoutreach.core.models import Project
    from openoutreach.signals.analysis_service import analyze_project

    project = get_object_or_404(Project.objects.select_related("organization"), pk=pk)
    try:
        analyze_project(project)
        messages.success(request, f"Analysis complete for {project.organization.name}.")
    except Exception as e:
        messages.error(request, f"Analysis failed: {e}")
    return redirect("operator-org-detail", pk=pk)


@_operator_required
@_operator_required
@require_POST
def operator_waitlist_status(request, pk):
    from openoutreach.signals.models import InterestSignup
    signup = get_object_or_404(InterestSignup, pk=pk)
    new_status = request.POST.get("status", "").strip()
    if new_status in InterestSignup.Status.values:
        signup.status = new_status
        signup.save(update_fields=["status"])
        messages.success(request, f"Updated {signup.name} → {signup.get_status_display()}")
    else:
        messages.error(request, f"Invalid status: {new_status}")
    return redirect("operator-waitlist")


@_operator_required
def operator_funders(request):
    from openoutreach.funding.models import Funder
    status_filter = request.GET.get("status", "")
    qs = Funder.objects.order_by("verification_status", "name")
    if status_filter:
        qs = qs.filter(verification_status=status_filter)

    # Normalize geography to list for consistent template rendering
    funders = list(qs)
    for f in funders:
        if isinstance(f.geography, str):
            f.geography = [f.geography] if f.geography else []

    from django.db.models import Count
    status_counts = {
        row["verification_status"]: row["count"]
        for row in Funder.objects.values("verification_status").annotate(count=Count("id"))
    }
    ctx = {
        "funders": funders,
        "status_filter": status_filter,
        "status_counts": status_counts,
        "total": Funder.objects.count(),
    }
    return render(request, "signals/operator/funders.html", ctx)


@_operator_required
@require_POST
def operator_funder_verify(request, pk):
    from openoutreach.funding.models import Funder
    from django.utils import timezone
    funder = get_object_or_404(Funder, pk=pk)
    new_status = request.POST.get("verification_status", "").strip()
    note = request.POST.get("note", "").strip()
    if new_status in Funder.VerificationStatus.values:
        funder.verification_status = new_status
        funder.last_reviewed_at = timezone.now()
        if note:
            funder.notes = (funder.notes + "\n\n" + note).strip() if funder.notes else note
        funder.save(update_fields=["verification_status", "last_reviewed_at", "notes"])
        messages.success(request, f"{funder.name} → {funder.get_verification_status_display()}")
    else:
        messages.error(request, f"Invalid status: {new_status}")
    next_url = request.POST.get("next", "operator-funders")
    status_param = request.POST.get("status_filter", "")
    base = redirect("operator-funders")
    if status_param:
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse("operator-funders") + f"?status={status_param}")
    return redirect("operator-funders")


@_operator_required
@require_POST
def operator_research_funder(request, pk):
    from openoutreach.funding.models import Funder
    from openoutreach.signals.research import research_funder
    import threading

    funder = get_object_or_404(Funder, pk=pk)
    status_filter = request.POST.get("status_filter", "")

    def _run():
        try:
            research_funder(funder)
        except Exception as e:
            logger.error("Funder research failed for pk=%s: %s", pk, e)

    threading.Thread(target=_run, daemon=True).start()
    messages.success(request, f"Research started for {funder.name} — refresh in a moment.")
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    url = reverse("operator-funders")
    if status_filter:
        url += f"?status={status_filter}"
    return HttpResponseRedirect(url)


@_operator_required
@require_POST
def operator_enrich_signup(request, pk):
    from openoutreach.signals.models import InterestSignup
    from openoutreach.signals.research import research_signup
    import threading

    signup = get_object_or_404(InterestSignup, pk=pk)

    def _run():
        try:
            research_signup(signup)
        except Exception as e:
            logger.error("Signup enrichment failed for pk=%s: %s", pk, e)

    threading.Thread(target=_run, daemon=True).start()
    messages.success(request, f"Enrichment started for {signup.organization or signup.email} — refresh in a moment.")
    return redirect("operator-waitlist")


@_operator_required
def operator_pipeline(request):
    from openoutreach.signals.models import SalesLead
    status_filter = request.GET.get("status", "")
    source_filter = request.GET.get("source", "")
    qs = SalesLead.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if source_filter:
        qs = qs.filter(source=source_filter)

    status_counts = {s.value: SalesLead.objects.filter(status=s).count() for s in SalesLead.Status}
    ctx = {
        "leads": qs,
        "status_filter": status_filter,
        "source_filter": source_filter,
        "status_counts": status_counts,
        "total": SalesLead.objects.count(),
        "closed": status_counts.get("closed", 0),
        "statuses": SalesLead.Status.choices,
        "sources": SalesLead.Source.choices,
    }
    return render(request, "signals/operator/pipeline.html", ctx)


@_operator_required
@require_POST
def operator_pipeline_add(request):
    from openoutreach.signals.models import SalesLead
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name is required.")
        return redirect("operator-pipeline")
    SalesLead.objects.create(
        name=name,
        organization=request.POST.get("organization", "").strip(),
        email=request.POST.get("email", "").strip(),
        phone=request.POST.get("phone", "").strip(),
        role=request.POST.get("role", "").strip(),
        linkedin_url=request.POST.get("linkedin_url", "").strip(),
        source=request.POST.get("source", SalesLead.Source.WARM),
        notes=request.POST.get("notes", "").strip(),
    )
    messages.success(request, f"Added {name} to the pipeline.")
    return redirect("operator-pipeline")


@_operator_required
@require_POST
def operator_pipeline_update(request, pk):
    from openoutreach.signals.models import SalesLead
    lead = get_object_or_404(SalesLead, pk=pk)
    new_status = request.POST.get("status", "").strip()
    note = request.POST.get("note", "").strip()
    follow_up = request.POST.get("next_follow_up", "").strip()

    update_fields = []
    if new_status in SalesLead.Status.values:
        lead.status = new_status
        update_fields.append("status")
    if note:
        from django.utils import timezone
        stamp = timezone.now().strftime("%b %-d")
        lead.notes = (f"[{stamp}] {note}\n\n" + lead.notes).strip()
        update_fields.append("notes")
    if follow_up:
        from datetime import date
        try:
            lead.next_follow_up = date.fromisoformat(follow_up)
            update_fields.append("next_follow_up")
        except ValueError:
            pass
    if update_fields:
        update_fields.append("updated_at")
        lead.save(update_fields=update_fields)
    messages.success(request, f"Updated {lead.name}.")
    return redirect("operator-pipeline")


@_operator_required
@require_POST
def operator_pipeline_draft(request, pk):
    from openoutreach.signals.models import SalesLead
    from pydantic_ai import Agent
    from openoutreach.core.llm import get_llm_model, run_agent_sync

    lead = get_object_or_404(SalesLead, pk=pk)
    source_label = lead.get_source_display()
    tone = "warm, personal, reference shared context" if lead.source == SalesLead.Source.WARM else "professional cold outreach, concise"

    prompt = f"""Write a short sales outreach email for Anansi Atlas — a nonprofit opportunity intelligence platform ($150/month founding partner rate).

Lead details:
- Name: {lead.name}
- Organization: {lead.organization or 'unknown'}
- Role: {lead.role or 'unknown'}
- Source: {source_label}
- Notes: {lead.notes or 'none'}

Tone: {tone}
Length: 5-8 sentences max. No subject line. No sign-off needed (we'll add it).
Goal: get them on a 45-minute founder walkthrough call.
Do not mention pricing unless they asked. End with a soft CTA — "would love to show you what it looks like for [org name]" style.
Return only the email body text."""

    try:
        agent = Agent(get_llm_model(), model_settings={"temperature": 0.7, "timeout": 60})
        draft = run_agent_sync(agent.run(prompt)).output.strip()
        lead.outreach_draft = draft
        lead.save(update_fields=["outreach_draft", "updated_at"])
        messages.success(request, f"Draft generated for {lead.name}.")
    except Exception as e:
        messages.error(request, f"Draft failed: {e}")
    return redirect("operator-pipeline")


@_operator_required
@require_POST
def operator_pipeline_delete(request, pk):
    from openoutreach.signals.models import SalesLead
    lead = get_object_or_404(SalesLead, pk=pk)
    name = lead.name
    lead.delete()
    messages.success(request, f"Removed {name} from pipeline.")
    return redirect("operator-pipeline")


@_operator_required
def operator_waitlist(request):
    try:
        from openoutreach.signals.models import InterestSignup
        signups = InterestSignup.objects.order_by("-created_at")
        nurture_counts = {
            "step_0": signups.filter(nurture_step=0).count(),
            "step_1": signups.filter(nurture_step=1).count(),
            "step_2": signups.filter(nurture_step=2).count(),
            "step_3": signups.filter(nurture_step=3).count(),
        }
        status_counts = {
            s.value: signups.filter(status=s).count()
            for s in InterestSignup.Status
        }
    except Exception:
        signups = []
        nurture_counts = {}
        status_counts = {}

    ctx = {"signups": signups, "nurture_counts": nurture_counts, "status_counts": status_counts}
    return render(request, "signals/operator/waitlist.html", ctx)
