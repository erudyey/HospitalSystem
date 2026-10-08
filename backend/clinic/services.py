"""Business logic service operations.

All operations execute inside database transactions, perform explicit validation,
and return strongly-typed model instances decoupled from HTTP requests.
"""

import os
import secrets
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from backend.clinic.models import (
    Appointment,
    AppointmentAudit,
    AppointmentStatus,
    DemoSeedState,
    MedicalRecord,
    MedicalRecordRevision,
    Patient,
    StaffRole,
    StaffUser,
    UserSession,
)


def clinic_timezone():
    """Return the configured clinic timezone or the workstation local timezone."""
    configured = os.environ.get("HOSPITAL_TIME_ZONE", "").strip()
    if configured:
        try:
            return ZoneInfo(configured)
        except ZoneInfoNotFoundError:
            pass
    return datetime.now().astimezone().tzinfo


def clinic_now() -> datetime:
    """Return the current clinic-local wall time."""
    return datetime.now(clinic_timezone())


def clinic_context() -> dict[str, str]:
    tz = clinic_timezone()
    return {"timezone": getattr(tz, "key", None) or str(tz), "now": clinic_now().isoformat()}


def get_daily_report(user: StaffUser, date_str: str | None = None) -> dict[str, Any]:
    """Summarize a date's current schedule within the authenticated staff scope."""
    now = clinic_now()
    target_date = now.date()
    if date_str is not None:
        try:
            target_date = date.fromisoformat(date_str)
            if target_date.isoformat() != date_str:
                raise ValueError
        except (ValueError, TypeError) as exc:
            raise ValidationError({"date": "Choose a valid date in YYYY-MM-DD format."}) from exc

    if not user.is_active or user.role not in (StaffRole.RECEPTIONIST, StaffRole.DOCTOR):
        raise ValidationError({"auth": "An active receptionist or doctor account is required."})

    appointments = Appointment.objects.filter(app_date=target_date)
    if user.role == StaffRole.DOCTOR:
        appointments = appointments.filter(doctor_id=user.id)
    status_keys = {
        AppointmentStatus.SCHEDULED: "scheduled",
        AppointmentStatus.CHECKED_IN: "checked_in",
        AppointmentStatus.IN_CONSULTATION: "in_consultation",
        AppointmentStatus.COMPLETED: "completed",
        AppointmentStatus.CANCELLED: "cancelled",
    }

    def counters() -> dict[str, int]:
        return dict.fromkeys(["appointments", "patients", *status_keys.values()], 0)

    totals = counters()
    doctors: dict[int | None, dict[str, Any]] = {}
    patients: set[int] = set()
    doctor_patients: dict[int | None, set[int]] = {}
    # One query keeps every subtotal within the same schedule snapshot.
    for row in appointments.values("doctor_id", "doctor__full_name", "patient_id", "status"):
        doctor_id = row["doctor_id"]
        if doctor_id not in doctors:
            doctors[doctor_id] = {
                "doctor_id": doctor_id,
                "doctor_name": row["doctor__full_name"] or "Unassigned",
                **counters(),
            }
            doctor_patients[doctor_id] = set()
        patients.add(row["patient_id"])
        doctor_patients[doctor_id].add(row["patient_id"])
        key = status_keys[row["status"]]
        totals["appointments"] += 1
        totals[key] += 1
        doctors[doctor_id]["appointments"] += 1
        doctors[doctor_id][key] += 1
    totals["patients"] = len(patients)
    for doctor_id, patient_ids in doctor_patients.items():
        doctors[doctor_id]["patients"] = len(patient_ids)
    return {
        "date": target_date.isoformat(),
        "generated_at": now.isoformat(),
        "mode": "demo" if os.environ.get("HOSPITAL_MODE") == "demo" else "clinic",
        "scope": "doctor" if user.role == StaffRole.DOCTOR else "clinic",
        "totals": totals,
        "doctors": sorted(
            doctors.values(),
            key=lambda doctor: (doctor["doctor_name"].casefold(), doctor["doctor_id"] or 0),
        ),
    }


def _appointment_snapshot(appointment: Appointment) -> dict[str, str | int | None]:
    return {
        "doctor_id": appointment.doctor_id,
        "doctor_name": appointment.doctor_name,
        "app_date": appointment.app_date.isoformat(),
        "app_time": appointment.app_time.strftime("%H:%M"),
        "reason_for_visit": appointment.reason_for_visit,
        "status": appointment.status,
        "checked_in_at": appointment.checked_in_at.isoformat()
        if appointment.checked_in_at
        else None,
    }


