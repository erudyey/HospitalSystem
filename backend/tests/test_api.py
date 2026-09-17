"""Integration tests for backend.clinic.views and security middleware."""

import json
import os
from unittest.mock import patch

from django.test import Client, TestCase

from backend.clinic import services


class ClinicAPITests(TestCase):
    """Test suite validating JSON endpoints, error envelopes, and loopback token security."""

    def setUp(self) -> None:
        self.client = Client()
        self.token = "test-secret-session-token-32-chars-long"
        self.auth_client = Client(headers={"X-Session-Token": self.token})

    def test_health_check_available_without_token(self) -> None:
        # Act
        response = self.client.get("/api/health/")

        # Assert: Health check must be 200 without token so readiness probe can check server
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    @patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-secret-session-token-32-chars-long"})
    def test_endpoints_reject_requests_without_session_token(self) -> None:
        # Act: Attempt GET without token header
        response = self.client.get("/api/patients/")

        # Assert: Must be 403 Forbidden
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    @patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-secret-session-token-32-chars-long"})
    def test_register_patient_api(self) -> None:
        # Act: Successful registration
        payload = {"full_name": "Anna Cruz", "contact": "09191234567", "age": 29}
        response = self.auth_client.post(
            "/api/patients/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Assert: 201 Created with JSON representation
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["full_name"], "Anna Cruz")
        self.assertEqual(data["age"], 29)

    @patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-secret-session-token-32-chars-long"})
    def test_register_patient_validation_error_envelope(self) -> None:
        # Act: Missing name
        payload = {"full_name": "", "contact": "123", "age": -1}
        response = self.auth_client.post(
            "/api/patients/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Assert: 400 Bad Request with standardized error envelope
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("full_name", data["error"]["fields"])
        self.assertIn("age", data["error"]["fields"])

    @patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-secret-session-token-32-chars-long"})
    def test_book_and_update_appointment_api(self) -> None:
        # Arrange
        patient = services.register_patient("David Kim", "09181112233", 42)

        # Act 1: Book appointment
        book_payload = {
            "patient_id": patient.id,
            "doctor_name": "Dr. Tan",
            "app_date": "2026-10-01",
        }
        book_resp = self.auth_client.post(
            "/api/appointments/",
            data=json.dumps(book_payload),
            content_type="application/json",
        )
        self.assertEqual(book_resp.status_code, 201)
        app_data = book_resp.json()
        self.assertEqual(app_data["status"], "Scheduled")

        # Act 2: Fetch appointments for patient
        list_resp = self.auth_client.get(f"/api/patients/{patient.id}/appointments/")
        self.assertEqual(list_resp.status_code, 200)
        appointments = list_resp.json()
        self.assertEqual(len(appointments), 1)
        self.assertEqual(appointments[0]["id"], app_data["id"])

        # Act 3: Patch status to Completed
        patch_payload = {"status": "Completed"}
        patch_resp = self.auth_client.patch(
            f"/api/appointments/{app_data['id']}/status/",
            data=json.dumps(patch_payload),
            content_type="application/json",
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertEqual(patch_resp.json()["status"], "Completed")
