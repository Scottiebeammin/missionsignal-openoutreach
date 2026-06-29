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
