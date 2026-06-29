import uuid
from django.db import migrations


def regenerate_tokens(apps, schema_editor):
    Project = apps.get_model("core", "Project")
    for project in Project.objects.all():
        project.share_token = uuid.uuid4()
        project.save(update_fields=["share_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_add_project_share_token"),
    ]

    operations = [
        migrations.RunPython(regenerate_tokens, migrations.RunPython.noop),
    ]
