"""Unit tests for backend.clinic.services."""

from datetime import date
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from backend.clinic import services
from backend.clinic.models import AppointmentStatus
from desktop.launcher import get_app_dir


class ClinicServicesTests(TestCase):
    """Test suite validating business logic and domain invariants."""

    def test_register_patient_happy_path(self) -> None:
        # Arrange & Act
        patient = services.register_patient("Maria Santos", "09170000001", 30)

        # Assert
        self.assertIsNotNone(patient.id)
        self.assertEqual(patient.full_name, "Maria Santos")
        self.assertEqual(patient.contact, "09170000001")
        self.assertEqual(patient.age, 30)

    def test_duplicate_names_allocate_separate_ids(self) -> None:
        # Arrange & Act: Register two patients with the exact same name
        p1 = services.register_patient("Alex Reyes", "09170000001", 20)
        p2 = services.register_patient("Alex Reyes", "09170000002", 21)

        # Assert: Both exist, names match, but IDs must be distinct
        self.assertNotEqual(p1.id, p2.id)
        self.assertEqual(p1.full_name, p2.full_name)
        self.assertEqual(len(services.list_patients("Alex Reyes")), 2)

    def test_register_patient_invalid_inputs_rejected(self) -> None:
        # Blank name
        with self.assertRaises(ValidationError) as ctx:
            services.register_patient("   ", "09170000001", 25)
        self.assertIn("full_name", ctx.exception.message_dict)

        # Zero age
        with self.assertRaises(ValidationError) as ctx:
            services.register_patient("John Doe", "09170000001", 0)
        self.assertIn("age", ctx.exception.message_dict)

        # Negative age
        with self.assertRaises(ValidationError) as ctx:
            services.register_patient("John Doe", "09170000001", -5)
        self.assertIn("age", ctx.exception.message_dict)

    def test_list_and_search_patients(self) -> None:
        # Arrange
        p1 = services.register_patient("Johnathan Doe", "111", 40)
        p2 = services.register_patient("Jane Smith", "222", 35)

        # Act & Assert: Substring search
        results = services.list_patients(query="john")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, p1.id)

        # Act & Assert: Exact numeric ID search
        results_id = services.list_patients(query=str(p2.id))
        self.assertEqual(len(results_id), 1)
        self.assertEqual(results_id[0].id, p2.id)

    def test_book_appointment_for_patient(self) -> None:
        # Arrange
        patient = services.register_patient("Carlos Rivera", "09170000003", 45)

        # Act
        app = services.book_appointment(patient.id, "Dr. Mendoza", "2026-09-25")

        # Assert
        self.assertIsNotNone(app.id)
        self.assertEqual(app.patient_id, patient.id)
        self.assertEqual(app.doctor_name, "Dr. Mendoza")
        self.assertEqual(app.app_date, date(2026, 9, 25))
        self.assertEqual(app.status, AppointmentStatus.SCHEDULED)

    def test_book_appointment_rejects_missing_patient(self) -> None:
        # Act & Assert: Non-existent patient ID
        with self.assertRaises(ValidationError) as ctx:
            services.book_appointment(99999, "Dr. Mendoza", "2026-09-25")
        self.assertIn("patient_id", ctx.exception.message_dict)

    def test_book_appointment_rejects_invalid_date_or_blank_doctor(self) -> None:
        patient = services.register_patient("Sam Lee", "09170000004", 22)

        # Blank doctor
        with self.assertRaises(ValidationError) as ctx:
            services.book_appointment(patient.id, "   ", "2026-09-25")
        self.assertIn("doctor_name", ctx.exception.message_dict)

        # Malformed date
        with self.assertRaises(ValidationError) as ctx:
            services.book_appointment(patient.id, "Dr. Santos", "invalid-date")
        self.assertIn("app_date", ctx.exception.message_dict)

    def test_update_patient(self) -> None:
        # Arrange
        patient = services.register_patient("Morgan Reed", "09171112233", 31)

        # Act
        updated = services.update_patient(patient.id, "Morgan R. Reed", "09179998877", 32)

        # Assert
        self.assertEqual(updated.full_name, "Morgan R. Reed")
        self.assertEqual(updated.contact, "09179998877")
        self.assertEqual(updated.age, 32)

    def test_delete_patient_cascades_appointments(self) -> None:
        # Arrange
        patient = services.register_patient("Jordan Bell", "09173334455", 40)
        app1 = services.book_appointment(patient.id, "Dr. Reyes", "2026-10-01")
        app2 = services.book_appointment(patient.id, "Dr. Mendoza", "2026-10-05")

        # Act
        services.delete_patient(patient.id)

        # Assert: Patient and associated appointments are deleted
        self.assertEqual(len(services.list_patients(query=str(patient.id))), 0)
        all_apps = services.list_all_appointments()
        app_ids = [a.id for a in all_apps]
        self.assertNotIn(app1.id, app_ids)
        self.assertNotIn(app2.id, app_ids)

    def test_delete_patient_with_completed_records_rejected(self) -> None:
        patient = services.register_patient("Sam Protected", "09170000008", 45)
        app = services.book_appointment(patient.id, "Dr. Stone", "2026-10-10")
        services.update_appointment_status(app.id, AppointmentStatus.COMPLETED)

        # Attempting to delete patient with completed appointment raises ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.delete_patient(patient.id)
        self.assertIn("patient", ctx.exception.message_dict)

    def test_list_all_appointments(self) -> None:
        # Arrange
        p1 = services.register_patient("Patient One", "111", 20)
        p2 = services.register_patient("Patient Two", "222", 30)
        app1 = services.book_appointment(p1.id, "Dr. A", "2026-10-01")
        app2 = services.book_appointment(p2.id, "Dr. B", "2026-10-02")

        # Act
        all_apps = services.list_all_appointments()

        # Assert
        ids = [a.id for a in all_apps]
        self.assertIn(app1.id, ids)
        self.assertIn(app2.id, ids)

    def test_update_appointment_reschedule(self) -> None:
        # Arrange
        patient = services.register_patient("Casey Vance", "09175556677", 29)
        app = services.book_appointment(patient.id, "Dr. Old", "2026-10-10")

        # Act
        updated = services.update_appointment(app.id, "Dr. New", "2026-10-15")

        # Assert
        self.assertEqual(updated.doctor_name, "Dr. New")
        self.assertEqual(updated.app_date, date(2026, 10, 15))

    def test_update_completed_appointment_rejected(self) -> None:
        # Arrange
        patient = services.register_patient("Drew Scott", "09177778899", 50)
        app = services.book_appointment(patient.id, "Dr. Stone", "2026-10-10")
        services.update_appointment_status(app.id, "Completed")

        # Act & Assert: Modifying a completed appointment is rejected
        with self.assertRaises(ValidationError) as ctx:
            services.update_appointment(app.id, "Dr. Altered", "2026-10-20")
        self.assertIn("appointment", ctx.exception.message_dict)

    def test_delete_appointment(self) -> None:
        # Arrange
        patient = services.register_patient("Riley Quinn", "09178889900", 25)
        app = services.book_appointment(patient.id, "Dr. Clark", "2026-10-12")

        # Act
        services.delete_appointment(app.id)

        # Assert
        self.assertEqual(len(services.list_patient_appointments(patient.id)), 0)

    def test_delete_completed_appointment_rejected(self) -> None:
        patient = services.register_patient("Jordan Lee", "09170000099", 40)
        app = services.book_appointment(patient.id, "Dr. House", "2026-10-12")
        services.update_appointment_status(app.id, AppointmentStatus.COMPLETED)

        with self.assertRaises(ValidationError) as ctx:
            services.delete_appointment(app.id)
        self.assertIn("appointment", ctx.exception.message_dict)

    def test_appointment_state_machine_invariants(self) -> None:
        # Arrange
        patient = services.register_patient("Taylor Kim", "09170000005", 28)
        app = services.book_appointment(patient.id, "Dr. Santos", "2026-09-20")

        # 1. Scheduled -> Completed
        updated = services.update_appointment_status(app.id, "Completed")
        self.assertEqual(updated.status, AppointmentStatus.COMPLETED)

        # 2. Completed -> Cancelled is FORBIDDEN (immutable clinical record)
        with self.assertRaises(ValidationError) as ctx:
            services.update_appointment_status(app.id, "Cancelled")
        self.assertIn("status", ctx.exception.message_dict)

        # 3. Completed -> Scheduled is FORBIDDEN
        with self.assertRaises(ValidationError) as ctx:
            services.update_appointment_status(app.id, "Scheduled")
        self.assertIn("status", ctx.exception.message_dict)

        # 4. New appointment: Scheduled -> Cancelled
        app2 = services.book_appointment(patient.id, "Dr. Santos", "2026-09-21")
        cancelled = services.update_appointment_status(app2.id, "Cancelled")
        self.assertEqual(cancelled.status, AppointmentStatus.CANCELLED)

        # 5. Cancelled -> Completed is FORBIDDEN (must restore to Scheduled first)
        with self.assertRaises(ValidationError) as ctx:
            services.update_appointment_status(app2.id, "Completed")
        self.assertIn("status", ctx.exception.message_dict)

        # 6. Cancelled -> Scheduled is ALLOWED (restoration)
        restored = services.update_appointment_status(app2.id, "Scheduled")
        self.assertEqual(restored.status, AppointmentStatus.SCHEDULED)

    def test_patient_active_appointment_count_annotation(self) -> None:
        # Arrange
        patient = services.register_patient("Alex Morgan", "09171234567", 30)
        app = services.book_appointment(patient.id, "Dr. Grey", "2026-11-10")

        # Act 1: Initial state is Scheduled
        fetched = services.get_patient(patient.id)
        self.assertEqual(getattr(fetched, "appointment_count", 0), 1)
        self.assertEqual(getattr(fetched, "active_appointment_count", 0), 1)

        # Act 2: Mark appointment as Completed -> active count drops to 0 while total remains 1
        services.update_appointment_status(app.id, "Completed")
        fetched_after = services.get_patient(patient.id)
        self.assertEqual(getattr(fetched_after, "appointment_count", 0), 1)
        self.assertEqual(getattr(fetched_after, "active_appointment_count", 0), 0)

    def test_cross_platform_app_dir_resolution(self):
        """Verify get_app_dir resolves correct paths across operating systems."""
        with patch("sys.platform", "darwin"):
            darwin_dir = get_app_dir()
            self.assertTrue(str(darwin_dir).endswith("HospitalSystem"))
            self.assertIn("Library", str(darwin_dir))

        with patch("sys.platform", "win32"):
            win_dir = get_app_dir()
            self.assertTrue(str(win_dir).endswith("HospitalSystem"))
