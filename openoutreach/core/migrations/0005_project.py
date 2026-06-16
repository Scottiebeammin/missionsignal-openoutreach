from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_alter_task_task_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("website", models.URLField(max_length=500)),
                ("mission", models.TextField()),
                ("organization_summary", models.TextField(blank=True, default="")),
                ("organization_type", models.JSONField(blank=True, default=None, null=True)),
                ("legal_structure", models.JSONField(blank=True, default=None, null=True)),
                ("nonprofit_status", models.JSONField(blank=True, default=None, null=True)),
                ("headquarters_location", models.JSONField(blank=True, default=None, null=True)),
                ("city", models.CharField(blank=True, default="", max_length=255)),
                ("county", models.CharField(blank=True, default="", max_length=255)),
                ("state", models.CharField(blank=True, default="", max_length=255)),
                ("service_area_notes", models.TextField(blank=True, default="")),
                ("service_geographies", models.JSONField(blank=True, default=list)),
                ("focus_areas", models.JSONField(blank=True, default=list)),
                ("beneficiaries", models.JSONField(blank=True, default=list)),
                ("capabilities", models.JSONField(blank=True, default=list)),
                ("outcomes_and_impact", models.JSONField(blank=True, default=list)),
                ("aliases", models.JSONField(blank=True, default=list)),
                ("search_keywords", models.JSONField(blank=True, default=list)),
                ("analysis_status", models.CharField(choices=[("pending", "Pending"), ("fetching", "Fetching"), ("analyzing", "Analyzing"), ("ready", "Ready"), ("partial", "Partial"), ("failed", "Failed"), ("needs_review", "Needs Review")], default="pending", max_length=20)),
                ("analysis_confidence", models.FloatField(blank=True, null=True)),
                ("analysis_warnings", models.JSONField(blank=True, default=list)),
                ("analyzer_version", models.CharField(blank=True, default="", max_length=100)),
                ("last_analyzed_at", models.DateTimeField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("users", models.ManyToManyField(blank=True, related_name="missionsignal_organizations", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("programs", models.TextField()),
                ("program_summaries", models.JSONField(blank=True, default=list)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="core.organization")),
                ("users", models.ManyToManyField(blank=True, related_name="missionsignal_projects", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
