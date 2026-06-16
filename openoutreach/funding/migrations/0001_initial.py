from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import openoutreach.funding.models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("core", "0005_project"), ("signals", "0001_initial"), ("sources", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Funder", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=500)),
            ("website", models.URLField(blank=True, default="", max_length=500)), ("description", models.TextField(blank=True, default="")),
            ("funder_type", models.CharField(choices=[("government", "Government"), ("foundation", "Foundation"), ("corporate", "Corporate"), ("multilateral", "Multilateral"), ("community", "Community"), ("other", "Other")], default="other", max_length=30)),
            ("geography", models.JSONField(blank=True, default=list)), ("external_ids", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="FundingCriteria", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("eligible_applicant_types", models.JSONField(blank=True, default=list)), ("likely_funder_types", models.JSONField(blank=True, default=list)), ("likely_opportunity_types", models.JSONField(blank=True, default=list)),
            ("focus_areas", models.JSONField(blank=True, default=list)), ("beneficiaries", models.JSONField(blank=True, default=list)), ("eligible_geographies", models.JSONField(blank=True, default=list)),
            ("program_areas", models.JSONField(blank=True, default=list)), ("funding_use_categories", models.JSONField(blank=True, default=list)),
            ("likely_amount_min", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)), ("likely_amount_max", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
            ("deadline_horizon_days", models.PositiveIntegerField(default=365)), ("inclusion_criteria", models.TextField(blank=True, default="")), ("exclusion_criteria", models.TextField(blank=True, default="")),
            ("scoring_weights", models.JSONField(default=openoutreach.funding.models.default_scoring_weights)), ("analyzer_confidence", models.FloatField(blank=True, null=True)),
            ("user_reviewed_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="funding_criteria", to="core.project")),
            ("source_analysis_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="funding_criteria", to="signals.organizationanalysisrun")),
        ]),
        migrations.CreateModel(name="FundingOpportunity", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("identity_key", models.CharField(editable=False, max_length=64, unique=True)), ("title", models.CharField(max_length=500)), ("summary", models.TextField(blank=True, default="")),
            ("canonical_url", models.URLField(blank=True, default="", max_length=1000)), ("external_id", models.CharField(blank=True, default="", max_length=500)), ("opportunity_type", models.CharField(blank=True, default="", max_length=100)),
            ("status", models.CharField(choices=[("unknown", "Unknown"), ("upcoming", "Upcoming"), ("open", "Open"), ("closed", "Closed"), ("cancelled", "Cancelled"), ("archived", "Archived")], default="unknown", max_length=20)),
            ("published_at", models.DateTimeField(blank=True, null=True)), ("opens_at", models.DateTimeField(blank=True, null=True)), ("deadline_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ("amount_min", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)), ("amount_max", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
            ("currency", models.CharField(blank=True, default="USD", max_length=3)), ("total_funding_available", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
            ("eligible_applicant_types", models.JSONField(blank=True, default=list)), ("eligible_geographies", models.JSONField(blank=True, default=list)), ("focus_areas", models.JSONField(blank=True, default=list)),
            ("beneficiaries", models.JSONField(blank=True, default=list)), ("requirements", models.JSONField(blank=True, default=list)), ("contact_information", models.JSONField(blank=True, default=dict)), ("raw_attributes", models.JSONField(blank=True, default=dict)),
            ("first_seen_at", models.DateTimeField(auto_now_add=True)), ("last_seen_at", models.DateTimeField(auto_now=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("funder", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="opportunities", to="funding.funder")),
        ]),
        migrations.CreateModel(name="FundingOpportunitySource", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("source_external_id", models.CharField(blank=True, default="", max_length=500)), ("source_url", models.URLField(blank=True, default="", max_length=1000)),
            ("is_primary", models.BooleanField(default=False)), ("first_seen_at", models.DateTimeField(auto_now_add=True)), ("last_seen_at", models.DateTimeField(auto_now=True)),
            ("opportunity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_links", to="funding.fundingopportunity")),
            ("source_record", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="funding_opportunity_link", to="sources.sourcerecord")),
        ], options={"constraints": [models.UniqueConstraint(fields=("opportunity", "source_record"), name="unique_opportunity_source_record")]}),
        migrations.AddField(
            model_name="fundingopportunity", name="source_records",
            field=models.ManyToManyField(related_name="funding_opportunities", through="funding.FundingOpportunitySource", to="sources.sourcerecord"),
        ),
        migrations.CreateModel(name="FundingSignal", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("state", models.CharField(choices=[("discovered", "Discovered"), ("needs_review", "Needs Review"), ("shortlisted", "Shortlisted"), ("monitoring", "Monitoring"), ("planning", "Planning"), ("applying", "Applying"), ("submitted", "Submitted"), ("awarded", "Awarded"), ("declined", "Declined"), ("dismissed", "Dismissed"), ("expired", "Expired")], default="discovered", max_length=30)),
            ("score", models.FloatField(blank=True, null=True)), ("confidence", models.FloatField(blank=True, null=True)),
            ("eligibility_status", models.CharField(choices=[("unknown", "Unknown"), ("eligible", "Eligible"), ("likely_eligible", "Likely Eligible"), ("needs_review", "Needs Review"), ("ineligible", "Ineligible")], default="unknown", max_length=30)),
            ("eligibility_reasons", models.JSONField(blank=True, default=list)), ("score_breakdown", models.JSONField(blank=True, default=dict)), ("explanation", models.TextField(blank=True, default="")),
            ("priority", models.PositiveSmallIntegerField(default=0)), ("reviewed_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("opportunity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="funding_signals", to="funding.fundingopportunity")),
            ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_funding_signals", to=settings.AUTH_USER_MODEL)),
            ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="funding_signals", to="core.project")),
        ], options={"constraints": [models.UniqueConstraint(fields=("project", "opportunity"), name="unique_project_funding_signal")]}),
        migrations.CreateModel(name="FundingSignalFeedback", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("label", models.CharField(choices=[("good_fit", "Good Fit"), ("bad_fit", "Bad Fit"), ("uncertain", "Uncertain"), ("duplicate", "Duplicate"), ("ineligible", "Ineligible"), ("outdated", "Outdated")], max_length=20)),
            ("reason", models.TextField(blank=True, default="")), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("signal", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback", to="funding.fundingsignal")),
            ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="funding_signal_feedback", to=settings.AUTH_USER_MODEL)),
        ]),
    ]
