from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_organization_budget_range_and_more"),
        ("funding", "0010_funder_last_reviewed_at_funder_source_notes_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="opportunities",
                to="core.project",
            ),
        ),
    ]