def _audit(
    appointment: Appointment, event: str, actor_id: int | None, reason: str = "", before=None
) -> None:
    AppointmentAudit.objects.create(
        appointment=appointment,
        actor_id=actor_id,
        event=event,
        reason=reason,
        before=before or {},
        after=_appointment_snapshot(appointment),
    )


def _validate_future_slot(app_date: date, app_time: time) -> None:
    if datetime.combine(app_date, app_time, tzinfo=clinic_timezone()) <= clinic_now():
        raise ValidationError({"schedule": "Scheduled appointments must be in the future."})


def next_quarter_hour() -> datetime:
    """Return the next clinic-local fifteen-minute appointment boundary."""
    now = clinic_now().replace(second=0, microsecond=0)
    return now + timedelta(minutes=15 - (now.minute % 15))


def import_legacy_rows(
    patients: list[dict[str, Any]], appointments: list[dict[str, Any]]
) -> tuple[int, int]:
    """Import validated legacy IDs only into an empty clinical database."""
    with transaction.atomic():
        if (
            Patient.objects.exists()
            or Appointment.objects.exists()
            or MedicalRecord.objects.exists()
        ):
            raise ValidationError(
                {
                    "database": "Legacy import requires an empty clinical database. Existing records were preserved."
                }
            )
        for row in patients:
            Patient.objects.create(**row)
        for row in appointments:
            Appointment.objects.create(**row)
        return len(patients), len(appointments)


