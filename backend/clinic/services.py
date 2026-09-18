"""Business logic service operations.

All operations execute inside database transactions, perform explicit validation,
and return strongly-typed model instances decoupled from HTTP requests.
"""

import secrets
from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from backend.clinic.models import (
    Appointment,
    AppointmentStatus,
    MedicalRecord,
    Patient,
    StaffRole,
    StaffUser,
    UserSession,
)


def register_patient(full_name: str, contact: str = "", age: int = 0) -> Patient:
    """Register a new patient with required name and positive age."""
    clean_name = (full_name or "").strip()
    clean_contact = (contact or "").strip()
    errors: dict[str, str] = {}

    if not clean_name:
        errors["full_name"] = "Full name is required."

    try:
        age_val = int(age)
        if age_val <= 0:
            raise ValueError
    except (ValueError, TypeError):
        errors["age"] = "Age must be a positive whole number greater than 0."
        age_val = 0

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        patient = Patient(full_name=clean_name, contact=clean_contact, age=age_val)
        patient.save()
        return patient


def list_patients(query: str | None = None) -> list[Patient]:
    """Return patients ordered by ID with precalculated appointment counts."""
    queryset = Patient.objects.annotate(
        appointment_count=Count("appointments"),
        active_appointment_count=Count(
            "appointments",
            filter=Q(
                appointments__status__in=[
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CHECKED_IN,
                    AppointmentStatus.IN_CONSULTATION,
                ]
            ),
        ),
    ).order_by("id")
    if query:
        clean_query = query.strip()
        if clean_query.isdigit():
            queryset = queryset.filter(Q(full_name__icontains=clean_query) | Q(id=int(clean_query)))
        else:
            queryset = queryset.filter(full_name__icontains=clean_query)
    return list(queryset)


def get_patient(patient_id: int) -> Patient:
    """Retrieve a single patient by ID with appointment count or raise Patient.DoesNotExist."""
    return Patient.objects.annotate(
        appointment_count=Count("appointments"),
        active_appointment_count=Count(
            "appointments",
            filter=Q(
                appointments__status__in=[
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CHECKED_IN,
                    AppointmentStatus.IN_CONSULTATION,
                ]
            ),
        ),
    ).get(id=patient_id)


def _parse_time(time_str: str) -> time:
    """Parse time string into a valid datetime.time object."""
    clean = (time_str or "").strip()
    if not clean:
        return time(9, 0)
    parts = clean.split(":")
    if len(parts) >= 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            return time(h, m, s)
        except (ValueError, TypeError):
            pass
    raise ValidationError({"app_time": f"Invalid time format '{clean}'. Use HH:MM format."})


def book_appointment(
    patient_id: int,
    doctor_name: str,
    app_date_str: str,
    app_time_str: str = "09:00",
    reason_for_visit: str = "",
    doctor_id: int | None = None,
    initial_status: str = AppointmentStatus.SCHEDULED,
) -> Appointment:
    """Book a new appointment with time slot, reason for visit, and optional doctor FK."""
    clean_doctor = (doctor_name or "").strip()
    clean_reason = (reason_for_visit or "").strip()
    clean_status = (initial_status or AppointmentStatus.SCHEDULED).strip()
    errors: dict[str, str] = {}

    assigned_doctor: StaffUser | None = None
    if doctor_id is not None:
        try:
            assigned_doctor = StaffUser.objects.get(id=doctor_id)
            if not clean_doctor:
                clean_doctor = assigned_doctor.full_name
        except StaffUser.DoesNotExist:
            errors["doctor_id"] = f"Doctor #{doctor_id} does not exist."

    if not clean_doctor:
        errors["doctor_name"] = "Doctor name is required."

    clean_date_str = (app_date_str or "").strip()
    parsed_date: date | None = None
    try:
        parsed_date = date.fromisoformat(clean_date_str)
    except (ValueError, TypeError):
        errors["app_date"] = "Date must be a valid ISO date in YYYY-MM-DD format."

    parsed_time: time = time(9, 0)
    try:
        parsed_time = _parse_time(app_time_str)
    except ValidationError:
        errors["app_time"] = "Time must be in HH:MM format (e.g. 09:30)."

    if clean_status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CHECKED_IN):
        errors["status"] = f"Initial status must be Scheduled or Checked In, not '{clean_status}'."

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        errors["patient_id"] = f"Patient #{patient_id} does not exist."
        patient = None

    if errors or parsed_date is None or patient is None:
        raise ValidationError(errors)

    with transaction.atomic():
        appointment = Appointment(
            patient=patient,
            doctor=assigned_doctor,
            doctor_name=clean_doctor,
            app_date=parsed_date,
            app_time=parsed_time,
            reason_for_visit=clean_reason,
            status=clean_status,
        )
        appointment.save()
        return appointment


