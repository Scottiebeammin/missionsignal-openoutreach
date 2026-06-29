import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.research import import_research_data


class Command(BaseCommand):
    help = "Import Hermes research output JSON into the opportunity database."

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the Hermes research JSON file")
        parser.add_argument("--project-id", type=int, default=None, help="Project ID to link opportunities to")
        parser.add_argument("--dry-run", action="store_true", help="Parse and validate without writing to the database")

    def handle(self, *args, **options):
        path = Path(options["json_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN — validating only"))
            counts = {k: len(data.get(k, [])) for k in ("funders", "partners", "government_entities", "resource_providers", "opportunities")}
            for k, n in counts.items():
                self.stdout.write(f"  {k}: {n} records found")
            return

        project = None
        if options["project_id"]:
            from openoutreach.core.models import Project
            try:
                project = Project.objects.get(pk=options["project_id"])
            except Project.DoesNotExist:
                raise CommandError(f"Project {options['project_id']} not found")

        counts = import_research_data(data, project=project)
        self.stdout.write(self.style.SUCCESS("Import complete"))
        for key, n in counts.items():
            if n:
                self.stdout.write(f"  {key}: {n}")