def seed_sample_rows(rows: list[dict[str, Any]], clear: bool = False) -> tuple[int, int]:
    """Write sample fixtures atomically, never into a production clinic database."""
    if not (settings.DEBUG or settings.IS_TESTING):
        raise ValidationError(
            {"database": "Sample seeding is restricted to development and test databases."}
        )
    with transaction.atomic():
        if Patient.objects.exists() and not clear:
            return 0, 0
        if clear:
            MedicalRecord.objects.all().delete()
            Appointment.objects.all().delete()
            Patient.objects.all().delete()
        appointment_count = 0
        for row in rows:
            patient = Patient.objects.create(
                full_name=row["full_name"], contact=row["contact"], age=row["age"]
            )
            for appointment in row["appointments"]:
                Appointment.objects.create(patient=patient, **appointment)
                appointment_count += 1
        return len(rows), appointment_count


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
    allow_conflict: bool = False,
    override_reason: str = "",
    override_by_id: int | None = None,
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
            if assigned_doctor.role != StaffRole.DOCTOR or not assigned_doctor.is_active:
                errors["doctor_id"] = "Appointment doctor must be an active physician."
            clean_doctor = assigned_doctor.full_name
        except StaffUser.DoesNotExist:
            errors["doctor_id"] = f"Doctor #{doctor_id} does not exist."

    elif not clean_doctor:
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

    if clean_status == AppointmentStatus.CHECKED_IN and parsed_date != clinic_now().date():
        errors["app_date"] = (
            "Patients can only check in for today's appointments. Reschedule the appointment to today first."
        )

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        errors["patient_id"] = f"Patient #{patient_id} does not exist."
        patient = None

    if clean_status == AppointmentStatus.SCHEDULED and parsed_date is not None:
        try:
            _validate_future_slot(parsed_date, parsed_time)
        except ValidationError as exc:
            for field, messages in exc.message_dict.items():
                errors[field] = " ".join(messages)
    if errors or parsed_date is None or patient is None:
        raise ValidationError(errors)

    clean_override_reason = (override_reason or "").strip()
    if allow_conflict and (not clean_override_reason or len(clean_override_reason) > 255):
        errors["override_reason"] = "An override reason of at most 255 characters is required."
    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        if assigned_doctor is not None:
            conflicts = check_schedule_conflict(
                assigned_doctor.id,
                parsed_date,
                parsed_time,
            )
            if conflicts and not allow_conflict:
                raise ValidationError(
                    {
                        "schedule": "The selected physician already has an active appointment in this time window."
                    }
                )
        override_by = None
        if allow_conflict and override_by_id is not None:
            override_by = StaffUser.objects.filter(id=override_by_id).first()
        appointment = Appointment(
            patient=patient,
            doctor=assigned_doctor,
            doctor_name=clean_doctor,
            app_date=parsed_date,
            app_time=parsed_time,
            reason_for_visit=clean_reason,
            status=clean_status,
            checked_in_at=timezone.now() if clean_status == AppointmentStatus.CHECKED_IN else None,
            conflict_override_reason=clean_override_reason if allow_conflict else "",
            conflict_overridden_at=timezone.now() if allow_conflict else None,
            conflict_overridden_by=override_by,
        )
        appointment.save()
        _audit(
            appointment,
            "walk_in" if clean_status == AppointmentStatus.CHECKED_IN else "booked",
            override_by_id,
            clean_override_reason if allow_conflict else "",
        )
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
        has_protected_visits = Appointment.objects.filter(
            patient_id=patient_id,
            status__in=[AppointmentStatus.COMPLETED, AppointmentStatus.IN_CONSULTATION],
        ).exists()
        has_records = MedicalRecord.objects.filter(patient_id=patient_id).exists()
        if has_protected_visits or has_records:
            raise ValidationError(
                {
                    "patient": (
                        "Cannot delete patient with an active consultation or finalized clinical history."
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
    allow_conflict: bool = False,
    override_reason: str = "",
    override_by_id: int | None = None,
) -> Appointment:
    """Update appointment details (rescheduling, time slot, or doctor reassignment)."""
    errors: dict[str, str] = {}

    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        before = _appointment_snapshot(appointment)
        if appointment.status in (AppointmentStatus.COMPLETED, AppointmentStatus.IN_CONSULTATION):
            raise ValidationError(
                {
                    "appointment": "Completed or in-consultation appointments cannot be rescheduled or modified."
                }
            )

        if doctor_id is not None:
            try:
                assigned_doctor = StaffUser.objects.get(id=doctor_id)
                if assigned_doctor.role != StaffRole.DOCTOR or not assigned_doctor.is_active:
                    errors["doctor_id"] = "Appointment doctor must be an active physician."
                else:
                    appointment.doctor = assigned_doctor
                    appointment.doctor_name = assigned_doctor.full_name
            except StaffUser.DoesNotExist:
                errors["doctor_id"] = f"Doctor #{doctor_id} does not exist."

        if doctor_name is not None and doctor_id is None:
            clean_doctor = doctor_name.strip()
            if not clean_doctor:
                errors["doctor_name"] = "Doctor name cannot be blank."
            elif appointment.doctor_id and clean_doctor != appointment.doctor.full_name:
                errors["doctor_id"] = "Select a registered physician to reassign this appointment."
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
            if not isinstance(reason_for_visit, str):
                errors["reason_for_visit"] = "Reason for visit must be a string."
            else:
                appointment.reason_for_visit = reason_for_visit.strip()

        if errors:
            raise ValidationError(errors)

        after = _appointment_snapshot(appointment)
        schedule_changed = any(
            before[field] != after[field] for field in ("doctor_id", "app_date", "app_time")
        ) or (appointment.doctor_id is None and before["doctor_name"] != after["doctor_name"])
        if appointment.status != AppointmentStatus.CANCELLED and (
            schedule_changed or appointment.status == AppointmentStatus.SCHEDULED
        ):
            _validate_future_slot(appointment.app_date, appointment.app_time)

        clean_override_reason = (override_reason or "").strip()
        conflicts = []
        if schedule_changed and appointment.doctor_id is not None:
            conflicts = check_schedule_conflict(
                appointment.doctor_id,
                appointment.app_date,
                appointment.app_time,
                exclude_id=appointment.id,
            )
        if conflicts and not allow_conflict:
            raise ValidationError(
                {
                    "schedule": "The selected physician already has an active appointment in this time window."
                }
            )
        if allow_conflict and (not clean_override_reason or len(clean_override_reason) > 255):
            raise ValidationError(
                {"override_reason": "An override reason of at most 255 characters is required."}
            )
        if allow_conflict:
            appointment.conflict_override_reason = clean_override_reason
            appointment.conflict_overridden_at = timezone.now()
            appointment.conflict_overridden_by_id = override_by_id
        if schedule_changed and before["status"] == AppointmentStatus.CHECKED_IN:
            appointment.status = AppointmentStatus.SCHEDULED
            appointment.checked_in_at = None
        appointment.save()
        _audit(
            appointment,
            "rescheduled" if schedule_changed else "updated",
            override_by_id,
            clean_override_reason if allow_conflict else "",
            before,
        )
        return appointment


def delete_appointment(appointment_id: int) -> tuple[int, dict[str, int]]:
    """Delete an appointment record."""
    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        if appointment.status in (AppointmentStatus.COMPLETED, AppointmentStatus.IN_CONSULTATION):
            raise ValidationError(
                {
                    "appointment": "Clinical appointments cannot be deleted while in consultation or after completion."
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

        if (
            clean_status == AppointmentStatus.CHECKED_IN
            and appointment.app_date != clinic_now().date()
        ):
            raise ValidationError(
                {
                    "app_date": "Patients can only check in for today's appointments. Reschedule the appointment to today first."
                }
            )

        if clean_status == AppointmentStatus.SCHEDULED:
            _validate_future_slot(appointment.app_date, appointment.app_time)
            if appointment.doctor_id and check_schedule_conflict(
                appointment.doctor_id,
                appointment.app_date,
                appointment.app_time,
                exclude_id=appointment.id,
            ):
                raise ValidationError(
                    {
                        "schedule": "The doctor already has an overlapping appointment. Reschedule to an available slot."
                    }
                )

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

        if (
            current == AppointmentStatus.SCHEDULED
            and clean_status == AppointmentStatus.IN_CONSULTATION
        ):
            raise ValidationError(
                {
                    "status": "Scheduled appointments must be 'Checked In' before moving to 'In Consultation'."
                }
            )

        appointment.status = clean_status
        update_fields = ["status"]
        if clean_status in (AppointmentStatus.SCHEDULED, AppointmentStatus.CANCELLED):
            appointment.checked_in_at = None
            update_fields.append("checked_in_at")
        if clean_status == AppointmentStatus.CHECKED_IN and appointment.checked_in_at is None:
            appointment.checked_in_at = timezone.now()
            update_fields.append("checked_in_at")
        appointment.save(update_fields=update_fields)
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
    elif len(clean_username) > 50:
        errors["username"] = "Username must be at most 50 characters long."
    elif StaffUser.objects.filter(username__iexact=clean_username).exists():
        errors["username"] = f"Username '{clean_username}' is already taken."

    if not clean_name:
        errors["full_name"] = "Full name is required."

    if clean_role not in StaffRole.values:
        errors["role"] = f"Invalid role '{clean_role}'. Must be receptionist or doctor."

    if not password or len(password) < 6:
        errors["password"] = "Password must be at least 6 characters long."

    if errors:
        raise ValidationError(errors)

    try:
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
    except IntegrityError as exc:
        raise ValidationError({"username": "This username is already taken."}) from exc


def bootstrap_receptionist(**kwargs) -> StaffUser:
    """Create the sole initial receptionist, never reopening public registration."""
    with transaction.atomic():
        if StaffUser.objects.exists():
            raise ValidationError({"registration": "Initial setup has already been completed."})
        if kwargs.get("role", StaffRole.RECEPTIONIST) != StaffRole.RECEPTIONIST:
            raise ValidationError({"role": "The initial account must be a receptionist."})
        return register_staff(**kwargs)


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

    if not staff.is_active:
        raise ValidationError({"auth": "This staff account is inactive."})

    # Prune expired sessions older than 24 hours
    cutoff = timezone.now() - timedelta(hours=SESSION_MAX_INACTIVITY_HOURS)
    UserSession.objects.filter(last_active__lt=cutoff).delete()

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

        if not session.user.is_active:
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


def rotate_session(token: str, user: StaffUser) -> UserSession:
    """Replace the current session after a credential change."""
    with transaction.atomic():
        if token:
            UserSession.objects.filter(token=token, user=user).delete()
        session = UserSession(token=secrets.token_urlsafe(48), user=user)
        session.save()
        return session


def update_staff_profile(
    user_id: int,
    full_name: str,
    contact: str = "",
    specialty: str = "",
    license_number: str = "",
    current_password: str | None = None,
    new_password: str | None = None,
    username: str | None = None,
    session_token: str | None = None,
) -> StaffUser:
    """Update staff profile information and optionally change password."""
    clean_name = (full_name or "").strip()
    clean_contact = (contact or "").strip()
    clean_specialty = (specialty or "").strip()
    clean_license = (license_number or "").strip()

    errors: dict[str, str] = {}
    if not clean_name:
        errors["full_name"] = "Full name is required."

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        try:
            staff = StaffUser.objects.select_for_update().get(id=user_id)
        except StaffUser.DoesNotExist:
            raise ValidationError({"user": f"Staff user #{user_id} does not exist."}) from None

        clean_username = staff.username if username is None else username.strip().lower()
        if not clean_username:
            errors["username"] = "Username is required."
        changing_credentials = bool(new_password) or clean_username != staff.username
        if changing_credentials:
            if not current_password:
                errors["current_password"] = "Current password is required to change credentials."
            elif not staff.check_password(current_password):
                errors["current_password"] = "Incorrect current password."
            elif new_password and len(new_password) < 6:
                errors["new_password"] = "New password must be at least 6 characters long."
            elif len(clean_username) > 50:
                errors["username"] = "Username must be at most 50 characters long."
            elif (
                StaffUser.objects.filter(username__iexact=clean_username)
                .exclude(id=staff.id)
                .exists()
            ):
                errors["username"] = "This username is already taken."

        if errors:
            raise ValidationError(errors)

        staff.full_name = clean_name
        staff.contact = clean_contact
        staff.specialty = clean_specialty
        staff.license_number = clean_license
        staff.username = clean_username
        if new_password:
            staff.set_password(new_password)
        staff.save()
        if changing_credentials:
            UserSession.objects.filter(user=staff).exclude(token=session_token or "").delete()
        return staff


def list_doctors() -> list[StaffUser]:
    """Return all active registered physician accounts ordered by full name."""
    return list(
        StaffUser.objects.filter(role=StaffRole.DOCTOR, is_active=True).order_by("full_name")
    )


DEFAULT_STAFF_ACCOUNTS: list[dict[str, str]] = [
    {
        "username": "maria",
        "password": "password123",
        "full_name": "Maria Santos",
        "role": StaffRole.RECEPTIONIST,
        "specialty": "",
        "license_number": "",
        "contact": "09171234567",
    },
    {
        "username": "dreyes",
        "password": "password123",
        "full_name": "Dr. Elena Reyes",
        "role": StaffRole.DOCTOR,
        "specialty": "General Medicine",
        "license_number": "PRC-018245",
        "contact": "09181234567",
    },
    {
        "username": "dsantos",
        "password": "password123",
        "full_name": "Dr. Marco Santos",
        "role": StaffRole.DOCTOR,
        "specialty": "Pediatrics",
        "license_number": "PRC-019382",
        "contact": "09201234567",
    },
    {
        "username": "dtan",
        "password": "password123",
        "full_name": "Dr. Chloe Tan",
        "role": StaffRole.DOCTOR,
        "specialty": "Cardiology",
        "license_number": "PRC-020491",
        "contact": "09221234567",
    },
]


DEMO_SEED_VERSION = 1


def ensure_demo_data() -> None:
    """Create versioned sample data once in the separate demo database.

    Existing unversioned clinical data is deliberately retained. Reset is an explicit
    user operation, never a side effect of opening demo mode.
    """
    if os.environ.get("HOSPITAL_MODE") != "demo":
        raise ValidationError({"mode": "Demo fixtures can only be seeded in demo mode."})
    with transaction.atomic():
        state = DemoSeedState.objects.filter(key="default").first()
        if state and state.version >= DEMO_SEED_VERSION:
            return
        staff = (
            list(StaffUser.objects.filter(id__in=state.account_ids.values()))
            if state and state.account_ids
            else ensure_default_staff()
        )
        if not state and (Patient.objects.exists() or Appointment.objects.exists()):
            DemoSeedState.objects.create(
                key="default",
                version=DEMO_SEED_VERSION,
                account_ids={user.username: user.id for user in staff},
            )
            return
        patients = []
        names = [
            "Alex Rivera",
            "Jamie Lim",
            "Morgan Cruz",
            "Taylor Reyes",
            "Casey Flores",
            "Avery Santos",
            "Riley Garcia",
            "Jordan Tan",
            "Parker Diaz",
            "Quinn Ramos",
            "Skyler Navarro",
            "Drew Torres",
            "Cameron Aquino",
            "Emerson Go",
            "Finley Chua",
            "Hayden Ong",
            "Rowan Bautista",
            "Sage Villanueva",
        ]
        for index, name in enumerate(names, start=1):
            patients.append(
                Patient.objects.create(
                    full_name=name, contact=f"0917000{index:04d}", age=18 + index
                )
            )
        doctors = [user for user in staff if user.role == StaffRole.DOCTOR]
        statuses = [
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_CONSULTATION,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
        ]
        anchor = clinic_now().date()
        for index in range(24):
            status = statuses[index % len(statuses)]
            doctor = doctors[index % len(doctors)]
            slot = next_quarter_hour() + timedelta(minutes=30 * index)
            day = anchor
            app_time = time(9 + (index % 6), (index // 3 % 4) * 15)
            if status == AppointmentStatus.SCHEDULED:
                day, app_time = slot.date(), slot.time().replace(tzinfo=None)
            elif status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
                day = anchor - timedelta(days=1 + index % 8)
            appointment = Appointment.objects.create(
                patient=patients[index % len(patients)],
                doctor=doctor,
                doctor_name=doctor.full_name,
                app_date=day,
                app_time=app_time,
                reason_for_visit="Sample consultation",
                status=status,
                checked_in_at=timezone.now()
                if status
                in (
                    AppointmentStatus.CHECKED_IN,
                    AppointmentStatus.IN_CONSULTATION,
                    AppointmentStatus.COMPLETED,
                )
                else None,
            )
            if status == AppointmentStatus.COMPLETED:
                record = MedicalRecord.objects.create(
                    patient=appointment.patient,
                    doctor=doctor,
                    appointment=appointment,
                    diagnosis="Sample follow-up",
                    clinical_notes="Demo clinical history.",
                )
                MedicalRecordRevision.objects.create(
                    record=record,
                    revision=1,
                    correction_reason="Initial demo record",
                    diagnosis=record.diagnosis,
                    symptoms="",
                    clinical_notes=record.clinical_notes,
                    prescription="",
                    follow_up_advice="",
                    changed_by=doctor,
                )
        DemoSeedState.objects.update_or_create(
            key="default",
            defaults={
                "version": DEMO_SEED_VERSION,
                "account_ids": {u.username: u.id for u in staff},
            },
        )


def reset_demo_data() -> None:
    """Reset demo clinical fixtures explicitly while retaining staff profiles."""
    if os.environ.get("HOSPITAL_MODE") != "demo":
        raise ValidationError({"mode": "Demo reset is unavailable in clinic mode."})
    with transaction.atomic():
        state = DemoSeedState.objects.filter(key="default").first()
        account_ids = state.account_ids if state else {}
        MedicalRecord.objects.all().delete()
        Appointment.objects.all().delete()
        Patient.objects.all().delete()
        UserSession.objects.all().delete()
        DemoSeedState.objects.update_or_create(
            key="default", defaults={"version": 0, "account_ids": account_ids}
        )
        ensure_demo_data()


def seed_clinical_samples(count: int = 15, clear: bool = False) -> dict[str, int]:
    """Create complete fixture encounters atomically in demo, development, or tests."""
    import random

    from backend.clinic.sample_data import (
        CLINICAL_CASES,
        CONTACTS,
        FIRST_NAMES,
        LAST_NAMES,
        REASONS,
    )

    if not (settings.DEBUG or settings.IS_TESTING or os.environ.get("HOSPITAL_MODE") == "demo"):
        raise ValidationError({"database": "Sample seeding is unavailable in clinic mode."})
    with transaction.atomic():
        if Patient.objects.exists() and not clear:
            return {"patients": 0, "appointments": 0, "records": 0}
        if clear:
            MedicalRecord.objects.all().delete()
            Appointment.objects.all().delete()
            Patient.objects.all().delete()
            UserSession.objects.all().delete()
        staff = ensure_default_staff()
        doctors = [user for user in staff if user.role == StaffRole.DOCTOR]
        rng = random.Random(42)
        record_count = 0
        for index in range(max(1, count)):
            patient = Patient.objects.create(
                full_name=rng.choice(FIRST_NAMES) + " " + rng.choice(LAST_NAMES),
                contact=rng.choice(CONTACTS),
                age=rng.randint(6, 82),
            )
            doctor = doctors[index % len(doctors)]
            status = [
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.COMPLETED,
                AppointmentStatus.CANCELLED,
            ][index % 5]
            slot = next_quarter_hour() + timedelta(minutes=30 * index)
            day = clinic_now().date()
            if status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
                day -= timedelta(days=1 + index % 10)
            elif status == AppointmentStatus.SCHEDULED:
                day = slot.date()
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                doctor_name=doctor.full_name,
                app_date=day,
                app_time=slot.time().replace(tzinfo=None),
                reason_for_visit=rng.choice(REASONS),
                status=status,
                checked_in_at=timezone.now()
                if status in (AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION)
                else None,
            )
            if status == AppointmentStatus.COMPLETED:
                record = MedicalRecord.objects.create(
                    patient=patient,
                    doctor=doctor,
                    appointment=appointment,
                    **rng.choice(CLINICAL_CASES),
                )
                MedicalRecordRevision.objects.create(
                    record=record,
                    revision=1,
                    correction_reason="Initial sample record",
                    diagnosis=record.diagnosis,
                    symptoms=record.symptoms,
                    clinical_notes=record.clinical_notes,
                    prescription=record.prescription,
                    follow_up_advice=record.follow_up_advice,
                    changed_by=doctor,
                )
                record_count += 1
        if os.environ.get("HOSPITAL_MODE") == "demo":
            DemoSeedState.objects.update_or_create(
                key="default",
                defaults={
                    "version": DEMO_SEED_VERSION,
                    "account_ids": {user.username: user.id for user in staff},
                },
            )
        return {"patients": max(1, count), "appointments": max(1, count), "records": record_count}


def list_demo_accounts() -> list[StaffUser]:
    """Return active fixture accounts by their persistent seeded IDs."""
    if os.environ.get("HOSPITAL_MODE") != "demo":
        raise ValidationError({"mode": "Demo accounts are only available in demo mode."})
    state = DemoSeedState.objects.filter(key="default").first()
    if state is None:
        return []
    ids = [value for value in state.account_ids.values() if isinstance(value, int)]
    return list(StaffUser.objects.filter(id__in=ids, is_active=True).order_by("role", "full_name"))


def authenticate_demo_account(
    account_id: int, previous_token: str = ""
) -> tuple[StaffUser, UserSession]:
    """Issue an in-memory demo session for a seeded account without credentials."""
    accounts = {account.id: account for account in list_demo_accounts()}
    staff = accounts.get(account_id)
    if staff is None:
        raise ValidationError({"account_id": "This demo account is unavailable."})
    with transaction.atomic():
        if previous_token:
            UserSession.objects.filter(token=previous_token).delete()
        session = UserSession(token=secrets.token_urlsafe(48), user=staff)
        session.save()
    return staff, session


def ensure_default_staff() -> list[StaffUser]:
    """Ensure baseline staff accounts exist and link unassigned legacy appointments.

    Idempotent operation wrapped in transaction.atomic():
    1. Checks if each default account ('maria', 'dreyes', 'dsantos', 'dtan') exists.
       If missing, creates it with PBKDF2 password hashing.
    2. Searches for unassigned appointments (doctor_id is None) and links them to
       the matching doctor account if doctor_name matches full_name.
    Returns list of all active staff accounts.
    """
    seeded_or_existing: list[StaffUser] = []
    with transaction.atomic():
        for fixture in DEFAULT_STAFF_ACCOUNTS:
            staff = StaffUser.objects.filter(username=fixture["username"]).first()
            if not staff:
                staff = StaffUser(
                    username=fixture["username"],
                    full_name=fixture["full_name"],
                    role=fixture["role"],
                    specialty=fixture["specialty"],
                    license_number=fixture["license_number"],
                    contact=fixture["contact"],
                )
                staff.set_password(fixture["password"])
                staff.save()
            seeded_or_existing.append(staff)

        # Link legacy unassigned appointments to doctors by name matching
        doctors = [s for s in seeded_or_existing if s.role == StaffRole.DOCTOR]
        doc_map = {d.full_name.strip().lower(): d for d in doctors}
        unassigned_appts = Appointment.objects.filter(doctor__isnull=True).exclude(doctor_name="")
        for appt in unassigned_appts:
            doc = doc_map.get(appt.doctor_name.strip().lower())
            if doc:
                appt.doctor = doc
                appt.save(update_fields=["doctor"])

    return seeded_or_existing


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
    doc = StaffUser.objects.filter(id=doctor_id).first()
    doctor_filter = Q(doctor_id=doctor_id)
    if doc and doc.full_name:
        doctor_filter |= Q(doctor__isnull=True, doctor_name__iexact=doc.full_name)

    qs = Appointment.objects.select_related("patient").filter(
        doctor_filter,
        app_date__range=(app_date - timedelta(days=1), app_date + timedelta(days=1)),
        status__in=active_statuses,
    )
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)

    conflicts: list[Appointment] = []
    target = datetime.combine(app_date, app_time)
    for appt in qs:
        appointment_at = datetime.combine(appt.app_date, appt.app_time)
        if abs((appointment_at - target).total_seconds()) < slot_duration_minutes * 60:
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

    with transaction.atomic():
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise ValidationError(
                {"patient_id": f"Patient #{patient_id} does not exist."}
            ) from None
        try:
            doctor = StaffUser.objects.get(id=doctor_id)
        except StaffUser.DoesNotExist:
            raise ValidationError({"doctor_id": f"Doctor #{doctor_id} does not exist."}) from None
        if not doctor.is_active or doctor.role != StaffRole.DOCTOR:
            raise ValidationError({"doctor_id": "Only active doctors can author medical records."})
        appointment: Appointment | None = None
        if appointment_id is not None:
            try:
                appointment = Appointment.objects.select_for_update().get(id=appointment_id)
            except Appointment.DoesNotExist:
                raise ValidationError(
                    {"appointment_id": f"Appointment #{appointment_id} does not exist."}
                ) from None
            if appointment.patient_id != patient.id:
                raise ValidationError(
                    {
                        "appointment_id": f"Appointment #{appointment_id} belongs to a different patient."
                    }
                )
            if appointment.doctor_id != doctor.id:
                raise ValidationError(
                    {"appointment_id": "Only the assigned doctor can sign this appointment."}
                )
            if appointment.status != AppointmentStatus.IN_CONSULTATION:
                raise ValidationError(
                    {"appointment_id": "Only an in-consultation appointment can be signed."}
                )
            if MedicalRecord.objects.filter(appointment_id=appointment_id).exists():
                raise ValidationError(
                    {
                        "appointment_id": f"A medical record already exists for appointment #{appointment_id}."
                    }
                )
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
        MedicalRecordRevision.objects.create(
            record=record,
            revision=record.revision,
            correction_reason="Initial signed record.",
            diagnosis=record.diagnosis,
            symptoms=record.symptoms,
            clinical_notes=record.clinical_notes,
            prescription=record.prescription,
            follow_up_advice=record.follow_up_advice,
            changed_by=doctor,
        )

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
    correction_reason: str = "",
    expected_revision: int | None = None,
) -> MedicalRecord:
    """Update clinical record with author-only restriction."""
    clean_diagnosis = (diagnosis or "").strip()
    if not clean_diagnosis:
        raise ValidationError({"diagnosis": "Primary diagnosis is required."})

    with transaction.atomic():
        try:
            record = MedicalRecord.objects.select_for_update().get(id=record_id)
        except MedicalRecord.DoesNotExist:
            raise ValidationError(
                {"record": f"Medical record #{record_id} does not exist."}
            ) from None
        if record.doctor_id != doctor_id:
            raise ValidationError(
                {"doctor": "Only the authoring physician can edit this clinical record."}
            )
        if expected_revision is not None and record.revision != expected_revision:
            raise ValidationError(
                {
                    "revision": "This record has been corrected by another user. Refresh and try again."
                }
            )
        clean_reason = (correction_reason or "").strip()
        if not clean_reason:
            raise ValidationError({"correction_reason": "A correction reason is required."})
        record.diagnosis = clean_diagnosis
        record.symptoms = (symptoms or "").strip()
        record.clinical_notes = (clinical_notes or "").strip()
        record.prescription = (prescription or "").strip()
        record.follow_up_advice = (follow_up_advice or "").strip()
        record.revision += 1
        record.save()
        MedicalRecordRevision.objects.create(
            record=record,
            revision=record.revision,
            correction_reason=clean_reason,
            diagnosis=record.diagnosis,
            symptoms=record.symptoms,
            clinical_notes=record.clinical_notes,
            prescription=record.prescription,
            follow_up_advice=record.follow_up_advice,
            changed_by_id=doctor_id,
        )
        return record


def get_doctor_queue(
    doctor_id: int, target_date: date | None = None
) -> dict[str, list[Appointment]]:
    """Return today's doctor queue grouped by clinical status."""
    ref_date = target_date or clinic_now().date()
    doc = StaffUser.objects.filter(id=doctor_id).first()
    doctor_filter = Q(doctor_id=doctor_id)
    if doc and doc.full_name:
        doctor_filter |= Q(doctor__isnull=True, doctor_name__iexact=doc.full_name)

    base_qs = (
        Appointment.objects.select_related("patient")
        .filter(doctor_filter, app_date=ref_date)
        .order_by("checked_in_at", "app_time", "id")
    )

    return {
        "checked_in": list(base_qs.filter(status=AppointmentStatus.CHECKED_IN)),
        "in_consultation": list(base_qs.filter(status=AppointmentStatus.IN_CONSULTATION)),
        "scheduled": list(base_qs.filter(status=AppointmentStatus.SCHEDULED)),
        "completed": list(base_qs.filter(status=AppointmentStatus.COMPLETED)),
    }


def get_doctor_patients(doctor_id: int, query: str | None = None) -> list[Patient]:
    """Return distinct patients seen by or scheduled with this doctor."""
    doc = StaffUser.objects.filter(id=doctor_id).first()
    appt_filter = Q(appointments__doctor_id=doctor_id)
    if doc and doc.full_name:
        appt_filter |= Q(
            appointments__doctor__isnull=True, appointments__doctor_name__iexact=doc.full_name
        )

    qs = (
        Patient.objects.filter(appt_filter | Q(medical_records__doctor_id=doctor_id))
        .distinct()
        .annotate(
            appointment_count=Count("appointments", distinct=True),
            doctor_appointment_count=Count(
                "appointments",
                filter=appt_filter,
                distinct=True,
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