def update_patient(patient_id: int, full_name: str, contact: str = "", age: int = 0) -> Patient:
    """Update patient details after validation."""
    clean_name = (full_name or "").strip()
    clean_contact = (contact or "").strip()
    errors: dict[str, str] = {}

    if not clean_name:
        errors["full_name"] = "Full name is required."

    try:
        age_val = int(age)
        if age_val <= 0:
            raise ValueError
    except (ValueError, TypeError):
        errors["age"] = "Age must be a positive whole number greater than 0."
        age_val = 0

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        patient = Patient.objects.select_for_update().get(id=patient_id)
        patient.full_name = clean_name
        patient.contact = clean_contact
        patient.age = age_val
        patient.save()
        return patient


def delete_patient(patient_id: int) -> tuple[int, dict[str, int]]:
    """Delete a patient record and cascade-delete associated appointments."""
    with transaction.atomic():
        patient = Patient.objects.select_for_update().get(id=patient_id)
        has_completed = Appointment.objects.filter(
            patient_id=patient_id, status=AppointmentStatus.COMPLETED
        ).exists()
        has_records = MedicalRecord.objects.filter(patient_id=patient_id).exists()
        if has_completed or has_records:
            raise ValidationError(
                {
                    "patient": (
                        "Cannot delete patient with finalized clinical history "
                        "(completed appointments or signed medical records exist)."
                    )
                }
            )
        return patient.delete()


def list_all_appointments() -> list[Appointment]:
    """Return all appointments ordered by ID descending with patient data pre-fetched."""
    return list(Appointment.objects.select_related("patient").order_by("-id"))


def list_patient_appointments(patient_id: int) -> list[Appointment]:
    """Return all appointments for a patient ordered by ID."""
    patient = Patient.objects.get(id=patient_id)
    return list(Appointment.objects.filter(patient=patient).order_by("id"))


def update_appointment(
    appointment_id: int,
    doctor_name: str | None = None,
    app_date_str: str | None = None,
    app_time_str: str | None = None,
    reason_for_visit: str | None = None,
    doctor_id: int | None = None,
) -> Appointment:
    """Update appointment details (rescheduling, time slot, or doctor reassignment)."""
    errors: dict[str, str] = {}

    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        if appointment.status == AppointmentStatus.COMPLETED:
            raise ValidationError(
                {
                    "appointment": "Completed appointments are finalized clinical records and cannot be rescheduled or modified."
                }
            )

        if doctor_id is not None:
            try:
                assigned_doctor = StaffUser.objects.get(id=doctor_id)
                appointment.doctor = assigned_doctor
                appointment.doctor_name = assigned_doctor.full_name
            except StaffUser.DoesNotExist:
                errors["doctor_id"] = f"Doctor #{doctor_id} does not exist."

        if doctor_name is not None:
            clean_doctor = doctor_name.strip()
            if not clean_doctor:
                errors["doctor_name"] = "Doctor name cannot be blank."
            else:
                appointment.doctor_name = clean_doctor

        if app_date_str is not None:
            try:
                appointment.app_date = date.fromisoformat(app_date_str.strip())
            except (ValueError, TypeError):
                errors["app_date"] = "Date must be a valid ISO date in YYYY-MM-DD format."

        if app_time_str is not None:
            try:
                appointment.app_time = _parse_time(app_time_str)
            except ValidationError:
                errors["app_time"] = "Time must be in HH:MM format (e.g. 09:30)."

        if reason_for_visit is not None:
            appointment.reason_for_visit = reason_for_visit.strip()

        if errors:
            raise ValidationError(errors)

        appointment.save()
        return appointment


