"""Regression coverage for role handoffs, demo resets, and profile sessions."""

import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from backend.clinic import services
from backend.clinic.models import (
    Appointment,
    AppointmentAudit,
    AppointmentStatus,
    DemoSeedState,
    MedicalRecord,
    Patient,
    StaffRole,
    StaffUser,
    UserSession,
)


@patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "synthetic-workflow-launch"})
class RoleHandoffTests(TestCase):
    def setUp(self) -> None:
        self.receptionist = services.register_staff(
            "synthetic.frontdesk", "synthetic-password", "Synthetic Front Desk"
        )
        self.doctor = services.register_staff(
            "synthetic.physician", "synthetic-password", "Synthetic Physician", StaffRole.DOCTOR
        )
        _, session = services.authenticate_staff("synthetic.frontdesk", "synthetic-password")
        self.token = session.token
        self.frontdesk = self.client_for(session.token)
        _, session = services.authenticate_staff("synthetic.physician", "synthetic-password")
        self.physician = self.client_for(session.token)
        self.patient = services.register_patient("Handoff Patient", "555-0102", 24)
        self.today = services.clinic_now().date().isoformat()

    def client_for(self, token: str) -> Client:
        return Client(
            headers={"X-Session-Token": "synthetic-workflow-launch", "X-User-Token": token}
        )

    def send(self, client: Client, method: str, path: str, payload: dict):
        return getattr(client, method)(
            path, data=json.dumps(payload), content_type="application/json"
        )

    def book(self, app_time: str = "10:00") -> dict:
        response = self.send(
            self.frontdesk,
            "post",
            "/api/appointments/",
            {
                "patient_id": self.patient.id,
                "doctor_id": self.doctor.id,
                "app_date": self.today,
                "app_time": app_time,
                "reason_for_visit": "Synthetic handoff",
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_booking_check_in_and_signed_visit_propagate_between_roles(self) -> None:
        appointment = self.book()
        appointment_id = appointment["id"]
        queue = self.physician.get("/api/doctor/queue/").json()["queue"]
        self.assertEqual([row["id"] for row in queue["scheduled"]], [appointment_id])
        roster = self.physician.get("/api/doctor/patients/").json()
        self.assertEqual(roster[0]["id"], self.patient.id)
        self.assertEqual(roster[0]["doctor_appointment_count"], 1)

        status_path = f"/api/appointments/{appointment_id}/status/"
        checked_in = self.send(
            self.frontdesk, "patch", status_path, {"status": AppointmentStatus.CHECKED_IN}
        )
        self.assertEqual(checked_in.status_code, 200, checked_in.content)
        queue = self.physician.get("/api/doctor/queue/").json()["queue"]
        self.assertEqual([row["id"] for row in queue["checked_in"]], [appointment_id])
        begun = self.send(
            self.physician, "patch", status_path, {"status": AppointmentStatus.IN_CONSULTATION}
        )
        self.assertEqual(begun.status_code, 200, begun.content)
        signed = self.send(
            self.physician,
            "post",
            "/api/medical-records/",
            {
                "patient_id": self.patient.id,
                "appointment_id": appointment_id,
                "diagnosis": "Synthetic signed diagnosis",
            },
        )
        self.assertEqual(signed.status_code, 201, signed.content)
        refreshed = self.frontdesk.get(f"/api/appointments/{appointment_id}/").json()
        self.assertEqual(refreshed["status"], AppointmentStatus.COMPLETED)
        self.assertEqual(self.physician.get("/api/doctor/queue/").json()["queue"]["checked_in"], [])
        denied = self.frontdesk.delete(f"/api/patients/{self.patient.id}/")
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(MedicalRecord.objects.get().doctor_id, self.doctor.id)

    def test_new_physician_is_bookable_without_replacing_frontdesk_session(self) -> None:
        response = self.send(
            self.frontdesk,
            "post",
            "/api/auth/register/",
            {
                "username": "synthetic.newdoctor",
                "password": "synthetic-password",
                "password_confirmation": "synthetic-password",
                "full_name": "New Synthetic Doctor",
                "role": "doctor",
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            self.frontdesk.get("/api/auth/me/").json()["user"]["id"], self.receptionist.id
        )
        self.assertIn(
            response.json()["id"], [row["id"] for row in self.frontdesk.get("/api/doctors/").json()]
        )

    def test_contact_save_keeps_session_and_credential_change_rotates_it(self) -> None:
        response = self.send(
            self.frontdesk,
            "put",
            "/api/auth/profile/",
            {"username": self.receptionist.username, "contact": "555-0199"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn("token", response.json())
        self.assertEqual(self.frontdesk.get("/api/auth/me/").status_code, 200)
        changed = self.send(
            self.frontdesk,
            "put",
            "/api/auth/profile/",
            {"username": "synthetic.renamed", "current_password": "synthetic-password"},
        )
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(self.frontdesk.get("/api/auth/me/").status_code, 401)
        self.assertEqual(
            self.client_for(changed.json()["token"]).get("/api/auth/me/").status_code, 200
        )

    def test_reschedule_override_requires_reason_and_preserves_audit(self) -> None:
        appointment = self.book()
        self.book("11:00")
        path = f"/api/appointments/{appointment['id']}/"
        payload = {"app_time": "11:00", "allow_conflict": True}
        self.assertEqual(self.send(self.frontdesk, "put", path, payload).status_code, 400)
        payload["override_reason"] = "Urgent synthetic review"
        response = self.send(self.frontdesk, "put", path, payload)
        self.assertEqual(response.status_code, 200, response.content)
        event = AppointmentAudit.objects.filter(
            appointment_id=appointment["id"], event="rescheduled"
        ).get()
        self.assertEqual(event.reason, "Urgent synthetic review")

    def test_blank_username_is_rejected_without_replacing_the_current_session(self) -> None:
        response = self.send(
            self.frontdesk,
            "put",
            "/api/auth/profile/",
            {"username": "", "current_password": "synthetic-password"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.frontdesk.get("/api/auth/me/").status_code, 200)
        self.receptionist.refresh_from_db()
        self.assertEqual(self.receptionist.username, "synthetic.frontdesk")

    def test_return_to_schedule_clears_old_arrival_priority(self) -> None:
        appointment = self.book()
        first_arrival = datetime(2026, 9, 1, 8)
        with patch("backend.clinic.services.timezone.now", return_value=first_arrival):
            services.update_appointment_status(appointment["id"], AppointmentStatus.CHECKED_IN)
        scheduled = services.update_appointment_status(
            appointment["id"], AppointmentStatus.SCHEDULED
        )
        self.assertIsNone(scheduled.checked_in_at)
        later_arrival = first_arrival + timedelta(minutes=30)
        with patch("backend.clinic.services.timezone.now", return_value=later_arrival):
            arrival = services.update_appointment_status(
                appointment["id"], AppointmentStatus.CHECKED_IN
            )
        self.assertEqual(arrival.checked_in_at, later_arrival)

    def assert_reason_edit_preserves_check_in(self, now: datetime) -> None:
        appointment = self.book()
        path = f"/api/appointments/{appointment['id']}/"
        arrived = self.send(
            self.frontdesk, "patch", path + "status/", {"status": AppointmentStatus.CHECKED_IN}
        ).json()
        with patch("backend.clinic.services.clinic_now", return_value=now):
            response = self.send(
                self.frontdesk,
                "put",
                path,
                {
                    "doctor_id": self.doctor.id,
                    "app_date": self.today,
                    "app_time": "10:00",
                    "reason_for_visit": "Corrected chief complaint",
                },
            )
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["status"], AppointmentStatus.CHECKED_IN)
            self.assertEqual(response.json()["checked_in_at"], arrived["checked_in_at"])
            queue = self.physician.get("/api/doctor/queue/").json()["queue"]["checked_in"]
            self.assertEqual(queue[0]["reason_for_visit"], "Corrected chief complaint")

    def test_reason_edit_keeps_early_arrival_in_waiting_room(self) -> None:
        self.assert_reason_edit_preserves_check_in(datetime(2026, 9, 1, 8, tzinfo=UTC))

    def test_reason_edit_remains_possible_after_booked_time_has_passed(self) -> None:
        self.assert_reason_edit_preserves_check_in(datetime(2026, 9, 1, 12, tzinfo=UTC))

    def test_actual_reschedule_requires_another_check_in(self) -> None:
        appointment = self.book()
        path = f"/api/appointments/{appointment['id']}/"
        self.send(
            self.frontdesk, "patch", path + "status/", {"status": AppointmentStatus.CHECKED_IN}
        )
        response = self.send(self.frontdesk, "put", path, {"app_time": "11:00"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], AppointmentStatus.SCHEDULED)
        self.assertIsNone(response.json()["checked_in_at"])
        self.assertEqual(self.physician.get("/api/doctor/queue/").json()["queue"]["checked_in"], [])


@patch.dict(
    os.environ, {"HOSPITAL_MODE": "demo", "HOSPITAL_SESSION_TOKEN": "synthetic-demo-launch"}
)
class DemoResetTests(TestCase):
    def test_unversioned_demo_keeps_existing_data_and_has_account_chooser(self) -> None:
        patient = services.register_patient("Existing demo edit", "", 21)
        services.ensure_demo_data()
        self.assertEqual(list(Patient.objects.values_list("id", flat=True)), [patient.id])
        self.assertEqual(len(services.list_demo_accounts()), 4)
        self.assertTrue(DemoSeedState.objects.exists())

    def test_reset_reanchors_dates_preserves_renamed_profiles_and_revokes_sessions(self) -> None:
        services.ensure_demo_data()
        physician = StaffUser.objects.get(username="dreyes")
        _, session = services.authenticate_demo_account(physician.id)
        services.update_staff_profile(
            physician.id,
            "Renamed Demo Physician",
            username="renamed.demo",
            current_password="password123",
            session_token=session.token,
        )
        future = datetime(2026, 9, 9, 23, 55, tzinfo=UTC)
        with patch("backend.clinic.services.clinic_now", return_value=future):
            services.ensure_demo_data()
            self.assertTrue(Appointment.objects.filter(app_date__lt=future.date()).exists())
            services.reset_demo_data()
            active = Appointment.objects.filter(
                status__in=[AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION]
            )
            self.assertTrue(active.exists())
            self.assertFalse(active.exclude(app_date=future.date()).exists())
            scheduled = Appointment.objects.filter(status=AppointmentStatus.SCHEDULED)
            self.assertFalse(scheduled.filter(app_date__lte=future.date()).exists())
        physician.refresh_from_db()
        self.assertEqual(physician.username, "renamed.demo")
        self.assertEqual(physician.full_name, "Renamed Demo Physician")
        self.assertEqual(StaffUser.objects.count(), 4)
        self.assertIn(physician.id, [user.id for user in services.list_demo_accounts()])
        self.assertFalse(UserSession.objects.exists())

    def test_reset_requires_confirmation_and_is_forbidden_in_clinic_mode(self) -> None:
        patient = services.register_patient("Preserved clinic patient", "", 35)
        client = Client(headers={"X-Session-Token": "synthetic-demo-launch"})
        self.assertEqual(
            client.post("/api/demo/reset/", data="{}", content_type="application/json").status_code,
            400,
        )
        with patch.dict(os.environ, {"HOSPITAL_MODE": "clinic"}):
            response = client.post(
                "/api/demo/reset/", data='{"confirm": true}', content_type="application/json"
            )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Patient.objects.filter(id=patient.id).exists())

    @override_settings(DEBUG=False, IS_TESTING=False)
    def test_sample_seeder_rejects_production_and_supports_late_day_demo_history(self) -> None:
        with patch.dict(os.environ, {"HOSPITAL_MODE": "clinic"}):
            from django.core.exceptions import ValidationError

            with self.assertRaises(ValidationError):
                services.seed_clinical_samples(clear=True)
        with patch(
            "backend.clinic.services.clinic_now",
            return_value=datetime(2026, 9, 1, 23, 55, tzinfo=UTC),
        ):
            counts = services.seed_clinical_samples(count=10)
        self.assertEqual(counts, {"patients": 10, "appointments": 10, "records": 2})
        self.assertEqual(MedicalRecord.objects.count(), 2)
        self.assertEqual(Appointment.objects.filter(status=AppointmentStatus.COMPLETED).count(), 2)
