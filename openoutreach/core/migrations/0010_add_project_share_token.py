import uuid
from django.db import migrations, models


def populate_share_tokens(apps, schema_editor):
    """Give each existing row a unique token (DB-agnostic; works on Postgres + SQLite)."""
    Project = apps.get_model("core", "Project")
    for project in Project.objects.filter(share_token__isnull=True):
        project.share_token = uuid.uuid4()
        project.save(update_fields=["share_token"])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_intake_contact_fields'),
    ]

    operations = [
        # Step 1: add nullable (avoids unique collision on existing rows)
        migrations.AddField(
            model_name='project',
            name='share_token',
            field=models.UUIDField(null=True, blank=True),
        ),
        # Step 2: populate each existing row with a unique token
        migrations.RunPython(populate_share_tokens, migrations.RunPython.noop),
        # Step 3: add unique + index constraint, remove nullability
        migrations.AlterField(
            model_name='project',
            name='share_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
    ]
