from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("crm", "0007_drop_legacy_lead_fields"),
    ]

    operations = [
        # VACUUM is a SQLite disk-reclamation step; no-op on Postgres (and would
        # error inside a managed transaction). Kept as a placeholder for history.
        migrations.RunSQL(migrations.RunSQL.noop, reverse_sql=migrations.RunSQL.noop),
    ]
