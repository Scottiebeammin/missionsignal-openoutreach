import uuid
from django.db import migrations, models


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
        migrations.RunSQL(
            sql="UPDATE core_project SET share_token = lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6))) WHERE share_token IS NULL",
            reverse_sql="UPDATE core_project SET share_token = NULL",
        ),
        # Step 3: add unique + index constraint, remove nullability
        migrations.AlterField(
            model_name='project',
            name='share_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
    ]
