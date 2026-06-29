from django.urls import path

from openoutreach.signals import views
from openoutreach.signals import operator_views

urlpatterns = [
    path("operator/", operator_views.operator_dashboard, name="operator-dashboard"),
    path("operator/organizations/", operator_views.operator_organizations, name="operator-organizations"),
    path("operator/organizations/<int:pk>/", operator_views.operator_org_detail, name="operator-org-detail"),
    path("operator/organizations/<int:pk>/research/", operator_views.operator_run_research, name="operator-run-research"),
    path("operator/organizations/<int:pk>/analysis/", operator_views.operator_run_analysis, name="operator-run-analysis"),
    path("operator/pipeline/", operator_views.operator_pipeline, name="operator-pipeline"),
    path("operator/pipeline/add/", operator_views.operator_pipeline_add, name="operator-pipeline-add"),
    path("operator/pipeline/<int:pk>/update/", operator_views.operator_pipeline_update, name="operator-pipeline-update"),
    path("operator/pipeline/<int:pk>/draft/", operator_views.operator_pipeline_draft, name="operator-pipeline-draft"),
    path("operator/pipeline/<int:pk>/delete/", operator_views.operator_pipeline_delete, name="operator-pipeline-delete"),
    path("operator/funders/", operator_views.operator_funders, name="operator-funders"),
    path("operator/funders/<int:pk>/verify/", operator_views.operator_funder_verify, name="operator-funder-verify"),
    path("operator/funders/<int:pk>/research/", operator_views.operator_research_funder, name="operator-funder-research"),
    path("operator/waitlist/", operator_views.operator_waitlist, name="operator-waitlist"),
    path("operator/waitlist/<int:pk>/status/", operator_views.operator_waitlist_status, name="operator-waitlist-status"),
    path("operator/waitlist/<int:pk>/enrich/", operator_views.operator_enrich_signup, name="operator-waitlist-enrich"),
    # SEO content pages
    path("nonprofit-grant-research/", views.seo_grant_research, name="nonprofit-grant-research"),
    path("nonprofit-funding-intelligence/", views.seo_funding_intelligence, name="nonprofit-funding-intelligence"),
    path("opportunity-mapping-for-nonprofits/", views.seo_opportunity_mapping, name="opportunity-mapping-nonprofits"),
    path("nonprofit-readiness-assessment/", views.seo_readiness_assessment, name="nonprofit-readiness-assessment"),
    # Public homepage = the landing page (so the bare domain shows it, not a login wall).
    path("", views.public_landing_page, name="home"),
    path("anansi-atlas/", views.public_landing_page, name="anansi-atlas-landing"),
    path("anansi-atlas/thanks/", views.public_landing_thanks, name="anansi-atlas-thanks"),
    path("anansi-atlas/seats/", views.founding_seat_count, name="founding-seat-count"),
    path("pilot/", views.pilot_onboarding, name="pilot-onboarding"),
    # Login-gated org intake — reached after sign-in via the portal redirect (by name).
    path("intake/", views.project_intake, name="project-intake"),
    path("projects/<int:pk>/created/", views.project_intake_success, name="project-intake-success"),
    path("projects/<int:pk>/analysis/", views.project_analysis_detail, name="project-analysis-detail"),
    path("projects/<int:pk>/analysis/run/", views.run_project_analysis, name="run-project-analysis"),
    path("projects/<int:pk>/dashboard/", views.project_executive_dashboard, name="project-dashboard"),
    path("projects/<int:pk>/readiness/", views.project_readiness_dashboard, name="project-readiness"),
    path("projects/<int:pk>/relationships/", views.project_relationships_dashboard, name="project-relationships"),
    path("projects/<int:pk>/documents/", views.project_documents_dashboard, name="project-documents"),
    path("projects/<int:pk>/evidence/", views.project_evidence_dashboard, name="project-evidence"),
    path("projects/<int:pk>/celebrations/", views.project_celebrations_dashboard, name="project-celebrations"),
    path("projects/<int:pk>/organization/", views.project_organization_workspace, name="project-organization"),
    path("projects/<int:pk>/pilot/", views.project_pilot_workspace, name="project-pilot-workspace"),
    path(
        "projects/<int:pk>/pilot/questionnaire/",
        views.project_pilot_questionnaire,
        name="project-pilot-questionnaire",
    ),
    path("projects/<int:pk>/pilot/feedback/", views.project_pilot_feedback, name="project-pilot-feedback"),
    path("projects/<int:pk>/mission-brief/", views.project_mission_brief, name="project-mission-brief"),
    path(
        "projects/<int:pk>/programs/",
        views.project_module_placeholder,
        {"module": "programs"},
        name="project-programs",
    ),
    path(
        "projects/<int:pk>/funding/",
        views.project_funding_dashboard,
        name="project-funding",
    ),
    path(
        "projects/<int:pk>/government/",
        views.project_government_dashboard,
        name="project-government",
    ),
    path(
        "projects/<int:pk>/ecosystem/",
        views.project_ecosystem_dashboard,
        name="project-ecosystem",
    ),
    path(
        "projects/<int:pk>/web/",
        views.project_opportunity_web,
        name="project-opportunity-web",
    ),
    path(
        "projects/<int:pk>/snapshot/",
        views.project_snapshot,
        name="project-snapshot",
    ),
    path(
        "s/<uuid:token>/",
        views.project_snapshot_public,
        name="project-snapshot-public",
    ),
    path(
        "projects/<int:pk>/matches/",
        views.project_match_dashboard,
        name="project-matches",
    ),
    path(
        "projects/<int:pk>/opportunities/",
        views.project_opportunities_workspace,
        name="project-opportunities",
    ),
    path(
        "projects/<int:pk>/opportunities/<int:opportunity_id>/",
        views.project_opportunity_workspace,
        name="project-opportunity-workspace",
    ),
    path(
        "projects/<int:pk>/opportunities/<int:opportunity_id>/tasks/<int:task_id>/status/",
        views.update_opportunity_task_status,
        name="project-opportunity-task-status",
    ),
    path(
        "projects/<int:pk>/discovery/",
        views.project_discovery_dashboard,
        name="project-discovery",
    ),
    path(
        "projects/<int:pk>/pipeline/",
        views.project_pipeline_workspace,
        name="project-pipeline",
    ),
    path(
        "projects/<int:pk>/pipeline/<int:opportunity_id>/lifecycle/",
        views.update_opportunity_lifecycle,
        name="project-pipeline-lifecycle-update",
    ),
    path(
        "projects/<int:pk>/pipeline/<int:opportunity_id>/owner/",
        views.assign_opportunity_owner_view,
        name="project-pipeline-owner-update",
    ),
    path(
        "projects/<int:pk>/partnerships/",
        views.project_partnership_dashboard,
        name="project-partnerships",
    ),
    path(
        "projects/<int:pk>/resources/",
        views.project_resource_dashboard,
        name="project-resources",
    ),
]
