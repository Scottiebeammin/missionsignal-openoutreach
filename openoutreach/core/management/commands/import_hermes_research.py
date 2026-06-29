import json
import sys
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from openoutreach.funding.models import (
    Funder,
    GovernmentEntity,
    Opportunity,
    PartnerOrganization,
    ResourceProvider,
)


class Command(BaseCommand):
    help = "Import Hermes research output JSON into the opportunity database."

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the Hermes research JSON file")
        parser.add_argument(
            "--project-id",
            type=int,
            default=None,
            help="Project ID to link opportunities to (optional)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without writing to the database",
        )

    def handle(self, *args, **options):
        path = Path(options["json_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        dry_run = options["dry_run"]
        project_id = options["project_id"]
        project = None

        if project_id:
            from openoutreach.core.models import Project
            try:
                project = Project.objects.get(pk=project_id)
            except Project.DoesNotExist:
                raise CommandError(f"Project {project_id} not found")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written"))

        counts = {"funders": 0, "partners": 0, "government": 0, "resources": 0, "opportunities": 0}

        # ── Funders ──────────────────────────────────────────────────────────
        for item in data.get("funders", []):
            name = item.get("name", "").strip()
            if not name:
                continue
            if not dry_run:
                obj, created = Funder.objects.update_or_create(
                    name=name,
                    defaults={
                        "funder_type": _coerce(item.get("funder_type", ""), Funder.FunderType, Funder.FunderType.OTHER),
                        "geography": item.get("geography", []),
                        "focus_areas": item.get("focus_areas", []),
                        "beneficiaries": item.get("beneficiaries", []),
                        "eligibility_notes": item.get("eligibility_notes", ""),
                        "website": item.get("website", ""),
                        "notes": item.get("notes", ""),
                        "source_urls": item.get("source_urls", []),
                        "source_references": item.get("source_references", []),
                        "source_notes": item.get("source_notes", ""),
                        "verification_status": _coerce(
                            item.get("verification_status", ""),
                            Funder.VerificationStatus,
                            Funder.VerificationStatus.UNVERIFIED,
                        ),
                        "intelligence_status": Funder.IntelligenceStatus.ACTIVE,
                        "active": True,
                    },
                )
                action = "created" if created else "updated"
            else:
                action = "would create/update"
            counts["funders"] += 1
            self.stdout.write(f"  Funder {action}: {name}")

        # ── Partners ─────────────────────────────────────────────────────────
        for item in data.get("partners", []):
            name = item.get("name", "").strip()
            if not name:
                continue
            if not dry_run:
                obj, created = PartnerOrganization.objects.update_or_create(
                    name=name,
                    defaults={
                        "partner_type": _coerce(item.get("partner_type", ""), PartnerOrganization.PartnerType, PartnerOrganization.PartnerType.OTHER),
                        "geography": item.get("geography", []),
                        "focus_areas": item.get("focus_areas", []),
                        "beneficiaries": item.get("beneficiaries", []),
                        "collaboration_opportunities": item.get("collaboration_opportunities", []),
                        "website": item.get("website", ""),
                        "notes": item.get("notes", ""),
                        "mission_alignment_notes": item.get("mission_alignment_notes", ""),
                        "opportunity_notes": item.get("opportunity_notes", ""),
                        "source_urls": item.get("source_urls", []),
                        "source_references": item.get("source_references", []),
                        "verification_status": _coerce(
                            item.get("verification_status", ""),
                            PartnerOrganization.VerificationStatus,
                            PartnerOrganization.VerificationStatus.UNVERIFIED,
                        ),
                        "intelligence_status": PartnerOrganization.IntelligenceStatus.ACTIVE,
                        "active": True,
                    },
                )
                action = "created" if created else "updated"
            else:
                action = "would create/update"
            counts["partners"] += 1
            self.stdout.write(f"  Partner {action}: {name}")

        # ── Government entities ───────────────────────────────────────────────
        for item in data.get("government_entities", []):
            name = item.get("name", "").strip()
            if not name:
                continue
            if not dry_run:
                obj, created = GovernmentEntity.objects.update_or_create(
                    name=name,
                    defaults={
                        "entity_type": _coerce(item.get("entity_type", ""), GovernmentEntity.EntityType, GovernmentEntity.EntityType.OTHER),
                        "geography": item.get("geography", []),
                        "focus_areas": item.get("focus_areas", []),
                        "department_or_office": item.get("department_or_office", ""),
                        "opportunity_lanes": item.get("opportunity_lanes", []),
                        "website": item.get("website", ""),
                        "notes": item.get("notes", ""),
                        "active": True,
                    },
                )
                action = "created" if created else "updated"
            else:
                action = "would create/update"
            counts["government"] += 1
            self.stdout.write(f"  Government {action}: {name}")

        # ── Resource providers ────────────────────────────────────────────────
        for item in data.get("resource_providers", []):
            name = item.get("name", "").strip()
            if not name:
                continue
            if not dry_run:
                obj, created = ResourceProvider.objects.update_or_create(
                    name=name,
                    defaults={
                        "resource_type": _coerce(item.get("resource_type", ""), ResourceProvider.ResourceType, ResourceProvider.ResourceType.OTHER),
                        "geography": item.get("geography", []),
                        "focus_areas": item.get("focus_areas", []),
                        "resource_categories": item.get("resource_categories", []),
                        "eligibility_notes": item.get("eligibility_notes", ""),
                        "website": item.get("website", ""),
                        "notes": item.get("notes", ""),
                        "active": True,
                    },
                )
                action = "created" if created else "updated"
            else:
                action = "would create/update"
            counts["resources"] += 1
            self.stdout.write(f"  Resource {action}: {name}")

        # ── Opportunities ─────────────────────────────────────────────────────
        for item in data.get("opportunities", []):
            name = item.get("name", "").strip()
            if not name:
                continue

            deadline = None
            if item.get("deadline"):
                try:
                    deadline = date.fromisoformat(item["deadline"])
                except ValueError:
                    self.stdout.write(self.style.WARNING(f"  Bad deadline for '{name}': {item['deadline']} — skipping deadline"))

            posted_date = None
            if item.get("posted_date"):
                try:
                    posted_date = date.fromisoformat(item["posted_date"])
                except ValueError:
                    pass

            if not dry_run:
                lookup = {"name": name}
                if project:
                    lookup["project"] = project
                obj, created = Opportunity.objects.update_or_create(
                    **lookup,
                    defaults={
                        "opportunity_type": _coerce(item.get("opportunity_type", ""), Opportunity.OpportunityType, Opportunity.OpportunityType.GRANT),
                        "source_type": _coerce(item.get("source_type", ""), Opportunity.SourceType, Opportunity.SourceType.MANUAL),
                        "source_name": item.get("source_name", ""),
                        "geography": item.get("geography", []),
                        "focus_areas": item.get("focus_areas", []),
                        "beneficiaries": item.get("beneficiaries", []),
                        "eligibility_notes": item.get("eligibility_notes", ""),
                        "funding_amount": item.get("funding_amount") or None,
                        "deadline": deadline,
                        "posted_date": posted_date,
                        "priority_level": _coerce(item.get("priority_level", ""), Opportunity.PriorityLevel, Opportunity.PriorityLevel.MEDIUM),
                        "status": _coerce(item.get("status", ""), Opportunity.Status, Opportunity.Status.ACTIVE),
                        "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
                        "notes": item.get("notes", ""),
                        "source_urls": item.get("source_urls", []),
                        "source_references": item.get("source_references", []),
                        "source_notes": item.get("source_notes", ""),
                        "verification_status": _coerce(
                            item.get("verification_status", ""),
                            Opportunity.VerificationStatus,
                            Opportunity.VerificationStatus.UNVERIFIED,
                        ),
                    },
                )
                action = "created" if created else "updated"
            else:
                action = "would create/update"
            counts["opportunities"] += 1
            self.stdout.write(f"  Opportunity {action}: {name}")

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import complete" if not dry_run else "Dry run complete"))
        for key, n in counts.items():
            if n:
                self.stdout.write(f"  {key}: {n}")


def _coerce(value, choices_class, default):
    if not value:
        return default
    normalized = str(value).lower().replace("-", "_").replace(" ", "_")
    for choice in choices_class:
        if choice.value.lower() == normalized or choice.name.lower() == normalized:
            return choice
    return default
