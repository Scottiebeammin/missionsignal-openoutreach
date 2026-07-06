"""
Send the "who we are & walkthrough" email (the WhoWeAre explainer video) to a
client's members. Companion to the auto-sent seat-welcome, which carries the
join links + the Dashboard Walkthrough video.

    python manage.py send_who_we_are --project-id 14           # all members
    python manage.py send_who_we_are --project-id 14 --dry-run
    python manage.py send_who_we_are --project-id 14 --to ed@empoweredgirlsinc.org
"""
from django.core.management.base import BaseCommand, CommandError

from openoutreach.core.models import Project
from openoutreach.signals.notifications import send_who_we_are_email


class Command(BaseCommand):
    help = "Send the who-we-are & walkthrough email (FBvLg9c35Qo) to a project's members."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, required=True)
        parser.add_argument("--to", default="", help="Send to just this email (must be a project member).")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        project = Project.objects.filter(pk=options["project_id"]).select_related("organization").first()
        if project is None:
            raise CommandError(f"No project with id {options['project_id']}")
        users = [u for u in project.users.all() if u.email]
        if options["to"]:
            users = [u for u in users if u.email.lower() == options["to"].lower()]
            if not users:
                raise CommandError(f"{options['to']} is not a member of this project.")
        if options["dry_run"]:
            self.stdout.write(f"[dry-run] would send who-we-are to: {', '.join(u.email for u in users)}")
            return
        sent = sum(1 for u in users if send_who_we_are_email(u, project))
        self.stdout.write(self.style.SUCCESS(
            f"Sent who-we-are & walkthrough to {sent}/{len(users)} member(s) of {project.organization.name}."
        ))
