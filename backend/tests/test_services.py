"""Unit tests for backend.clinic.services."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from backend.clinic import services
from backend.clinic.models import AppointmentStatus


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

    def test_update_appointment_status(self) -> None:
        # Arrange
        patient = services.register_patient("Taylor Kim", "09170000005", 28)
        app = services.book_appointment(patient.id, "Dr. Santos", "2026-09-20")

        # Act: Mark completed
        updated = services.update_appointment_status(app.id, "Completed")
        self.assertEqual(updated.status, AppointmentStatus.COMPLETED)

        # Act: Mark cancelled
        updated_cancelled = services.update_appointment_status(app.id, "Cancelled")
        self.assertEqual(updated_cancelled.status, AppointmentStatus.CANCELLED)

        # Act & Assert: Reverting to Scheduled is rejected by service contract
        with self.assertRaises(ValidationError) as ctx:
            services.update_appointment_status(app.id, "Scheduled")
        self.assertIn("status", ctx.exception.message_dict)
