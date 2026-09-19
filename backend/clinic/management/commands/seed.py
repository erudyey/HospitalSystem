"""Management command to seed the database with multi-role clinical sample data.

Usage:
    python backend/manage.py seed              # add sample data (skips if data exists)
    python backend/manage.py seed --clear      # wipe all staff/patients/appointments/records first
    python backend/manage.py seed --count 15   # seed 15 patients (default: 15)
"""

import random
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand

from backend.clinic.models import (
    Appointment,
    AppointmentStatus,
    MedicalRecord,
    Patient,
    StaffRole,
    StaffUser,
)
from backend.clinic.services import (
    DEFAULT_STAFF_ACCOUNTS,
    book_appointment,
    create_medical_record,
    ensure_default_staff,
    register_patient,
    update_appointment_status,
)

STAFF_FIXTURES = DEFAULT_STAFF_ACCOUNTS

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

REASONS = [
    "Routine physical and wellness checkup",
    "Persistent productive cough and low-grade fever",
    "Hypertension maintenance review",
    "Follow-up for seasonal allergic rhinitis",
    "Pediatric immunization and growth review",
    "Mild epigastric discomfort after meals",
    "Headache and eye strain during screen use",
    "Prescription renewal for antidiabetic therapy",
]

CLINICAL_CASES = [
    {
        "diagnosis": "Acute Upper Respiratory Tract Infection (URTI)",
        "symptoms": "3-day history of rhinorrhea, mild sore throat, non-productive cough, afebrile.",
        "clinical_notes": "BP: 118/76 mmHg, HR: 76 bpm, Temp: 36.8C. Pharyngeal erythema present, tonsils not enlarged. Lungs clear to auscultation.",
        "prescription": "Paracetamol 500mg tab, 1 tab Q6H PRN fever/headache\nCetirizine 10mg tab, 1 tab OD at bedtime x 5 days\nSaline nasal spray, 2 sprays per nostril TID",
        "follow_up_advice": "Rest, oral rehydration (2L water/day). Return in 5 days if cough worsens or fever spikes.",
    },
    {
        "diagnosis": "Essential (Primary) Hypertension, Stage 1",
        "symptoms": "Occasional morning occipital headache, no chest pain or shortness of breath.",
        "clinical_notes": "BP: 142/90 mmHg (repeat: 140/88 mmHg), HR: 80 bpm regular. S1/S2 normal, no murmurs. Peripheral pulses intact.",
        "prescription": "Amlodipine 5mg tab, 1 tab OD every morning\nHome BP monitoring log daily",
        "follow_up_advice": "Low-salt diet (<2g sodium/day), 30 minutes brisk walking daily. Return in 2 weeks with BP log.",
    },
    {
        "diagnosis": "Acute Viral Gastroenteritis",
        "symptoms": "Watery diarrhea 4x in past 24 hours, mild nausea, no hematochezia.",
        "clinical_notes": "BP: 110/70 mmHg, HR: 84 bpm, Temp: 37.2C. Abdomen soft, hyperactive bowel sounds, mild diffuse tenderness without guarding.",
        "prescription": "Oral Rehydration Salts (ORS), 1 sachet in 1L water, drink freely\nZinc sulfate 20mg tab, 1 tab OD x 10 days\nParacetamol 500mg tab, 1 tab PRN",
        "follow_up_advice": "Bland diet (BRAT). Avoid dairy, caffeine, and fatty food. Return immediately if signs of dehydration appear.",
    },
    {
        "diagnosis": "Allergic Contact Dermatitis",
        "symptoms": "Pruritic erythematous papules and patches on bilateral forearms following garden exposure.",
        "clinical_notes": "Well-demarcated erythematous plaques with scattered microvesicles. No signs of secondary bacterial infection.",
        "prescription": "Hydrocortisone 1% cream, apply thinly BID x 7 days\nLoratadine 10mg tab, 1 tab OD in morning x 7 days",
        "follow_up_advice": "Avoid scratching, keep skin moisturized with hypoallergenic lotion. Wear protective gloves during yard work.",
    },
]

CONTACTS = [
    "09171234567",
    "09281234567",
    "09391234567",
    "09501234567",
    "09611234567",
    "09721234567",
    "(02) 8123-4567",
    "(032) 412-3456",
    "",
]

TODAY = date.today()
SAMPLE_TIMES = [
    time(9, 0),
    time(9, 30),
    time(10, 0),
    time(10, 30),
    time(11, 0),
    time(14, 0),
    time(14, 30),
    time(15, 0),
]