def delete_appointment(appointment_id: int) -> tuple[int, dict[str, int]]:
    """Delete an appointment record."""
    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        if appointment.status == AppointmentStatus.COMPLETED:
            raise ValidationError(
                {
                    "appointment": "Completed appointments are immutable clinical records and cannot be deleted."
                }
            )
        return appointment.delete()


def update_appointment_status(appointment_id: int, new_status: str) -> Appointment:
    """Update an appointment status following the 5-state clinical lifecycle.

    State transitions:
    - Scheduled -> Checked In, Cancelled
    - Checked In -> In Consultation, Scheduled, Cancelled
    - In Consultation -> Completed, Checked In
    - Completed -> Immutable
    - Cancelled -> Scheduled
    """
    clean_status = (new_status or "").strip()
    if clean_status not in AppointmentStatus.values:
        raise ValidationError({"status": f"Invalid status '{clean_status}'."})

    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        current = appointment.status

        if current == clean_status:
            return appointment

        if current == AppointmentStatus.COMPLETED:
            raise ValidationError(
                {
                    "status": "Completed appointments are finalized clinical records and cannot be altered or cancelled."
                }
            )

        if current == AppointmentStatus.CANCELLED and clean_status != AppointmentStatus.SCHEDULED:
            raise ValidationError(
                {
                    "status": f"Cancelled appointments can only be restored to 'Scheduled', not directly to '{clean_status}'."
                }
            )

        if current == AppointmentStatus.IN_CONSULTATION and clean_status not in (
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CHECKED_IN,
        ):
            raise ValidationError(
                {
                    "status": f"In Consultation appointments can only transition to 'Completed' or 'Checked In', not '{clean_status}'."
                }
            )

        appointment.status = clean_status
        appointment.save()
        return appointment


# Staff Authentication and Profile Services


def register_staff(
    username: str,
    password: str,
    full_name: str,
    role: str = StaffRole.RECEPTIONIST,
    specialty: str = "",
    license_number: str = "",
    contact: str = "",
) -> StaffUser:
    """Register a new staff account with validated role and hashed password."""
    clean_username = (username or "").strip().lower()
    clean_name = (full_name or "").strip()
    clean_role = (role or "").strip().lower()
    clean_specialty = (specialty or "").strip()
    clean_license = (license_number or "").strip()
    clean_contact = (contact or "").strip()

    errors: dict[str, str] = {}

    if not clean_username:
        errors["username"] = "Username is required."
    elif StaffUser.objects.filter(username=clean_username).exists():
        errors["username"] = f"Username '{clean_username}' is already taken."

    if not clean_name:
        errors["full_name"] = "Full name is required."

    if clean_role not in StaffRole.values:
        errors["role"] = f"Invalid role '{clean_role}'. Must be receptionist or doctor."

    if not password or len(password) < 6:
        errors["password"] = "Password must be at least 6 characters long."

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        staff = StaffUser(
            username=clean_username,
            full_name=clean_name,
            role=clean_role,
            specialty=clean_specialty,
            license_number=clean_license,
            contact=clean_contact,
        )
        staff.set_password(password)
        staff.save()
        return staff


def authenticate_staff(username: str, password: str) -> tuple[StaffUser, UserSession]:
    """Verify credentials and issue a new secure session token."""
    clean_username = (username or "").strip().lower()
    if not clean_username or not password:
        raise ValidationError({"auth": "Username and password are required."})

    try:
        staff = StaffUser.objects.get(username=clean_username)
    except StaffUser.DoesNotExist:
        raise ValidationError({"auth": "Invalid username or password."}) from None

    if not staff.check_password(password):
        raise ValidationError({"auth": "Invalid username or password."})

    # Generate a cryptographically secure 64-character URL-safe session token
    token = secrets.token_urlsafe(48)

    with transaction.atomic():
        session = UserSession(token=token, user=staff)
        session.save()
        return staff, session


