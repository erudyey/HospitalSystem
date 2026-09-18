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

    @patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-secret-session-token-32-chars-long"})
    def test_patient_detail_crud_api(self) -> None:
        # Arrange: Register patient
        patient = services.register_patient("Rachel Green", "09170001122", 28)
        services.book_appointment(patient.id, "Dr. Burke", "2026-10-15")

        # Act 1: GET patient detail
        get_resp = self.auth_client.get(f"/api/patients/{patient.id}/")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertEqual(data["full_name"], "Rachel Green")
        self.assertEqual(data["appointment_count"], 1)
        self.assertEqual(data["active_appointment_count"], 1)

        # Act 2: PUT update patient
        put_payload = {"full_name": "Rachel Geller-Green", "contact": "09179990011", "age": 29}
        put_resp = self.auth_client.put(
            f"/api/patients/{patient.id}/",
            data=json.dumps(put_payload),
            content_type="application/json",
        )
        self.assertEqual(put_resp.status_code, 200)
        updated_data = put_resp.json()
        self.assertEqual(updated_data["full_name"], "Rachel Geller-Green")
        self.assertEqual(updated_data["contact"], "09179990011")
        self.assertEqual(updated_data["age"], 29)

        # Act 3: DELETE patient
        del_resp = self.auth_client.delete(f"/api/patients/{patient.id}/")
        self.assertEqual(del_resp.status_code, 204)

        # Act 4: Verify 404 after delete
        get_deleted_resp = self.auth_client.get(f"/api/patients/{patient.id}/")
        self.assertEqual(get_deleted_resp.status_code, 404)

    @patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-secret-session-token-32-chars-long"})
    def test_appointment_detail_and_list_all_api(self) -> None:
        # Arrange
        patient = services.register_patient("Monica Geller", "09172223344", 30)
        app = services.book_appointment(patient.id, "Dr. Richard", "2026-10-20")

        # Act 1: GET all appointments
        list_resp = self.auth_client.get("/api/appointments/")
        self.assertEqual(list_resp.status_code, 200)
        apps = list_resp.json()
        self.assertTrue(any(a["id"] == app.id for a in apps))

        # Act 2: GET single appointment detail
        detail_resp = self.auth_client.get(f"/api/appointments/{app.id}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.json()["doctor_name"], "Dr. Richard")

        # Act 3: PUT reschedule appointment
        put_payload = {"doctor_name": "Dr. Timothy", "app_date": "2026-10-25"}
        put_resp = self.auth_client.put(
            f"/api/appointments/{app.id}/",
            data=json.dumps(put_payload),
            content_type="application/json",
        )
        self.assertEqual(put_resp.status_code, 200)
        self.assertEqual(put_resp.json()["doctor_name"], "Dr. Timothy")
        self.assertEqual(put_resp.json()["app_date"], "2026-10-25")

        # Act 4: DELETE appointment
        del_resp = self.auth_client.delete(f"/api/appointments/{app.id}/")
        self.assertEqual(del_resp.status_code, 204)
        self.assertEqual(self.auth_client.get(f"/api/appointments/{app.id}/").status_code, 404)

    @patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "test-secret-session-token-32-chars-long"})
    def test_state_machine_transition_api_guards(self) -> None:
        # Arrange
        patient = services.register_patient("Chandler Bing", "09173334455", 32)
        app = services.book_appointment(patient.id, "Dr. Ross", "2026-11-01")

        # Complete the appointment
        self.auth_client.patch(
            f"/api/appointments/{app.id}/status/",
            data=json.dumps({"status": "Completed"}),
            content_type="application/json",
        )

        # Attempt to cancel completed appointment -> HTTP 400
        cancel_resp = self.auth_client.patch(
            f"/api/appointments/{app.id}/status/",
            data=json.dumps({"status": "Cancelled"}),
            content_type="application/json",
        )
        self.assertEqual(cancel_resp.status_code, 400)
        self.assertEqual(cancel_resp.json()["error"]["code"], "VALIDATION_ERROR")

        # Attempt to reschedule completed appointment -> HTTP 400
        reschedule_resp = self.auth_client.put(
            f"/api/appointments/{app.id}/",
            data=json.dumps({"doctor_name": "Dr. Joey", "app_date": "2026-11-05"}),
            content_type="application/json",
        )
        self.assertEqual(reschedule_resp.status_code, 400)
        self.assertEqual(reschedule_resp.json()["error"]["code"], "VALIDATION_ERROR")
