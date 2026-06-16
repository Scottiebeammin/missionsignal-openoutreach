from django.urls import path

from openoutreach.signals import views

urlpatterns = [
    path("", views.project_intake, name="project-intake"),
    path("projects/<int:pk>/created/", views.project_intake_success, name="project-intake-success"),
    path("projects/<int:pk>/analysis/", views.project_analysis_detail, name="project-analysis-detail"),
    path("projects/<int:pk>/analysis/run/", views.run_project_analysis, name="run-project-analysis"),
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
        "projects/<int:pk>/partnerships/",
        views.project_module_placeholder,
        {"module": "partnerships"},
        name="project-partnerships",
    ),
    path(
        "projects/<int:pk>/resources/",
        views.project_module_placeholder,
        {"module": "resources"},
        name="project-resources",
    ),
]
