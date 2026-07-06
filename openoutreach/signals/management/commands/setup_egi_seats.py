"""
Set up Empowered Girls Inc.'s two founding seats (ED = admin, program lead =
member) and print the ready-to-send invite link.

The first person to open the invite becomes the account admin; the second
becomes the teammate seat. Any users already on the project are added to the
Founding Partners group so the founding-partner welcome shows on their
dashboard. Idempotent.

    python manage.py setup_egi_seats
    python manage.py setup_egi_seats --organization-id N   # if the name is ambiguous
"""
from django.core.management.base import BaseCommand, CommandError

from openoutreach.core.access import founding_partners_group
from openoutreach.core.models import Organization, Project
from openoutreach.signals.invites import INVITE_MAX_AGE_DAYS, make_invite_token


class Command(BaseCommand):
    help = "Set up EGI's 2 founding seats and print the invite link (ED admin + program lead)."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", type=int, default=None)
        parser.add_argument("--base-url", default="https://anansiatlas.com")

    def handle(self, *args, **options):
        if options["organization_id"] is not None:
            org = Organization.objects.filter(pk=options["organization_id"]).first()
        else:
            matches = list(Organization.objects.filter(name__icontains="Empowered Girls")[:2])
            if len(matches) > 1:
                raise CommandError("Multiple 'Empowered Girls' orgs — pass --organization-id.")
            org = matches[0] if matches else None
        if org is None:
            raise CommandError("No Empowered Girls organization found. Run seed_egi first.")

        project = Project.objects.filter(organization=org).first()
        if project is None:
            raise CommandError(f"No project for {org.name}. Run seed_egi first.")

        # Anyone already on the project is a founding partner → show the welcome.
        group = founding_partners_group()
        promoted = 0
        for user in project.users.all():
            if not user.groups.filter(pk=group.pk).exists():
                user.groups.add(group)
                promoted += 1

        token = make_invite_token(project.pk)
        url = f"{options['base_url'].rstrip('/')}/invite/{token}/"

        self.stdout.write(self.style.SUCCESS(f"Empowered Girls Inc. — 2 founding seats"))
        self.stdout.write(
            f"  Existing seats: {project.users.count()} ({promoted} added to Founding Partners)\n"
            f"\n  Invite link (valid {INVITE_MAX_AGE_DAYS} days) — send to BOTH:\n  {url}\n"
            f"\n  • Seat 1 — the Executive Director opens it FIRST → becomes the account admin.\n"
            f"  • Seat 2 — the program lead opens it next → becomes the teammate seat.\n"
            f"  (Or if the ED already bought the founding seat via Stripe, they're the admin — "
            f"just send this link to the program lead for seat 2.)"
        )
