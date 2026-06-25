from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_organization_budget_range_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(
                    choices=[
                        ("owner", "Owner"),
                        ("executive_director", "Executive Director"),
                        ("development_lead", "Development Lead"),
                        ("staff", "Staff"),
                    ],
                    default="staff",
                    max_length=30,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="members",
                    to="core.project",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="organization_memberships",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=("user", "project"), name="unique_user_project_member"),
            ]},
        ),
    ]
