"""Unit and integration tests for authentication, sessions, and staff services."""

import json
import os
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from backend.clinic.models import StaffRole, StaffUser
from backend.clinic.services import (
    authenticate_staff,
    list_doctors,
    logout_staff,
    register_staff,
    update_staff_profile,
    validate_session,
)


class StaffAuthServiceTests(TestCase):
    """Tests for pure Python authentication and profile service operations."""

    def test_register_staff_success(self) -> None:
        user = register_staff(
            username="nurse.joy",
            password="securepassword123",
            full_name="Nurse Joy",
            role=StaffRole.RECEPTIONIST,
            contact="09170001122",
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "nurse.joy")
        self.assertEqual(user.role, StaffRole.RECEPTIONIST)
        self.assertTrue(user.check_password("securepassword123"))

    def test_register_duplicate_username_fails(self) -> None:
        register_staff(
            username="dr.who",
            password="password123",
            full_name="Doctor Who",
            role=StaffRole.DOCTOR,
        )
        with self.assertRaises(ValidationError) as ctx:
            register_staff(
                username="dr.who",
                password="password123",
                full_name="Doctor Who Clone",
                role=StaffRole.DOCTOR,
            )
        self.assertIn("username", ctx.exception.message_dict)

    def test_authenticate_staff_issues_session(self) -> None:
        register_staff(
            username="dr.strange",
            password="magicpassword",
            full_name="Stephen Strange",
            role=StaffRole.DOCTOR,
            specialty="Neurosurgercy",
        )
        user, session = authenticate_staff(username="dr.strange", password="magicpassword")
        self.assertEqual(user.username, "dr.strange")
        self.assertEqual(len(session.token), 64)

        # Validate session retrieval
        active_user = validate_session(session.token)
        self.assertEqual(active_user, user)

    def test_authenticate_bad_password_fails(self) -> None:
        register_staff(
            username="dr.house",
            password="vicodinpassword",
            full_name="Gregory House",
            role=StaffRole.DOCTOR,
        )
        with self.assertRaises(ValidationError) as ctx:
            authenticate_staff(username="dr.house", password="wrongpassword")
        self.assertIn("auth", ctx.exception.message_dict)

    def test_logout_invalidates_session(self) -> None:
        register_staff(
            username="nurse.clara",
            password="password123",
            full_name="Clara Oswald",
            role=StaffRole.RECEPTIONIST,
        )
        _, session = authenticate_staff(username="nurse.clara", password="password123")
        token = session.token

        self.assertIsNotNone(validate_session(token))
        logged_out = logout_staff(token)
        self.assertTrue(logged_out)
        self.assertIsNone(validate_session(token))

    def test_validate_session_inactivity_timeout(self) -> None:
        register_staff(
            username="timed.out",
            password="password123",
            full_name="Timed Out User",
            role=StaffRole.RECEPTIONIST,
        )
        _, session = authenticate_staff("timed.out", "password123")
        # Artificially age session by 25 hours using QuerySet update (bypasses auto_now)
        from backend.clinic.models import UserSession

        UserSession.objects.filter(token=session.token).update(
            last_active=timezone.now() - timedelta(hours=25)
        )

        self.assertIsNone(validate_session(session.token))

    def test_update_profile_and_change_password(self) -> None:
        user = register_staff(
            username="dr.watson",
            password="initialpassword",
            full_name="John Watson",
            role=StaffRole.DOCTOR,
            specialty="General Medicine",
        )
        # Update name and contact without changing password
        updated = update_staff_profile(
            user_id=user.id,
            full_name="Dr. John H. Watson",
            contact="09199998877",
            specialty="Forensic Medicine",
        )
        self.assertEqual(updated.full_name, "Dr. John H. Watson")
        self.assertEqual(updated.specialty, "Forensic Medicine")
        self.assertTrue(updated.check_password("initialpassword"))

        # Update password
        updated_with_pwd = update_staff_profile(
            user_id=user.id,
            full_name="Dr. John H. Watson",
            current_password="initialpassword",
            new_password="newsecurepassword",
        )
        self.assertTrue(updated_with_pwd.check_password("newsecurepassword"))
        self.assertFalse(updated_with_pwd.check_password("initialpassword"))

    def test_list_doctors_filters_only_physicians(self) -> None:
        register_staff(
            username="rec1",
            password="password123",
            full_name="Receptionist One",
            role=StaffRole.RECEPTIONIST,
        )
        register_staff(
            username="doc1", password="password123", full_name="Dr. Alpha", role=StaffRole.DOCTOR
        )
        register_staff(
            username="doc2", password="password123", full_name="Dr. Beta", role=StaffRole.DOCTOR
        )

        doctors = list_doctors()
        self.assertEqual(len(doctors), 2)
        doctor_names = [d.full_name for d in doctors]
        self.assertIn("Dr. Alpha", doctor_names)
        self.assertIn("Dr. Beta", doctor_names)
        self.assertNotIn("Receptionist One", doctor_names)

    def test_inactive_staff_cannot_authenticate(self) -> None:
        user = register_staff(
            username="inactive.staff",
            password="password123",
            full_name="Inactive Staff Member",
            role=StaffRole.RECEPTIONIST,
        )
        user.is_active = False
        user.save()

        with self.assertRaises(ValidationError):
            authenticate_staff("inactive.staff", "password123")

    def test_validate_session_revokes_inactive_staff(self) -> None:
        user = register_staff(
            username="active.to.inactive",
            password="password123",
            full_name="Staff Soon Inactive",
            role=StaffRole.RECEPTIONIST,
        )
        _, session = authenticate_staff("active.to.inactive", "password123")
        self.assertIsNotNone(validate_session(session.token))

        # Deactivate user
        user.is_active = False
        user.save()

        # Next validation must reject and revoke the session
        self.assertIsNone(validate_session(session.token))

    def test_inactive_doctor_excluded_from_list_doctors(self) -> None:
        doc = register_staff(
            username="doc.inactive",
            password="password123",
            full_name="Dr. Retired",
            role=StaffRole.DOCTOR,
        )
        self.assertTrue(any(d.id == doc.id for d in list_doctors()))

        doc.is_active = False
        doc.save()

        self.assertFalse(any(d.id == doc.id for d in list_doctors()))