SESSION_MAX_INACTIVITY_HOURS = 24


def validate_session(token: str) -> StaffUser | None:
    """Validate a session token and enforce inactivity expiry."""
    clean_token = (token or "").strip()
    if not clean_token:
        return None

    try:
        session = UserSession.objects.select_related("user").get(token=clean_token)
        # Expire session if inactive for more than 24 hours
        if timezone.now() - session.last_active > timedelta(hours=SESSION_MAX_INACTIVITY_HOURS):
            session.delete()
            return None

        session.last_active = timezone.now()
        session.save(update_fields=["last_active"])
        return session.user
    except UserSession.DoesNotExist:
        return None


def logout_staff(token: str) -> bool:
    """Terminate an active session token."""
    clean_token = (token or "").strip()
    if not clean_token:
        return False

    with transaction.atomic():
        deleted_count, _ = UserSession.objects.filter(token=clean_token).delete()
        return deleted_count > 0


def update_staff_profile(
    user_id: int,
    full_name: str,
    contact: str = "",
    specialty: str = "",
    license_number: str = "",
    current_password: str | None = None,
    new_password: str | None = None,
) -> StaffUser:
    """Update staff profile information and optionally change password."""
    clean_name = (full_name or "").strip()
    clean_contact = (contact or "").strip()
    clean_specialty = (specialty or "").strip()
    clean_license = (license_number or "").strip()

    errors: dict[str, str] = {}
    if not clean_name:
        errors["full_name"] = "Full name is required."

    try:
        staff = StaffUser.objects.get(id=user_id)
    except StaffUser.DoesNotExist:
        raise ValidationError({"user": f"Staff user #{user_id} does not exist."}) from None

    if new_password:
        if not current_password:
            errors["current_password"] = "Current password is required to set a new password."
        elif not staff.check_password(current_password):
            errors["current_password"] = "Incorrect current password."
        elif len(new_password) < 6:
            errors["new_password"] = "New password must be at least 6 characters long."

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        staff.full_name = clean_name
        staff.contact = clean_contact
        staff.specialty = clean_specialty
        staff.license_number = clean_license
        if new_password:
            staff.set_password(new_password)
        staff.save()
        return staff


def list_doctors() -> list[StaffUser]:
    """Return all registered physician accounts ordered by full name."""
    return list(StaffUser.objects.filter(role=StaffRole.DOCTOR).order_by("full_name"))


# Clinical Logic, Conflict Engine, and Medical Records


def check_schedule_conflict(
    doctor_id: int,
    app_date: date,
    app_time: time,
    slot_duration_minutes: int = 15,
    exclude_id: int | None = None,
) -> list[Appointment]:
    """Find active appointments for a doctor within the slot duration window."""
    active_statuses = [
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.IN_CONSULTATION,
    ]
    qs = Appointment.objects.select_related("patient").filter(
        doctor_id=doctor_id,
        app_date=app_date,
        status__in=active_statuses,
    )
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)

    conflicts: list[Appointment] = []
    target_minutes = app_time.hour * 60 + app_time.minute
    for appt in qs:
        appt_minutes = appt.app_time.hour * 60 + appt.app_time.minute
        if abs(appt_minutes - target_minutes) < slot_duration_minutes:
            conflicts.append(appt)

    return conflicts


