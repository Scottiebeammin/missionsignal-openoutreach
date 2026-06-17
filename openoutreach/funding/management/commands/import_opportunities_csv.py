import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from openoutreach.funding.models import Opportunity, SourceOrganization


REQUIRED_COLUMNS = {"name", "opportunity_type", "geography", "status"}


def _choice_value(value: str, choices, column: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        raise CommandError(f"Missing required value for {column}.")
    normalized = clean.casefold().replace(" ", "_").replace("-", "_")
    for choice_value, label in choices:
        if normalized == choice_value or clean.casefold() == label.casefold():
            return choice_value
    allowed = ", ".join(label for _choice_value, label in choices)
    raise CommandError(f"Unsupported {column} '{clean}'. Expected one of: {allowed}.")


def _optional_choice_value(value: str, choices, default: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        return default
    return _choice_value(clean, choices, "priority")


def _list_value(value: str) -> list[str]:
    return [
        item.strip()
        for item in str(value or "").replace("|", ";").split(";")
        if item.strip()
    ]


def _date_value(value: str):
    clean = str(value or "").strip()
    if not clean:
        return None
    for date_format in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(clean, date_format).date()
        except ValueError:
            continue
    raise CommandError(f"Unsupported deadline '{clean}'. Use YYYY-MM-DD or MM/DD/YYYY.")


class Command(BaseCommand):
    help = "Import manually managed Discovery Engine opportunities from CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to a CSV file of opportunities.")

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        with open(csv_path, newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = {str(field or "").strip().casefold() for field in reader.fieldnames or []}
            missing = sorted(REQUIRED_COLUMNS - fieldnames)
            if missing:
                raise CommandError(f"Missing required columns: {', '.join(missing)}")

            created = 0
            updated = 0
            for row in reader:
                normalized = {
                    str(key or "").strip().casefold(): value
                    for key, value in row.items()
                }
                source_name = str(normalized.get("source organization", "") or "").strip()
                source_organization = None
                if source_name:
                    source_organization, _ = SourceOrganization.objects.update_or_create(
                        name=source_name,
                        defaults={
                            "organization_type": SourceOrganization.OrganizationType.OTHER,
                            "geography": _list_value(normalized.get("geography", "")),
                        },
                    )

                opportunity_type = _choice_value(
                    normalized.get("opportunity_type", ""),
                    Opportunity.OpportunityType.choices,
                    "opportunity_type",
                )
                status = _choice_value(normalized.get("status", ""), Opportunity.Status.choices, "status")
                priority = _optional_choice_value(
                    normalized.get("priority", ""),
                    Opportunity.PriorityLevel.choices,
                    Opportunity.PriorityLevel.MEDIUM,
                )
                opportunity, was_created = Opportunity.objects.update_or_create(
                    name=str(normalized.get("name", "")).strip(),
                    defaults={
                        "opportunity_type": opportunity_type,
                        "source_organization": source_organization,
                        "source_name": source_name,
                        "source_type": Opportunity.SourceType.MANUAL,
                        "geography": _list_value(normalized.get("geography", "")),
                        "focus_areas": _list_value(normalized.get("focus areas", "")),
                        "beneficiaries": _list_value(normalized.get("beneficiaries", "")),
                        "status": status,
                        "deadline": _date_value(normalized.get("deadline", "")),
                        "priority_level": priority,
                        "notes": str(normalized.get("notes", "") or "").strip(),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported opportunities from {csv_path}: {created} created, {updated} updated.",
            )
        )
