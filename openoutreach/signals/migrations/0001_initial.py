from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("core", "0005_project")]
    operations = [
        migrations.CreateModel(name="OrganizationAnalysisRun", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("partial", "Partial"), ("failed", "Failed")], default="pending", max_length=20)),
            ("analyzer_version", models.CharField(blank=True, default="", max_length=100)),
            ("input_snapshot", models.JSONField(blank=True, default=dict)), ("output_snapshot", models.JSONField(blank=True, default=dict)),
            ("warnings", models.JSONField(blank=True, default=list)), ("error", models.TextField(blank=True, default="")),
            ("started_at", models.DateTimeField(blank=True, null=True)), ("completed_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="analysis_runs", to="core.organization")),
        ]),
        migrations.CreateModel(name="OrganizationSourcePage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("url", models.URLField(max_length=1000)), ("canonical_url", models.URLField(blank=True, default="", max_length=1000)),
            ("page_type", models.CharField(blank=True, default="", max_length=50)), ("title", models.CharField(blank=True, default="", max_length=500)),
            ("raw_text", models.TextField(blank=True, default="")), ("content_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
            ("fetch_status", models.CharField(choices=[("pending", "Pending"), ("fetched", "Fetched"), ("failed", "Failed")], default="pending", max_length=20)),
            ("fetched_at", models.DateTimeField(blank=True, null=True)), ("error", models.TextField(blank=True, default="")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_pages", to="core.organization")),
        ], options={"constraints": [models.UniqueConstraint(fields=("organization", "url"), name="unique_organization_source_page")]}),
    ]
