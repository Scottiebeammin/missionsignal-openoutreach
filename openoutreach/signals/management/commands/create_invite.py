"""
Generate a signed invite URL for a project.

    python manage.py create_invite --project-id 14

Prints a link (valid 14 days) the founder can email to the client. Whoever
opens it chooses their own email + password and is attached to the project.
"""

from django.core.management.base import BaseCommand, CommandError

from openoutreach.core.models import Project
from openoutreach.signals.invites import INVITE_MAX_AGE_DAYS, make_invite_token


class Command(BaseCommand):
    help = "Print a signed invite URL that lets a client create their own account on a project."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, required=True)
        parser.add_argument("--base-url", default="https://anansiatlas.com")

    def handle(self, *args, **options):
        try:
            project = Project.objects.select_related("organization").get(pk=options["project_id"])
        except Project.DoesNotExist:
            raise CommandError(f"No project with id {options['project_id']}")
        token = make_invite_token(project.pk)
        url = f"{options['base_url'].rstrip('/')}/invite/{token}/"
        self.stdout.write(self.style.SUCCESS(
            f"Invite for {project.organization.name} (valid {INVITE_MAX_AGE_DAYS} days):\n{url}"
        ))
