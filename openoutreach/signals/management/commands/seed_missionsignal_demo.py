from django.core.management.base import BaseCommand
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo


class Command(BaseCommand):
    help = "Create or refresh demo-ready MissionSignal data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Set a login password for the missionsignal-demo user.",
        )

    def handle(self, *args, **options):
        user, organization, project = seed_missionsignal_demo(
            password=options["password"],
        )
        analysis_url = reverse("project-analysis-detail", kwargs={"pk": project.pk})
        brief_url = reverse("project-mission-brief", kwargs={"pk": project.pk})

        self.stdout.write(self.style.SUCCESS("MissionSignal demo data is ready."))
        self.stdout.write(f"Demo user: {user.username} (ID: {user.pk})")
        self.stdout.write(f"Organization ID: {organization.pk}")
        self.stdout.write(f"Project ID: {project.pk}")
        self.stdout.write(f"Analysis review: {analysis_url}")
        self.stdout.write(f"Mission Brief: {brief_url}")
        if not options["password"]:
            self.stdout.write(
                self.style.WARNING(
                    "No password was set. Rerun with --password to enable demo login."
                )
            )
