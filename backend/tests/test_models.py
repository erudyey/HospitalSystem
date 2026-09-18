"""Unit tests for clinic ORM models: StaffUser, UserSession, Patient, Appointment, MedicalRecord."""

from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from backend.clinic.models import (
    Appointment,
    AppointmentStatus,
    MedicalRecord,
    Patient,
    StaffRole,
    StaffUser,
    UserSession,
)


class StaffUserModelTests(TestCase):
    """Tests for StaffUser credentials, hashing, and field validation."""

    def test_create_receptionist_with_password(self) -> None:
        staff = StaffUser(
            username="maria.santos",
            full_name="Maria Santos",
            role=StaffRole.RECEPTIONIST,
            contact="09171234567",
        )
        staff.set_password("clinic123")
        staff.save()

        self.assertIsNotNone(staff.id)
        self.assertTrue(staff.check_password("clinic123"))
        self.assertFalse(staff.check_password("wrongpassword"))
        self.assertNotEqual(staff.password_hash, "clinic123")
        self.assertIn("pbkdf2", staff.password_hash)

    def test_create_doctor_with_specialty_and_license(self) -> None:
        doctor = StaffUser(
            username="dr.reyes",
            full_name="Dr. Ana Reyes",
            role=StaffRole.DOCTOR,
            specialty="Cardiology",
            license_number="PRC-123456",
        )
        doctor.set_password("doctor123")
        doctor.save()

        self.assertEqual(doctor.role, StaffRole.DOCTOR)
        self.assertEqual(doctor.specialty, "Cardiology")
        self.assertIn("Dr. Ana Reyes", str(doctor))
        self.assertIn("Cardiology", str(doctor))

    def test_short_password_rejected(self) -> None:
        staff = StaffUser(username="nurse1", full_name="Nurse Jane")
        with self.assertRaises(ValidationError):
            staff.set_password("12345")

    def test_invalid_username_characters_rejected(self) -> None:
        staff = StaffUser(username="user name with spaces!", full_name="Test User")
        staff.set_password("validpass123")
        with self.assertRaises(ValidationError):
            staff.save()

    def test_duplicate_username_rejected(self) -> None:
        staff1 = StaffUser(username="unique_user", full_name="User One")
        staff1.set_password("password123")
        staff1.save()

        staff2 = StaffUser(username="unique_user", full_name="User Two")
        staff2.set_password("password123")
        with self.assertRaises((IntegrityError, ValidationError)):
            staff2.save()


class UserSessionModelTests(TestCase):
    """Tests for UserSession token model."""

    def test_session_lifecycle_and_cascade(self) -> None:
        user = StaffUser.objects.create(
            username="session_user",
            full_name="Session User",
            password_hash="dummy_hash",
            role=StaffRole.RECEPTIONIST,
        )
        session = UserSession.objects.create(
            token="test_token_abcdef1234567890",
            user=user,
        )
        self.assertEqual(session.token, "test_token_abcdef1234567890")
        self.assertEqual(session.user, user)

        # Deleting the user must cascade delete active sessions
        user.delete()
        self.assertEqual(UserSession.objects.filter(token="test_token_abcdef1234567890").count(), 0)


class AppointmentEnrichedModelTests(TestCase):
    """Tests for Appointment with app_time, reason_for_visit, and doctor FK."""

    def setUp(self) -> None:
        self.patient = Patient.objects.create(
            full_name="Pedro Penduko", contact="09181112233", age=30
        )
        self.doctor = StaffUser.objects.create(
            username="dr.cruz",
            full_name="Dr. Robert Cruz",
            role=StaffRole.DOCTOR,
            specialty="Orthopedics",
            password_hash="dummy",
        )

    def test_create_appointment_with_time_and_doctor_fk(self) -> None:
        appt = Appointment(
            patient=self.patient,
            doctor=self.doctor,
            app_date=date(2026, 10, 15),
            app_time=time(14, 30),
            reason_for_visit="Knee joint pain after running",
            status=AppointmentStatus.SCHEDULED,
        )
        appt.save()

        self.assertIsNotNone(appt.id)
        self.assertEqual(appt.doctor_name, "Dr. Robert Cruz")
        self.assertEqual(appt.app_time, time(14, 30))
        self.assertEqual(appt.reason_for_visit, "Knee joint pain after running")
        self.assertEqual(appt.status, AppointmentStatus.SCHEDULED)

    def test_new_status_choices_valid(self) -> None:
        appt = Appointment(
            patient=self.patient,
            doctor_name="Dr. House",
            app_date=date(2026, 10, 15),
            app_time=time(10, 0),
            status=AppointmentStatus.CHECKED_IN,
        )
        appt.save()
        self.assertEqual(appt.status, AppointmentStatus.CHECKED_IN)

        appt.status = AppointmentStatus.IN_CONSULTATION
        appt.save()
        self.assertEqual(appt.status, AppointmentStatus.IN_CONSULTATION)


class MedicalRecordModelTests(TestCase):
    """Tests for MedicalRecord clinical documentation model."""

    def setUp(self) -> None:
        self.patient = Patient.objects.create(full_name="Clara Santos", age=45)
        self.doctor = StaffUser.objects.create(
            username="dr.tan",
            full_name="Dr. Lisa Tan",
            role=StaffRole.DOCTOR,
            specialty="Internal Medicine",
            password_hash="dummy",
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            doctor_name=self.doctor.full_name,
            app_date=date(2026, 9, 18),
            app_time=time(9, 30),
            status=AppointmentStatus.COMPLETED,
        )

    def test_create_medical_record_success(self) -> None:
        record = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            appointment=self.appointment,
            diagnosis="Essential Hypertension",
            symptoms="Occasional morning headaches, dizziness",
            clinical_notes="BP 145/95 mmHg, HR 78 bpm, lungs clear",
            prescription="Amlodipine 5mg once daily every morning",
            follow_up_advice="Reduce salt intake, return in 30 days for BP recheck",
        )
        record.save()

        self.assertIsNotNone(record.id)
        self.assertEqual(record.diagnosis, "Essential Hypertension")
        self.assertEqual(record.patient, self.patient)
        self.assertEqual(record.doctor, self.doctor)
        self.assertEqual(record.appointment, self.appointment)
        self.assertIn("Essential Hypertension", str(record))

    def test_empty_diagnosis_rejected(self) -> None:
        record = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis="",
        )
        with self.assertRaises(ValidationError):
            record.save()

    def test_medical_record_protects_patient_and_doctor_from_deletion(self) -> None:
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment=self.appointment,
            diagnosis="Routine Checkup",
        )
        self.assertIsNotNone(record.id)

        # Deleting patient must be blocked by models.PROTECT
        with self.assertRaises(ProtectedError):
            self.patient.delete()

        # Deleting doctor must be blocked by models.PROTECT
        with self.assertRaises(ProtectedError):
            self.doctor.delete()

    def test_unique_appointment_constraint_on_medical_record(self) -> None:
        MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment=self.appointment,
            diagnosis="Initial Consultation Note",
        )

        duplicate = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            appointment=self.appointment,
            diagnosis="Duplicate Consultation Note",
        )
        with self.assertRaises(ValidationError):
            duplicate.save()
