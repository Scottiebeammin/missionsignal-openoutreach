from django.db import migrations


def set_site_domain(apps, schema_editor):
    """Point Site #1 at the real domain so sitemap.xml builds correct absolute URLs."""
    Site = apps.get_model("sites", "Site")
    Site.objects.update_or_create(
        id=1,
        defaults={"domain": "anansiatlas.com", "name": "Anansi Atlas"},
    )


def reverse_site_domain(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.filter(id=1).update(domain="example.com", name="example.com")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_regenerate_project_share_tokens"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(set_site_domain, reverse_site_domain),
    ]
