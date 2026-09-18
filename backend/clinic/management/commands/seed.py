"""Management command to seed the database with realistic sample data.

Usage:
    python backend/manage.py seed              # add sample data (skips if data exists)
    python backend/manage.py seed --clear      # wipe all patients/appointments first
    python backend/manage.py seed --count 20   # seed 20 patients (default: 15)
"""

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from backend.clinic.models import Appointment, AppointmentStatus, Patient
from backend.clinic.services import book_appointment, register_patient

FIRST_NAMES = [
    "Maria",
    "Jose",
    "Juan",
    "Ana",
    "Carlos",
    "Rosa",
    "Miguel",
    "Elena",
    "Luis",
    "Sofia",
    "Pedro",
    "Isabel",
    "Antonio",
    "Carmen",
    "Fernando",
    "Laura",
    "Ricardo",
    "Patricia",
    "Eduardo",
    "Gabriela",
]

LAST_NAMES = [
    "Santos",
    "Reyes",
    "Cruz",
    "Flores",
    "Garcia",
    "Torres",
    "Rivera",
    "Mendoza",
    "Ramos",
    "Dela Cruz",
    "Villanueva",
    "Gonzalez",
    "Aquino",
    "Bautista",
    "Castillo",
    "Morales",
    "Espinoza",
    "Navarro",
    "Herrera",
    "Soriano",
]

DOCTORS = [
    "Dr. Ana Reyes",
    "Dr. Marco Santos",
    "Dr. Lisa Tan",
    "Dr. James Navarro",
    "Dr. Grace Villanueva",
    "Dr. Robert Cruz",
]

CONTACTS = [
    "09171234567",
    "09281234567",
    "09391234567",
    "09501234567",
    "09611234567",
    "09721234567",
    "09831234567",
    "(02) 8123-4567",
    "(032) 412-3456",
    "",  # some patients have no contact on file
]

TODAY = date.today()


def _random_date(days_back: int, days_forward: int) -> date:
    offset = random.randint(-days_back, days_forward)
    return TODAY + timedelta(days=offset)


def _random_status(app_date: date) -> str:
    """Derive a plausible status based on how far the appointment is from today."""
    if app_date < TODAY - timedelta(days=3):
        # Past appointments are mostly completed, occasionally cancelled
        return random.choices(
            [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED],
            weights=[75, 25],
        )[0]
    if app_date > TODAY + timedelta(days=1):
        # Future appointments are scheduled, occasionally cancelled
        return random.choices(
            [AppointmentStatus.SCHEDULED, AppointmentStatus.CANCELLED],
            weights=[85, 15],
        )[0]
    # Appointments around today stay scheduled
    return AppointmentStatus.SCHEDULED


class Command(BaseCommand):
    help = "Seed the database with realistic sample patients and appointments."

    def add_arguments(self, parser) -> None:  # type: ignore[override]
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing patients and appointments before seeding.",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=15,
            help="Number of patients to create (default: 15).",
        )

    def handle(self, *args, **options) -> None:
        rng = random.Random(42)  # deterministic so re-runs produce the same names

        if options["clear"]:
            deleted_appts, _ = Appointment.objects.all().delete()
            deleted_patients, _ = Patient.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {deleted_patients} patient(s) and {deleted_appts} appointment(s)."
                )
            )

        existing = Patient.objects.count()
        if existing > 0 and not options["clear"]:
            self.stdout.write(
                self.style.NOTICE(
                    f"Database already has {existing} patient(s). "
                    "Use --clear to wipe and re-seed, or --count to add more."
                )
            )
            return

        count = max(1, options["count"])
        first_names = rng.sample(FIRST_NAMES, min(count, len(FIRST_NAMES)))
        last_names = rng.choices(LAST_NAMES, k=count)

        patients_created = 0
        appointments_created = 0

        for i in range(count):
            first = first_names[i] if i < len(first_names) else rng.choice(FIRST_NAMES)
            last = last_names[i]
            full_name = f"{first} {last}"
            contact = rng.choice(CONTACTS)
            age = rng.randint(5, 85)

            patient = register_patient(full_name=full_name, contact=contact, age=age)
            patients_created += 1

            # Give each patient 1-4 appointments spread around today
            num_appts = rng.randint(1, 4)
            for _ in range(num_appts):
                doctor = rng.choice(DOCTORS)
                app_date = _random_date(days_back=180, days_forward=60)
                status = _random_status(app_date)

                appt = book_appointment(
                    patient_id=patient.id,
                    doctor_name=doctor,
                    app_date_str=app_date.isoformat(),
                )

                # book_appointment always sets Scheduled; patch status directly if needed
                if status != AppointmentStatus.SCHEDULED:
                    appt.status = status
                    appt.save(update_fields=["status"])

                appointments_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {patients_created} patient(s) and {appointments_created} appointment(s) "
                f"into the database."
            )
        )