class Command(BaseCommand):
    help = "Seed the database with multi-role staff, realistic patients, triage queues, and SOAP notes."

    def add_arguments(self, parser) -> None:  # type: ignore[override]
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing records before seeding.",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=15,
            help="Number of patients to create (default: 15).",
        )

    def handle(self, *args, **options) -> None:
        rng = random.Random(42)  # deterministic seed

        if options["clear"]:
            MedicalRecord.objects.all().delete()
            Appointment.objects.all().delete()
            Patient.objects.all().delete()
            StaffUser.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    "Cleared all staff, patients, appointments, and medical records."
                )
            )

        # 1. Ensure baseline staff accounts exist regardless of existing patients
        staff_users = ensure_default_staff()
        doctors = [s for s in staff_users if s.role == StaffRole.DOCTOR]
        self.stdout.write(
            self.style.SUCCESS(
                f"Verified/seeded {len(staff_users)} staff accounts (1 receptionist, {len(doctors)} doctors)."
            )
        )

        existing_patients = Patient.objects.count()
        if existing_patients > 0 and not options["clear"]:
            self.stdout.write(
                self.style.NOTICE(
                    f"Database already contains {existing_patients} patient(s). "
                    "Use --clear to wipe and re-seed, or --count to add more."
                )
            )
            return

        # 2. Seed Patients
        count = max(1, options["count"])
        first_names = rng.sample(FIRST_NAMES, min(count, len(FIRST_NAMES)))
        last_names = rng.choices(LAST_NAMES, k=count)

        patients: list[Patient] = []
        for i in range(count):
            first = first_names[i] if i < len(first_names) else rng.choice(FIRST_NAMES)
            last = last_names[i]
            patient = register_patient(
                full_name=f"{first} {last}",
                contact=rng.choice(CONTACTS),
                age=rng.randint(6, 82),
            )
            patients.append(patient)

        # 3. Seed Appointments spanning all 5 states
        appointments_created = 0
        records_created = 0

        # State Distribution for realism:
        # - 3 Checked In (Waiting Room today)
        # - 1 In Consultation (today)
        # - 4 Scheduled (today and tomorrow)
        # - 6 Completed (in the past, with SOAP records)
        # - 2 Cancelled
        for idx, patient in enumerate(patients):
            doc = rng.choice(doctors)
            slot_time = rng.choice(SAMPLE_TIMES)
            reason = rng.choice(REASONS)

            if idx in (0, 1, 2):
                # Live Waiting Room (Checked In today)
                appt = book_appointment(
                    patient_id=patient.id,
                    doctor_name=doc.full_name,
                    doctor_id=doc.id,
                    app_date_str=TODAY.isoformat(),
                    app_time_str=slot_time.strftime("%H:%M"),
                    reason_for_visit=reason,
                    initial_status=AppointmentStatus.CHECKED_IN,
                )
                appointments_created += 1

            elif idx == 3:
                # In Consultation today
                appt = book_appointment(
                    patient_id=patient.id,
                    doctor_name=doc.full_name,
                    doctor_id=doc.id,
                    app_date_str=TODAY.isoformat(),
                    app_time_str=time(9, 30).strftime("%H:%M"),
                    reason_for_visit=reason,
                    initial_status=AppointmentStatus.CHECKED_IN,
                )
                update_appointment_status(appt.id, AppointmentStatus.IN_CONSULTATION)
                appointments_created += 1

            elif idx in (4, 5, 6, 7):
                # Scheduled (today or future)
                offset = rng.randint(0, 5)
                appt = book_appointment(
                    patient_id=patient.id,
                    doctor_name=doc.full_name,
                    doctor_id=doc.id,
                    app_date_str=(TODAY + timedelta(days=offset)).isoformat(),
                    app_time_str=slot_time.strftime("%H:%M"),
                    reason_for_visit=reason,
                    initial_status=AppointmentStatus.SCHEDULED,
                )
                appointments_created += 1

            elif idx in (8, 9, 10, 11, 12, 13):
                # Completed past appointments with signed SOAP medical records
                past_date = TODAY - timedelta(days=rng.randint(2, 60))
                appt = book_appointment(
                    patient_id=patient.id,
                    doctor_name=doc.full_name,
                    doctor_id=doc.id,
                    app_date_str=past_date.isoformat(),
                    app_time_str=slot_time.strftime("%H:%M"),
                    reason_for_visit=reason,
                    initial_status=AppointmentStatus.SCHEDULED,
                )
                appointments_created += 1

                # Create linked SOAP record
                case = rng.choice(CLINICAL_CASES)
                create_medical_record(
                    patient_id=patient.id,
                    doctor_id=doc.id,
                    diagnosis=case["diagnosis"],
                    symptoms=case["symptoms"],
                    clinical_notes=case["clinical_notes"],
                    prescription=case["prescription"],
                    follow_up_advice=case["follow_up_advice"],
                    appointment_id=appt.id,
                )
                records_created += 1

            else:
                # Cancelled appointment
                past_date = TODAY - timedelta(days=rng.randint(1, 14))
                appt = book_appointment(
                    patient_id=patient.id,
                    doctor_name=doc.full_name,
                    doctor_id=doc.id,
                    app_date_str=past_date.isoformat(),
                    app_time_str=slot_time.strftime("%H:%M"),
                    reason_for_visit=reason,
                    initial_status=AppointmentStatus.SCHEDULED,
                )
                update_appointment_status(appt.id, AppointmentStatus.CANCELLED)
                appointments_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(patients)} patients, {appointments_created} appointments "
                f"(3 Checked In, 1 In Consultation, 4 Scheduled, 6 Completed, 1+ Cancelled), "
                f"and {records_created} signed SOAP medical records."
            )
        )
