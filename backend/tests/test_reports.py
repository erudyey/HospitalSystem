"""Daily schedule report contracts and role isolation."""

import os
from datetime import datetime
from unittest.mock import patch

from django.test import Client, TestCase

from backend.clinic import services
from backend.clinic.models import Appointment, AppointmentStatus, StaffRole


@patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "synthetic-report-launch"})
class DailyReportTests(TestCase):
    def setUp(self) -> None:
        self.frontdesk = services.register_staff(
            "report.frontdesk", "synthetic-password", "Front Desk"
        )
        self.doctor = services.register_staff(
            "report.doctor", "synthetic-password", "Doctor One", StaffRole.DOCTOR
        )
        self.other_doctor = services.register_staff(
            "report.other", "synthetic-password", "Doctor Two", StaffRole.DOCTOR
        )
        self.patient = services.register_patient("Report Patient", "", 30)
        self.today = services.clinic_now().date().isoformat()

    def client_for(self, user) -> Client:
        _, session = services.authenticate_staff(user.username, "synthetic-password")
        return Client(
            headers={"X-Session-Token": "synthetic-report-launch", "X-User-Token": session.token}
        )

    def appointment(self, doctor, status: str = AppointmentStatus.SCHEDULED, **changes):
        return Appointment.objects.create(
            **(
                {
                    "doctor": doctor,
                    "doctor_name": doctor.full_name if doctor else "Legacy Doctor",
                    "patient": self.patient,
                    "app_date": self.today,
                    "app_time": "10:00",
                    "status": status,
                }
                | changes
            )
        )

    def test_all_states_and_distinct_patients_are_counted_without_double_counting(self) -> None:
        for status in AppointmentStatus.values:
            self.appointment(self.doctor, status)
        self.appointment(self.other_doctor)
        response = self.client_for(self.frontdesk).get("/api/reports/daily/")
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["scope"], "clinic")
        self.assertEqual(
            report["totals"],
            {
                "appointments": 6,
                "patients": 1,
                "scheduled": 2,
                "checked_in": 1,
                "in_consultation": 1,
                "completed": 1,
                "cancelled": 1,
            },
        )
        self.assertEqual([row["patients"] for row in report["doctors"]], [1, 1])
        self.assertNotIn("patient_name", str(report))
        self.assertNotIn("diagnosis", str(report))

    def test_doctor_cannot_expand_scope_using_query_parameters_or_legacy_name(self) -> None:
        self.appointment(self.doctor)
        self.appointment(self.other_doctor, AppointmentStatus.COMPLETED)
        self.appointment(None, doctor_name=self.doctor.full_name)
        report = (
            self.client_for(self.doctor)
            .get(f"/api/reports/daily/?scope=clinic&doctor_id={self.other_doctor.id}")
            .json()
        )
        self.assertEqual(report["scope"], "doctor")
        self.assertEqual(report["totals"]["appointments"], 1)
        self.assertEqual([row["doctor_id"] for row in report["doctors"]], [self.doctor.id])

    def test_unassigned_and_inactive_doctors_remain_in_clinic_reports(self) -> None:
        self.appointment(None)
        self.appointment(self.other_doctor)
        self.other_doctor.is_active = False
        self.other_doctor.save(update_fields=["is_active"])
        report = self.client_for(self.frontdesk).get("/api/reports/daily/").json()
        self.assertEqual(report["totals"]["appointments"], 2)
        self.assertEqual(
            {row["doctor_name"] for row in report["doctors"]}, {"Doctor Two", "Unassigned"}
        )

    def test_default_date_uses_clinic_day_and_explicit_date_stays_selected(self) -> None:
        now = datetime.fromisoformat("2026-09-02T00:05:00+08:00")
        self.appointment(self.doctor, app_date="2026-09-02")
        self.appointment(self.doctor, app_date="2026-09-01")
        with patch("backend.clinic.services.clinic_now", return_value=now):
            client = self.client_for(self.frontdesk)
            today = client.get("/api/reports/daily/").json()
            previous = client.get("/api/reports/daily/?date=2026-09-01").json()
        self.assertEqual(today["date"], "2026-09-02")
        self.assertEqual(today["generated_at"], now.isoformat())
        self.assertEqual(today["totals"]["appointments"], 1)
        self.assertEqual(previous["date"], "2026-09-01")
        self.assertEqual(previous["totals"]["appointments"], 1)

    def test_invalid_dates_are_visible_validation_errors(self) -> None:
        client = self.client_for(self.frontdesk)
        for invalid in ("", "20260901", "2026-02-30", "2026-9-1", "not-a-date"):
            with self.subTest(date=invalid):
                response = client.get("/api/reports/daily/", {"date": invalid})
                self.assertEqual(response.status_code, 400)
                self.assertIn("date", response.json()["error"]["fields"])

    def test_empty_past_future_and_leap_days_return_zero_totals(self) -> None:
        client = self.client_for(self.doctor)
        for target in ("2024-02-29", "2030-01-01"):
            report = client.get("/api/reports/daily/", {"date": target}).json()
            self.assertEqual(report["date"], target)
            self.assertEqual(report["doctors"], [])
            self.assertEqual(set(report["totals"].values()), {0})

    def test_report_requires_live_staff_and_loopback_authentication(self) -> None:
        self.assertEqual(Client().get("/api/reports/daily/").status_code, 403)
        anonymous = Client(headers={"X-Session-Token": "synthetic-report-launch"})
        self.assertEqual(anonymous.get("/api/reports/daily/").status_code, 401)
        client = self.client_for(self.doctor)
        self.doctor.is_active = False
        self.doctor.save(update_fields=["is_active"])
        self.assertEqual(client.get("/api/reports/daily/").status_code, 401)

    def test_report_marks_demo_and_updates_current_status(self) -> None:
        appointment = self.appointment(self.doctor)
        client = self.client_for(self.frontdesk)
        with patch.dict(os.environ, {"HOSPITAL_MODE": "demo"}):
            self.assertEqual(client.get("/api/reports/daily/").json()["mode"], "demo")
        services.update_appointment_status(appointment.id, AppointmentStatus.CANCELLED)
        report = client.get("/api/reports/daily/").json()
        self.assertEqual(report["totals"]["cancelled"], 1)
        self.assertEqual(report["totals"]["scheduled"], 0)
