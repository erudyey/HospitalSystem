"""Regression coverage for clinical data preservation and desktop launch security."""

import json
import os
from datetime import date, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings

from backend.clinic import services
from backend.clinic.models import Appointment, AppointmentStatus, MedicalRecord, Patient, StaffRole


class ClinicalPreservationTests(TestCase):
    def setUp(self) -> None:
        self.patient = services.register_patient("Synthetic Patient", "555-0101", 31)
        self.doctor = services.register_staff(
            "synthetic.doctor", "synthetic-password", "Synthetic Doctor", StaffRole.DOCTOR
        )
        self.today = services.clinic_now().date()

    def appointment(self, **changes):
        values = {
            "patient": self.patient,
            "doctor": self.doctor,
            "doctor_name": self.doctor.full_name,
            "app_date": self.today,
            "app_time": "10:00",
        }
        return Appointment.objects.create(**(values | changes))

    def test_active_consultation_blocks_parent_and_appointment_changes(self) -> None:
        appointment = self.appointment(status=AppointmentStatus.IN_CONSULTATION)
        for operation in (
            lambda: services.delete_patient(self.patient.id),
            lambda: services.delete_appointment(appointment.id),
            lambda: services.update_appointment(appointment.id, doctor_name="Another Doctor"),
        ):
            with self.assertRaises(ValidationError):
                operation()
        self.assertTrue(Patient.objects.filter(id=self.patient.id).exists())
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, AppointmentStatus.IN_CONSULTATION)

    def test_check_in_rejects_another_day_and_today_enters_doctor_queue(self) -> None:
        tomorrow = self.appointment(app_date=self.today + timedelta(days=1))
        with self.assertRaises(ValidationError):
            services.update_appointment_status(tomorrow.id, AppointmentStatus.CHECKED_IN)
        today = self.appointment()
        services.update_appointment_status(today.id, AppointmentStatus.CHECKED_IN)
        queue = services.get_doctor_queue(self.doctor.id)
        self.assertEqual([row.id for row in queue["checked_in"]], [today.id])
        tomorrow.refresh_from_db()
        self.assertEqual(tomorrow.status, AppointmentStatus.SCHEDULED)

    def test_cancelled_appointment_cannot_reclaim_occupied_or_past_slot(self) -> None:
        cancelled = self.appointment(status=AppointmentStatus.CANCELLED)
        self.appointment()
        with self.assertRaises(ValidationError):
            services.update_appointment_status(cancelled.id, AppointmentStatus.SCHEDULED)
        past = self.appointment(app_date=date(2020, 1, 1), status=AppointmentStatus.CANCELLED)
        with self.assertRaises(ValidationError):
            services.update_appointment_status(past.id, AppointmentStatus.SCHEDULED)
        cancelled.refresh_from_db()
        self.assertEqual(cancelled.status, AppointmentStatus.CANCELLED)

    def test_joined_roster_counts_each_appointment_once(self) -> None:
        for hour in (10, 11):
            appointment = self.appointment(
                app_time=f"{hour}:00", status=AppointmentStatus.COMPLETED
            )
            MedicalRecord.objects.create(
                patient=self.patient,
                doctor=self.doctor,
                appointment=appointment,
                diagnosis="Synthetic diagnosis",
            )
        roster = services.get_doctor_patients(self.doctor.id)
        self.assertEqual(getattr(roster[0], "appointment_count", 0), 2)
        self.assertEqual(getattr(roster[0], "doctor_appointment_count", 0), 2)

    def test_doctor_name_edit_cannot_disagree_with_assigned_physician(self) -> None:
        appointment = self.appointment()
        with self.assertRaises(ValidationError):
            services.update_appointment(appointment.id, doctor_name="Different physician")
        appointment.refresh_from_db()
        self.assertEqual(appointment.doctor_id, self.doctor.id)
        self.assertEqual(appointment.doctor_name, self.doctor.full_name)

    def test_legacy_rows_cannot_overwrite_existing_clinical_history(self) -> None:
        appointment = self.appointment(status=AppointmentStatus.COMPLETED)
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment=appointment,
            diagnosis="Preserved diagnosis",
        )
        with self.assertRaises(ValidationError):
            services.import_legacy_rows(
                [{"id": self.patient.id, "full_name": "Overwritten", "contact": "", "age": 20}],
                [
                    {
                        "id": appointment.id,
                        "patient_id": self.patient.id,
                        "doctor_name": "Other",
                        "app_date": self.today,
                        "status": AppointmentStatus.SCHEDULED,
                    }
                ],
            )
        self.patient.refresh_from_db()
        appointment.refresh_from_db()
        record.refresh_from_db()
        self.assertEqual(self.patient.full_name, "Synthetic Patient")
        self.assertEqual(appointment.status, AppointmentStatus.COMPLETED)
        self.assertEqual(record.diagnosis, "Preserved diagnosis")

    @override_settings(DEBUG=False, IS_TESTING=False)
    def test_sample_seeding_cannot_clear_clinic_data(self) -> None:
        with self.assertRaises(ValidationError):
            services.seed_sample_rows([], clear=True)
        self.assertTrue(Patient.objects.filter(id=self.patient.id).exists())

    def test_failed_sample_seed_rolls_back_clear_and_partial_writes(self) -> None:
        with self.assertRaises(ValidationError):
            services.seed_sample_rows(
                [{"full_name": "Invalid sample", "contact": "", "age": -1, "appointments": []}],
                clear=True,
            )
        self.assertTrue(Patient.objects.filter(id=self.patient.id).exists())


@patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "synthetic-launch-token"})
class DesktopSecurityTests(TestCase):
    def test_root_requires_launch_token_and_sets_protected_cookie(self) -> None:
        client = Client()
        self.assertEqual(client.get("/").status_code, 403)
        self.assertEqual(client.get("/?token=wrong").status_code, 403)
        response = client.get("/?token=synthetic-launch-token")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies["session_token"]["httponly"])
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_other_local_port_cannot_bootstrap_staff_account(self) -> None:
        client = Client(enforce_csrf_checks=True)
        client.get("/?token=synthetic-launch-token")
        response = client.post(
            "/api/auth/register/",
            data=json.dumps(
                {
                    "username": "synthetic",
                    "password": "synthetic-password",
                    "full_name": "Synthetic",
                }
            ),
            content_type="application/json",
            headers={
                "Origin": "http://127.0.0.1:59999",
                "X-CSRFToken": client.cookies["csrftoken"].value,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_login_rejects_nontext_credentials_without_server_error(self) -> None:
        response = Client(headers={"X-Session-Token": "synthetic-launch-token"}).post(
            "/api/auth/login/",
            data=json.dumps({"username": ["synthetic"], "password": {}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
