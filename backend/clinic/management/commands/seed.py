"""Seed isolated demo or development data through the clinical service layer."""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from backend.clinic.services import seed_clinical_samples


class Command(BaseCommand):
    help = "Seed sample staff, patients, triage queues, and clinical records."

    def add_arguments(self, parser) -> None:  # type: ignore[override]
        parser.add_argument(
            "--clear", action="store_true", help="Reset sample encounters; retain staff profiles."
        )
        parser.add_argument(
            "--count", type=int, default=15, help="Number of sample patients (default: 15)."
        )

    def handle(self, *args, **options) -> None:
        try:
            result = seed_clinical_samples(count=max(1, options["count"]), clear=options["clear"])
        except ValidationError as err:
            raise CommandError(str(err)) from err
        self.stdout.write(
            f"Seeded {result['patients']} patient(s), {result['appointments']} appointment(s), and {result['records']} record(s). Existing data is retained unless --clear is used."
        )