def create_medical_record(
    patient_id: int,
    doctor_id: int,
    diagnosis: str,
    symptoms: str = "",
    clinical_notes: str = "",
    prescription: str = "",
    follow_up_advice: str = "",
    appointment_id: int | None = None,
) -> MedicalRecord:
    """Create a clinical medical record and finalize the associated appointment."""
    clean_diagnosis = (diagnosis or "").strip()
    if not clean_diagnosis:
        raise ValidationError({"diagnosis": "Primary diagnosis is required."})

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        raise ValidationError({"patient_id": f"Patient #{patient_id} does not exist."}) from None

    try:
        doctor = StaffUser.objects.get(id=doctor_id)
        if doctor.role != StaffRole.DOCTOR:
            raise ValidationError(
                {"doctor_id": "Only registered doctors can author medical records."}
            )
    except StaffUser.DoesNotExist:
        raise ValidationError({"doctor_id": f"Doctor #{doctor_id} does not exist."}) from None

    appointment: Appointment | None = None
    if appointment_id is not None:
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ValidationError(
                {"appointment_id": f"Appointment #{appointment_id} does not exist."}
            ) from None

    with transaction.atomic():
        record = MedicalRecord(
            patient=patient,
            doctor=doctor,
            appointment=appointment,
            diagnosis=clean_diagnosis,
            symptoms=(symptoms or "").strip(),
            clinical_notes=(clinical_notes or "").strip(),
            prescription=(prescription or "").strip(),
            follow_up_advice=(follow_up_advice or "").strip(),
        )
        record.save()

        # Finalize the linked appointment if present
        if appointment and appointment.status != AppointmentStatus.COMPLETED:
            appointment.status = AppointmentStatus.COMPLETED
            appointment.save(update_fields=["status"])

        return record


def get_patient_medical_history(patient_id: int) -> list[MedicalRecord]:
    """Return complete chronological clinical history for a patient."""
    return list(
        MedicalRecord.objects.select_related("doctor", "appointment")
        .filter(patient_id=patient_id)
        .order_by("-created_at", "-id")
    )


def update_medical_record(
    record_id: int,
    doctor_id: int,
    diagnosis: str,
    symptoms: str = "",
    clinical_notes: str = "",
    prescription: str = "",
    follow_up_advice: str = "",
) -> MedicalRecord:
    """Update clinical record with author-only restriction."""
    clean_diagnosis = (diagnosis or "").strip()
    if not clean_diagnosis:
        raise ValidationError({"diagnosis": "Primary diagnosis is required."})

    try:
        record = MedicalRecord.objects.select_related("doctor").get(id=record_id)
    except MedicalRecord.DoesNotExist:
        raise ValidationError({"record": f"Medical record #{record_id} does not exist."}) from None

    if record.doctor_id != doctor_id:
        raise ValidationError(
            {"doctor": "Only the authoring physician can edit this clinical record."}
        )

    with transaction.atomic():
        record.diagnosis = clean_diagnosis
        record.symptoms = (symptoms or "").strip()
        record.clinical_notes = (clinical_notes or "").strip()
        record.prescription = (prescription or "").strip()
        record.follow_up_advice = (follow_up_advice or "").strip()
        record.save()
        return record


def get_doctor_queue(
    doctor_id: int, target_date: date | None = None
) -> dict[str, list[Appointment]]:
    """Return today's doctor queue grouped by clinical status."""
    ref_date = target_date or date.today()
    base_qs = (
        Appointment.objects.select_related("patient")
        .filter(doctor_id=doctor_id, app_date=ref_date)
        .order_by("app_time", "id")
    )

    return {
        "checked_in": list(base_qs.filter(status=AppointmentStatus.CHECKED_IN)),
        "in_consultation": list(base_qs.filter(status=AppointmentStatus.IN_CONSULTATION)),
        "scheduled": list(base_qs.filter(status=AppointmentStatus.SCHEDULED)),
        "completed": list(base_qs.filter(status=AppointmentStatus.COMPLETED)),
    }


def get_doctor_patients(doctor_id: int, query: str | None = None) -> list[Patient]:
    """Return distinct patients seen by or scheduled with this doctor."""
    qs = (
        Patient.objects.filter(
            Q(appointments__doctor_id=doctor_id) | Q(medical_records__doctor_id=doctor_id)
        )
        .distinct()
        .annotate(
            appointment_count=Count("appointments"),
            doctor_appointment_count=Count(
                "appointments",
                filter=Q(appointments__doctor_id=doctor_id),
            ),
        )
        .order_by("full_name")
    )
    if query:
        clean_q = query.strip()
        if clean_q.isdigit():
            qs = qs.filter(Q(id=int(clean_q)) | Q(full_name__icontains=clean_q))
        else:
            qs = qs.filter(full_name__icontains=clean_q)
    return list(qs)
