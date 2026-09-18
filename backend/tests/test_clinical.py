"""Unit and integration tests for clinical services, conflict engine, and medical records."""

import json
import os
from datetime import date, time
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from backend.clinic.models import AppointmentStatus, StaffRole
from backend.clinic.services import (
    authenticate_staff,
    book_appointment,
    check_schedule_conflict,
    create_medical_record,
    get_doctor_patients,
    get_doctor_queue,
    get_patient_medical_history,
    register_patient,
    register_staff,
    update_appointment_status,
    update_medical_record,
)


class ScheduleConflictEngineTests(TestCase):
    """Tests for doctor appointment schedule conflict detection."""

    def setUp(self) -> None:
        self.doctor = register_staff(
            username="dr.conflict",
            password="password123",
            full_name="Dr. Gregory Conflict",
            role=StaffRole.DOCTOR,
            specialty="Internal Medicine",
        )
        self.patient1 = register_patient("Conflict Patient 1", "09171110001", 30)
        self.patient2 = register_patient("Conflict Patient 2", "09171110002", 40)

    def test_conflict_detected_within_time_window(self) -> None:
        # Book initial appointment at 10:00
        book_appointment(
            patient_id=self.patient1.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-01",
            app_time_str="10:00",
            doctor_id=self.doctor.id,
        )

        # Check exact same time
        conflicts_exact = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(10, 0),
            slot_duration_minutes=15,
        )
        self.assertEqual(len(conflicts_exact), 1)

        # Check 10 minutes later (overlaps with 15 min slot)
        conflicts_overlap = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(10, 10),
            slot_duration_minutes=15,
        )
        self.assertEqual(len(conflicts_overlap), 1)

        # Check 10 minutes earlier (overlaps with 15 min slot)
        conflicts_before = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(9, 50),
            slot_duration_minutes=15,
        )
        self.assertEqual(len(conflicts_before), 1)

        # Check 20 minutes later (no overlap for 15 min slot)
        conflicts_clear = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(10, 20),
            slot_duration_minutes=15,
        )
        self.assertEqual(len(conflicts_clear), 0)

    def test_no_conflict_different_doctor_or_date(self) -> None:
        other_doctor = register_staff(
            username="dr.other",
            password="password123",
            full_name="Dr. Other",
            role=StaffRole.DOCTOR,
        )
        book_appointment(
            patient_id=self.patient1.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-01",
            app_time_str="10:00",
            doctor_id=self.doctor.id,
        )

        # Same time, different doctor -> no conflict
        conflicts = check_schedule_conflict(
            doctor_id=other_doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(10, 0),
        )
        self.assertEqual(len(conflicts), 0)

        # Same doctor, different date -> no conflict
        conflicts_date = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 2),
            app_time=time(10, 0),
        )
        self.assertEqual(len(conflicts_date), 0)

    def test_no_conflict_completed_or_cancelled_appointments(self) -> None:
        appt = book_appointment(
            patient_id=self.patient1.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-01",
            app_time_str="10:00",
            doctor_id=self.doctor.id,
        )

        # Mark appointment as Cancelled
        update_appointment_status(appt.id, AppointmentStatus.CANCELLED)

        # Check same slot -> no conflict
        conflicts = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(10, 0),
        )
        self.assertEqual(len(conflicts), 0)

        # Restore to Scheduled, then move to Completed
        update_appointment_status(appt.id, AppointmentStatus.SCHEDULED)
        update_appointment_status(appt.id, AppointmentStatus.COMPLETED)

        # Check same slot -> no conflict
        conflicts_completed = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(10, 0),
        )
        self.assertEqual(len(conflicts_completed), 0)

    def test_exclude_id_ignores_self_during_rescheduling(self) -> None:
        appt = book_appointment(
            patient_id=self.patient1.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-01",
            app_time_str="10:00",
            doctor_id=self.doctor.id,
        )

        # When updating this appointment to same time, exclude_id ensures no false conflict
        conflicts = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(10, 0),
            exclude_id=appt.id,
        )
        self.assertEqual(len(conflicts), 0)

    def test_conflict_detected_with_doctor_name_fallback(self) -> None:
        # Legacy appointment created without doctor foreign key
        book_appointment(
            patient_id=self.patient1.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-01",
            app_time_str="14:00",
            doctor_id=None,
        )

        conflicts = check_schedule_conflict(
            doctor_id=self.doctor.id,
            app_date=date(2026, 10, 1),
            app_time=time(14, 5),
            slot_duration_minutes=15,
        )
        self.assertEqual(len(conflicts), 1)


