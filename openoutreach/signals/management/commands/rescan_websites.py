"""
Monthly website re-verification for every active client project.

Re-runs the profile-vs-website check and, when NEW claims have gone missing
since the last check (drift), emails the project owner a nudge. Only new drift
triggers mail — steady-state mismatches the client already knows about don't
re-nag them every month.

    python manage.py rescan_websites            # all projects, email on new drift
    python manage.py rescan_websites --no-email # rescan only (e.g. a manual sweep)
    python manage.py rescan_websites --project-id N
"""
from django.core.management.base import BaseCommand

from openoutreach.core.models import OrganizationMember, Project
from openoutreach.signals.notifications import send_website_drift_nudge
from openoutreach.signals.website_verification import verify_website_claims


def _missing_keys(report) -> set:
    return {(m["kind"], m["claim"]) for m in (report or {}).get("missing", [])}


class Command(BaseCommand):
    help = "Re-verify client websites against their profiles; email owners on new drift."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, default=None)
        parser.add_argument("--no-email", action="store_true", help="Rescan without sending nudges.")

    def handle(self, *args, **options):
        projects = Project.objects.select_related("organization")
        if options["project_id"]:
            projects = projects.filter(pk=options["project_id"])

        scanned = nudged = 0
        for project in projects:
            organization = project.organization
            if not organization.website:
                continue
            before = _missing_keys(organization.website_check)
            report = verify_website_claims(organization, project)
            scanned += 1
            if report.get("status") != "ok":
                continue
            after = _missing_keys(report)
            new_drift = after - before
            if not new_drift or options["no_email"]:
                continue
            missing_items = [m for m in report["missing"] if (m["kind"], m["claim"]) in new_drift]
            owner = (
                OrganizationMember.objects.filter(project=project, is_admin=True)
                .select_related("user").first()
                or OrganizationMember.objects.filter(project=project).select_related("user").first()
            )
            if owner and owner.user.email and send_website_drift_nudge(owner.user, project, missing_items):
                nudged += 1

        self.stdout.write(self.style.SUCCESS(
            f"Rescanned {scanned} website(s); sent {nudged} drift nudge(s)."
        ))
