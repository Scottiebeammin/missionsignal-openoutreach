from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from openoutreach.core.models import Project
from openoutreach.funding.readiness import build_funding_readiness
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.signals.dashboard import build_executive_dashboard
from openoutreach.signals.discovery import build_discovery_overview
from openoutreach.signals.ecosystem import build_ecosystem_overview
from openoutreach.signals.forms import OrganizationIntakeForm
from openoutreach.signals.government import build_government_readiness
from openoutreach.signals.matching import build_opportunity_matches
from openoutreach.signals.mission_brief import recommended_next_steps
from openoutreach.signals.partnerships import build_partnership_readiness
from openoutreach.signals.resources import build_resource_readiness
from openoutreach.signals.services import create_organization_intake


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


@login_required
def project_intake(request):
    if request.method == "POST":
        form = OrganizationIntakeForm(request.POST)
        if form.is_valid():
            project = create_organization_intake(user=request.user, **form.cleaned_data)
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
    return render(
        request,
        "signals/project_executive_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "dashboard": dashboard,
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
    return render(
        request,
        "signals/project_ecosystem_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "ecosystem": ecosystem,
        },
    )


@login_required
def project_match_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    match_overview = build_opportunity_matches(project, funding_criteria)
    return render(
        request,
        "signals/project_match_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "funding_criteria": funding_criteria,
            "match_overview": match_overview,
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
        },
    )


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