class ClinicalLifecycleAndQueueTests(TestCase):
    """Tests for 5-state lifecycle transitions and doctor queue triage."""

    def setUp(self) -> None:
        self.doctor = register_staff(
            username="dr.house",
            password="password123",
            full_name="Dr. Gregory House",
            role=StaffRole.DOCTOR,
            specialty="Diagnostics",
        )
        self.patient = register_patient("Lisa Cuddy", "09175550001", 42)

    def test_five_state_transitions(self) -> None:
        # 1. Scheduled -> Checked In (Waiting room arrival)
        appt = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-05",
            app_time_str="09:00",
            doctor_id=self.doctor.id,
        )
        self.assertEqual(appt.status, AppointmentStatus.SCHEDULED)

        checked_in = update_appointment_status(appt.id, AppointmentStatus.CHECKED_IN)
        self.assertEqual(checked_in.status, AppointmentStatus.CHECKED_IN)

        # 2. Checked In -> In Consultation (Doctor starts exam)
        in_consult = update_appointment_status(appt.id, AppointmentStatus.IN_CONSULTATION)
        self.assertEqual(in_consult.status, AppointmentStatus.IN_CONSULTATION)

        # 3. In Consultation -> Completed (Doctor finishes visit)
        completed = update_appointment_status(appt.id, AppointmentStatus.COMPLETED)
        self.assertEqual(completed.status, AppointmentStatus.COMPLETED)

        # 4. Completed is immutable
        with self.assertRaises(ValidationError):
            update_appointment_status(appt.id, AppointmentStatus.CANCELLED)

        with self.assertRaises(ValidationError):
            update_appointment_status(appt.id, AppointmentStatus.SCHEDULED)

    def test_scheduled_cannot_jump_to_in_consultation_directly(self) -> None:
        appt = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-05",
            app_time_str="11:00",
            doctor_id=self.doctor.id,
        )
        with self.assertRaises(ValidationError):
            update_appointment_status(appt.id, AppointmentStatus.IN_CONSULTATION)

    def test_checked_in_to_scheduled_reversion(self) -> None:
        # Patient checked in by mistake, front-desk reverts back to Scheduled
        appt = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-05",
            app_time_str="09:30",
            doctor_id=self.doctor.id,
            initial_status=AppointmentStatus.CHECKED_IN,
        )
        self.assertEqual(appt.status, AppointmentStatus.CHECKED_IN)

        reverted = update_appointment_status(appt.id, AppointmentStatus.SCHEDULED)
        self.assertEqual(reverted.status, AppointmentStatus.SCHEDULED)

    def test_in_consultation_to_checked_in_reversion(self) -> None:
        # Physician accidentally started consultation and returns patient to waiting queue
        appt = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-05",
            app_time_str="10:00",
            doctor_id=self.doctor.id,
        )
        update_appointment_status(appt.id, AppointmentStatus.CHECKED_IN)
        update_appointment_status(appt.id, AppointmentStatus.IN_CONSULTATION)

        reverted = update_appointment_status(appt.id, AppointmentStatus.CHECKED_IN)
        self.assertEqual(reverted.status, AppointmentStatus.CHECKED_IN)

    def test_doctor_queue_categorization(self) -> None:
        target_date = date(2026, 10, 5)
        # Create appointments in different states for target date
        a1 = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-05",
            app_time_str="09:00",
            doctor_id=self.doctor.id,
            initial_status=AppointmentStatus.CHECKED_IN,
        )
        a2 = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-05",
            app_time_str="09:30",
            doctor_id=self.doctor.id,
            initial_status=AppointmentStatus.SCHEDULED,
        )
        a3 = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-05",
            app_time_str="10:00",
            doctor_id=self.doctor.id,
        )
        update_appointment_status(a3.id, AppointmentStatus.CHECKED_IN)
        update_appointment_status(a3.id, AppointmentStatus.IN_CONSULTATION)

        queue = get_doctor_queue(doctor_id=self.doctor.id, target_date=target_date)
        self.assertEqual(len(queue["checked_in"]), 1)
        self.assertEqual(queue["checked_in"][0].id, a1.id)

        self.assertEqual(len(queue["in_consultation"]), 1)
        self.assertEqual(queue["in_consultation"][0].id, a3.id)

        self.assertEqual(len(queue["scheduled"]), 1)
        self.assertEqual(queue["scheduled"][0].id, a2.id)

    def test_get_doctor_patients_roster(self) -> None:
        p1 = register_patient("Roster Patient 1", "0917001", 25)
        p2 = register_patient("Roster Patient 2", "0917002", 35)
        p3 = register_patient("Unrelated Patient", "0917003", 45)

        book_appointment(
            patient_id=p1.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-06",
            app_time_str="09:00",
            doctor_id=self.doctor.id,
        )
        book_appointment(
            patient_id=p2.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-06",
            app_time_str="09:30",
            doctor_id=self.doctor.id,
        )

        roster = get_doctor_patients(doctor_id=self.doctor.id)
        roster_ids = [p.id for p in roster]
        self.assertIn(p1.id, roster_ids)
        self.assertIn(p2.id, roster_ids)
        self.assertNotIn(p3.id, roster_ids)

        # Search query within roster
        filtered = get_doctor_patients(doctor_id=self.doctor.id, query="Roster Patient 1")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, p1.id)