class StaffAuthApiTests(TestCase):
    """Integration tests for authentication and profile REST endpoints."""

    def setUp(self) -> None:
        self.session_token = "valid-loopback-desktop-test-token"
        self.auth_client = Client(headers={"X-Session-Token": self.session_token})

    def test_register_and_login_api_flow(self) -> None:
        with patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": self.session_token}):
            # Register staff via API
            register_payload = {
                "username": "api.receptionist",
                "password": "apipassword123",
                "full_name": "API Frontdesk",
                "role": "receptionist",
                "contact": "09171239999",
            }
            reg_response = self.auth_client.post(
                reverse("api-auth-register"),
                data=json.dumps(register_payload),
                content_type="application/json",
            )
            self.assertEqual(reg_response.status_code, 201)
            reg_data = reg_response.json()
            self.assertEqual(reg_data["username"], "api.receptionist")

            # Login via API
            login_payload = {
                "username": "api.receptionist",
                "password": "apipassword123",
            }
            login_response = self.auth_client.post(
                reverse("api-auth-login"),
                data=json.dumps(login_payload),
                content_type="application/json",
            )
            self.assertEqual(login_response.status_code, 200)
            login_data = login_response.json()
            self.assertIn("token", login_data)
            user_token = login_data["token"]

            # Query /api/auth/me/ with user session token
            user_client = Client(
                headers={
                    "X-Session-Token": self.session_token,
                    "X-User-Token": user_token,
                }
            )
            me_response = user_client.get(reverse("api-auth-me"))
            self.assertEqual(me_response.status_code, 200)
            me_data = me_response.json()
            self.assertEqual(me_data["user"]["username"], "api.receptionist")

            # Update profile via PUT
            profile_payload = {
                "full_name": "Senior Frontdesk",
                "contact": "09179998888",
            }
            put_response = user_client.put(
                reverse("api-auth-profile"),
                data=json.dumps(profile_payload),
                content_type="application/json",
            )
            self.assertEqual(put_response.status_code, 200)
            put_data = put_response.json()
            self.assertEqual(put_data["user"]["full_name"], "Senior Frontdesk")

            # Logout
            logout_response = user_client.post(reverse("api-auth-logout"))
            self.assertEqual(logout_response.status_code, 200)

            # Re-query /api/auth/me/ -> must return 401
            unauth_response = user_client.get(reverse("api-auth-me"))
            self.assertEqual(unauth_response.status_code, 401)

    def test_doctors_collection_api(self) -> None:
        StaffUser.objects.create(
            username="doc.pedro",
            full_name="Dr. Pedro Gil",
            role=StaffRole.DOCTOR,
            specialty="Pediatrics",
            password_hash="dummy",
        )
        with patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": self.session_token}):
            response = self.auth_client.get(reverse("api-doctors"))
            self.assertEqual(response.status_code, 200)
            doctors = response.json()
            self.assertTrue(len(doctors) >= 1)
            self.assertEqual(doctors[0]["full_name"], "Dr. Pedro Gil")
            self.assertEqual(doctors[0]["specialty"], "Pediatrics")
