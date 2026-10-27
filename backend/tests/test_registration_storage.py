"""Public staff registration and authenticated storage information."""

import json
import os
from unittest.mock import patch

from django.db import connection
from django.test import Client, TestCase

from backend.clinic import services
from backend.clinic.models import StaffRole


@patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-launch-token"})
class RegistrationStorageTests(TestCase):
    def setUp(self) -> None:
        self.client = Client(headers={"X-Session-Token": "test-launch-token"})

    def register(self, username: str, role: str, confirmation: str = "password123"):
        return self.client.post(
            "/api/auth/register/",
            data=json.dumps(
                {
                    "username": username,
                    "full_name": "Example Staff",
                    "role": role,
                    "password": "password123",
                    "password_confirmation": confirmation,
                }
            ),
            content_type="application/json",
        )

    def test_initial_receptionist_then_signed_out_registration_for_both_roles(self) -> None:
        self.assertEqual(self.register("first", StaffRole.DOCTOR).status_code, 400)
        self.assertEqual(self.register("first", StaffRole.RECEPTIONIST).status_code, 201)
        for role in (StaffRole.RECEPTIONIST, StaffRole.DOCTOR):
            response = self.register(f"new.{role}", role)
            self.assertEqual(response.status_code, 201)
            login = self.client.post(
                "/api/auth/login/",
                data=json.dumps({"username": f"new.{role}", "password": "password123"}),
                content_type="application/json",
            )
            self.assertEqual(login.status_code, 200)
            self.assertEqual(login.json()["user"]["role"], role)

    def test_duplicate_and_mismatched_password_have_field_errors(self) -> None:
        self.register("first", StaffRole.RECEPTIONIST)
        duplicate = self.register("FIRST", StaffRole.DOCTOR)
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("username", duplicate.json()["error"]["fields"])
        mismatch = self.register("other", StaffRole.DOCTOR, "wrong")
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn("password_confirmation", mismatch.json()["error"]["fields"])

    def test_registration_still_rejects_a_different_local_origin(self) -> None:
        services.register_staff("first", "password123", "First Receptionist")
        client = Client(enforce_csrf_checks=True)
        client.get("/?token=test-launch-token")
        response = client.post(
            "/api/auth/register/",
            data=json.dumps(
                {"username": "new", "password": "password123", "full_name": "New Staff"}
            ),
            content_type="application/json",
            headers={
                "Origin": "http://127.0.0.1:59999",
                "X-CSRFToken": client.cookies["csrftoken"].value,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_storage_requires_staff_and_reports_active_config(self) -> None:
        self.assertEqual(self.client.get("/api/system/storage/").status_code, 401)
        services.register_staff("staff", "password123", "Staff")
        _, session = services.authenticate_staff("staff", "password123")
        staff_client = Client(
            headers={"X-Session-Token": "test-launch-token", "X-User-Token": session.token}
        )
        with (
            patch.dict(os.environ, {"HOSPITAL_MODE": "demo"}),
            patch.dict(connection.settings_dict, {"NAME": "custom/clinic_demo.sqlite3"}),
        ):
            response = staff_client.get("/api/system/storage/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "demo")
        self.assertEqual(response.json()["database_path"], "custom/clinic_demo.sqlite3")
        self.assertTrue(response.json()["journal_mode"])
