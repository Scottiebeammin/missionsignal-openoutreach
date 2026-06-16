from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("core", "0005_project")]
    operations = [
        migrations.CreateModel(name="Source", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("key", models.SlugField(max_length=100, unique=True)), ("name", models.CharField(max_length=255)),
            ("source_type", models.CharField(choices=[("manual", "Manual"), ("api", "API"), ("web", "Web"), ("rss", "RSS")], max_length=20)),
            ("base_url", models.URLField(blank=True, default="", max_length=500)), ("active", models.BooleanField(default=True)),
            ("configuration", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="SearchQuery", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("signal_type", models.CharField(choices=[("funding", "FundingSignal")], default="funding", max_length=20)), ("query", models.TextField()),
            ("filters", models.JSONField(blank=True, default=dict)), ("filters_hash", models.CharField(editable=False, max_length=64)),
            ("rationale", models.TextField(blank=True, default="")), ("priority", models.PositiveSmallIntegerField(default=0)),
            ("status", models.CharField(choices=[("generated", "Generated"), ("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("archived", "Archived")], default="generated", max_length=20)),
            ("result_count", models.PositiveIntegerField(default=0)), ("generated_at", models.DateTimeField(auto_now_add=True)), ("executed_at", models.DateTimeField(blank=True, null=True)), ("error", models.TextField(blank=True, default="")),
            ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="search_queries", to="core.project")),
            ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="search_queries", to="sources.source")),
        ], options={"constraints": [models.UniqueConstraint(fields=("project", "signal_type", "source", "query", "filters_hash"), name="unique_project_source_query")]}),
        migrations.CreateModel(name="SourceRecord", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("external_id", models.CharField(blank=True, default="", max_length=500)), ("canonical_url", models.URLField(blank=True, default="", max_length=1000)),
            ("title", models.CharField(blank=True, default="", max_length=500)), ("raw_data", models.JSONField(blank=True, default=dict)), ("raw_text", models.TextField(blank=True, default="")),
            ("content_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)), ("discovered_at", models.DateTimeField(auto_now_add=True)),
            ("fetched_at", models.DateTimeField(blank=True, null=True)), ("last_seen_at", models.DateTimeField(auto_now_add=True)),
            ("processing_status", models.CharField(choices=[("discovered", "Discovered"), ("fetched", "Fetched"), ("processed", "Processed"), ("failed", "Failed")], default="discovered", max_length=20)),
            ("processing_error", models.TextField(blank=True, default="")),
            ("search_queries", models.ManyToManyField(blank=True, related_name="source_records", to="sources.searchquery")),
            ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="sources.source")),
        ], options={"constraints": [
            models.UniqueConstraint(condition=~models.Q(("external_id", "")), fields=("source", "external_id"), name="unique_source_external_id"),
            models.UniqueConstraint(condition=models.Q(("canonical_url__gt", ""), ("external_id", "")), fields=("source", "canonical_url"), name="unique_source_canonical_url"),
        ]}),
    ]