class MedicalRecordClinicalTests(TestCase):
    """Tests for clinical diagnosis and SOAP note authoring."""

    def setUp(self) -> None:
        self.doctor = register_staff(
            username="dr.watson",
            password="password123",
            full_name="Dr. John Watson",
            role=StaffRole.DOCTOR,
            specialty="General Medicine",
        )
        self.other_doctor = register_staff(
            username="dr.moriarty",
            password="password123",
            full_name="Dr. Jim Moriarty",
            role=StaffRole.DOCTOR,
            specialty="Forensics",
        )
        self.receptionist = register_staff(
            username="mrs.hudson",
            password="password123",
            full_name="Mrs. Martha Hudson",
            role=StaffRole.RECEPTIONIST,
        )
        self.patient = register_patient("Sherlock Holmes", "09172221100", 38)
        self.appt = book_appointment(
            patient_id=self.patient.id,
            doctor_name=self.doctor.full_name,
            app_date_str="2026-10-10",
            app_time_str="11:00",
            doctor_id=self.doctor.id,
        )

    def test_create_medical_record_success(self) -> None:
        record = create_medical_record(
            patient_id=self.patient.id,
            doctor_id=self.doctor.id,
            diagnosis="Acute Bronchitis",
            symptoms="Persistent dry cough, mild fever of 38.2C",
            clinical_notes="Chest auscultation reveals mild expiratory wheezing.",
            prescription="Amoxicillin 500mg TID for 7 days, Salbutamol inhaler PRN.",
            follow_up_advice="Return in 7 days if symptoms do not improve.",
            appointment_id=self.appt.id,
        )
        self.assertIsNotNone(record.id)
        self.assertEqual(record.diagnosis, "Acute Bronchitis")
        self.assertEqual(record.patient_id, self.patient.id)
        self.assertEqual(record.doctor_id, self.doctor.id)
        self.assertEqual(record.appointment_id, self.appt.id)

    def test_non_doctor_cannot_create_medical_record(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            create_medical_record(
                patient_id=self.patient.id,
                doctor_id=self.receptionist.id,
                diagnosis="Common Cold",
            )
        self.assertIn("doctor_id", ctx.exception.message_dict)

    def test_empty_diagnosis_rejected(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            create_medical_record(
                patient_id=self.patient.id,
                doctor_id=self.doctor.id,
                diagnosis="   ",
            )
        self.assertIn("diagnosis", ctx.exception.message_dict)

    def test_update_medical_record_by_authoring_physician(self) -> None:
        record = create_medical_record(
            patient_id=self.patient.id,
            doctor_id=self.doctor.id,
            diagnosis="Seasonal Allergies",
            symptoms="Sneezing, itchy eyes",
        )
        updated = update_medical_record(
            record_id=record.id,
            doctor_id=self.doctor.id,
            diagnosis="Allergic Rhinitis",
            prescription="Cetirizine 10mg once daily.",
        )
        self.assertEqual(updated.diagnosis, "Allergic Rhinitis")
        self.assertEqual(updated.prescription, "Cetirizine 10mg once daily.")

    def test_different_doctor_cannot_update_record(self) -> None:
        record = create_medical_record(
            patient_id=self.patient.id,
            doctor_id=self.doctor.id,
            diagnosis="Hypertension Stage 1",
        )
        with self.assertRaises(ValidationError) as ctx:
            update_medical_record(
                record_id=record.id,
                doctor_id=self.other_doctor.id,
                diagnosis="Updated diagnosis",
            )
        self.assertIn("doctor", ctx.exception.message_dict)

    def test_patient_medical_history_ordering(self) -> None:
        r1 = create_medical_record(
            patient_id=self.patient.id,
            doctor_id=self.doctor.id,
            diagnosis="First Visit Note",
        )
        r2 = create_medical_record(
            patient_id=self.patient.id,
            doctor_id=self.doctor.id,
            diagnosis="Second Visit Note",
        )
        history = get_patient_medical_history(patient_id=self.patient.id)
        self.assertEqual(len(history), 2)
        # Ordered by -created_at, -id
        self.assertEqual(history[0].id, r2.id)
        self.assertEqual(history[1].id, r1.id)

    def test_cannot_create_duplicate_medical_record_for_same_appointment(self) -> None:
        create_medical_record(
            patient_id=self.patient.id,
            doctor_id=self.doctor.id,
            diagnosis="Initial Diagnosis",
            appointment_id=self.appt.id,
        )
        with self.assertRaises(ValidationError):
            create_medical_record(
                patient_id=self.patient.id,
                doctor_id=self.doctor.id,
                diagnosis="Second Diagnosis",
                appointment_id=self.appt.id,
            )

    def test_cannot_create_medical_record_for_mismatched_patient_appointment(self) -> None:
        other_patient = register_patient("John Doe", "09170000000", 25)
        with self.assertRaises(ValidationError):
            create_medical_record(
                patient_id=other_patient.id,
                doctor_id=self.doctor.id,
                diagnosis="Mismatched Record",
                appointment_id=self.appt.id,
            )

    def test_inactive_doctor_cannot_author_medical_record(self) -> None:
        self.doctor.is_active = False
        self.doctor.save()
        with self.assertRaises(ValidationError):
            create_medical_record(
                patient_id=self.patient.id,
                doctor_id=self.doctor.id,
                diagnosis="Rejected Record",
            )


class ClinicalApiIntegrationTests(TestCase):
    """Integration tests for clinical REST API endpoints."""

    def setUp(self) -> None:
        self.session_token = "clinical-api-test-token"
        self.auth_client = Client(headers={"X-Session-Token": self.session_token})

        self.doctor = register_staff(
            username="dr.api",
            password="password123",
            full_name="Dr. API Physician",
            role=StaffRole.DOCTOR,
            specialty="Cardiology",
        )
        _, self.doc_session = authenticate_staff("dr.api", "password123")

        self.receptionist = register_staff(
            username="rec.api",
            password="password123",
            full_name="Receptionist API",
            role=StaffRole.RECEPTIONIST,
        )
        _, self.rec_session = authenticate_staff("rec.api", "password123")

        self.patient = register_patient("Clinical Patient", "09178889900", 50)

    def test_conflict_check_endpoint(self) -> None:
        with patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": self.session_token}):
            # Book an appointment
            book_appointment(
                patient_id=self.patient.id,
                doctor_name=self.doctor.full_name,
                app_date_str="2026-10-15",
                app_time_str="14:00",
                doctor_id=self.doctor.id,
            )

            # Query conflict check for conflicting time (14:10)
            resp = self.auth_client.get(
                reverse("api-appointment-conflict-check"),
                {"doctor_id": self.doctor.id, "date": "2026-10-15", "time": "14:10"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["has_conflict"])
            self.assertEqual(len(data["conflicts"]), 1)

            # Query conflict check for non-conflicting time (15:00)
            clear_resp = self.auth_client.get(
                reverse("api-appointment-conflict-check"),
                {"doctor_id": self.doctor.id, "date": "2026-10-15", "time": "15:00"},
            )
            self.assertEqual(clear_resp.status_code, 200)
            clear_data = clear_resp.json()
            self.assertFalse(clear_data["has_conflict"])
            self.assertEqual(len(clear_data["conflicts"]), 0)

    def test_doctor_queue_endpoint_authorization(self) -> None:
        with patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": self.session_token}):
            # Doctor client can access queue
            doc_client = Client(
                headers={
                    "X-Session-Token": self.session_token,
                    "X-User-Token": self.doc_session.token,
                }
            )
            doc_resp = doc_client.get(reverse("api-doctor-queue"))
            self.assertEqual(doc_resp.status_code, 200)
            self.assertIn("queue", doc_resp.json())

            # Receptionist client is forbidden from doctor queue (403)
            rec_client = Client(
                headers={
                    "X-Session-Token": self.session_token,
                    "X-User-Token": self.rec_session.token,
                }
            )
            rec_resp = rec_client.get(reverse("api-doctor-queue"))
            self.assertEqual(rec_resp.status_code, 403)

    def test_medical_records_crud_flow(self) -> None:
        with patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": self.session_token}):
            doc_client = Client(
                headers={
                    "X-Session-Token": self.session_token,
                    "X-User-Token": self.doc_session.token,
                }
            )

            # Create medical record via POST
            create_payload = {
                "patient_id": self.patient.id,
                "diagnosis": "Essential Hypertension",
                "symptoms": "Occasional morning headaches",
                "clinical_notes": "BP: 145/95 mmHg sitting.",
                "prescription": "Losartan 50mg once daily.",
                "follow_up_advice": "Low sodium diet, monitor BP log.",
            }
            create_resp = doc_client.post(
                reverse("api-medical-records"),
                data=json.dumps(create_payload),
                content_type="application/json",
            )
            self.assertEqual(create_resp.status_code, 201)
            record_data = create_resp.json()
            record_id = record_data["id"]
            self.assertEqual(record_data["diagnosis"], "Essential Hypertension")

            # Update medical record via PUT
            update_payload = {
                "diagnosis": "Essential Hypertension (Controlled)",
                "symptoms": "Headaches resolved",
                "clinical_notes": "BP: 125/80 mmHg.",
                "prescription": "Continue Losartan 50mg once daily.",
                "follow_up_advice": "Check in 3 months.",
            }
            update_resp = doc_client.put(
                reverse("api-medical-record-detail", kwargs={"record_id": record_id}),
                data=json.dumps(update_payload),
                content_type="application/json",
            )
            self.assertEqual(update_resp.status_code, 200)
            self.assertEqual(update_resp.json()["diagnosis"], "Essential Hypertension (Controlled)")

            # Fetch patient medical records without user token is rejected with 401
            unauth_resp = self.auth_client.get(
                reverse("api-patient-medical-records", kwargs={"patient_id": self.patient.id})
            )
            self.assertEqual(unauth_resp.status_code, 401)

            # Fetch patient medical records list with authenticated staff session
            history_resp = doc_client.get(
                reverse("api-patient-medical-records", kwargs={"patient_id": self.patient.id})
            )
            self.assertEqual(history_resp.status_code, 200)
            history = history_resp.json()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["id"], record_id)

            # Fetch single medical record detail via GET
            detail_resp = doc_client.get(
                reverse("api-medical-record-detail", kwargs={"record_id": record_id})
            )
            self.assertEqual(detail_resp.status_code, 200)
            self.assertEqual(detail_resp.json()["id"], record_id)
            self.assertEqual(detail_resp.json()["diagnosis"], "Essential Hypertension (Controlled)")
