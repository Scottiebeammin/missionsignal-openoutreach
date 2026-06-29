from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("linkedin", "0003_siteconfig"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
