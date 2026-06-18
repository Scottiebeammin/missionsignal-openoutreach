from django.contrib.auth.decorators import login_required
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
    build_document_vault_summary,
    build_evidence_library_summary,
    build_opportunity_document_summary,
)
from openoutreach.signals.ecosystem import build_ecosystem_overview
from openoutreach.signals.forms import OrganizationIntakeForm
from openoutreach.signals.forecasting import build_pipeline_forecast
from openoutreach.signals.government import build_government_readiness
from openoutreach.signals.lifecycle import assign_opportunity_owner, transition_opportunity_lifecycle
from openoutreach.signals.matching import build_opportunity_matches
from openoutreach.signals.mission_brief import recommended_next_steps
from openoutreach.signals.opportunity_work import build_opportunity_workspace, ensure_default_tasks
from openoutreach.signals.partnerships import build_partnership_readiness
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
        },
    )


@login_required
def project_relationships_dashboard(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    return render(
        request,
        "signals/project_relationships_dashboard.html",
        {
            "project": project,
            "organization": project.organization,
            "relationships": build_relationship_overview(project),
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
    forecast = build_pipeline_forecast()
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
        },
    )


@login_required
def project_pipeline_workspace(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("organization"), pk=pk, users=request.user,
    )
    funding_criteria = getattr(project, "funding_criteria", None)
    discovery = build_discovery_overview(project, funding_criteria)
    forecast = build_pipeline_forecast()
    return render(
        request,
        "signals/project_pipeline_workspace.html",
        {
            "project": project,
            "organization": project.organization,
            "discovery": discovery,
            "lifecycle": discovery.lifecycle_summary,
            "forecast": forecast,
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
