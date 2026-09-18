"""Business logic service operations.

All operations execute inside database transactions, perform explicit validation,
and return strongly-typed model instances decoupled from HTTP requests.
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q

from backend.clinic.models import Appointment, AppointmentStatus, Patient


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
            filter=Q(appointments__status=AppointmentStatus.SCHEDULED),
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
            filter=Q(appointments__status=AppointmentStatus.SCHEDULED),
        ),
    ).get(id=patient_id)


def book_appointment(patient_id: int, doctor_name: str, app_date_str: str) -> Appointment:
    """Book a new scheduled appointment for a valid patient ID."""
    clean_doctor = (doctor_name or "").strip()
    errors: dict[str, str] = {}

    if not clean_doctor:
        errors["doctor_name"] = "Doctor name is required."

    clean_date_str = (app_date_str or "").strip()
    parsed_date: date | None = None
    try:
        parsed_date = date.fromisoformat(clean_date_str)
    except (ValueError, TypeError):
        errors["app_date"] = "Date must be a valid ISO date in YYYY-MM-DD format."

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
            doctor_name=clean_doctor,
            app_date=parsed_date,
            status=AppointmentStatus.SCHEDULED,
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
        return patient.delete()


def list_all_appointments() -> list[Appointment]:
    """Return all appointments ordered by ID descending with patient data pre-fetched."""
    return list(Appointment.objects.select_related("patient").order_by("-id"))


def list_patient_appointments(patient_id: int) -> list[Appointment]:
    """Return all appointments for a patient ordered by ID."""
    patient = Patient.objects.get(id=patient_id)
    return list(Appointment.objects.filter(patient=patient).order_by("id"))


def update_appointment(appointment_id: int, doctor_name: str, app_date_str: str) -> Appointment:
    """Update appointment details (rescheduling / doctor reassignment)."""
    clean_doctor = (doctor_name or "").strip()
    clean_date_str = (app_date_str or "").strip()
    errors: dict[str, str] = {}

    if not clean_doctor:
        errors["doctor_name"] = "Doctor name is required."

    parsed_date: date | None = None
    try:
        parsed_date = date.fromisoformat(clean_date_str)
    except (ValueError, TypeError):
        errors["app_date"] = "Date must be a valid ISO date in YYYY-MM-DD format."

    if errors or parsed_date is None:
        raise ValidationError(errors)

    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        if appointment.status == AppointmentStatus.COMPLETED:
            raise ValidationError(
                {
                    "appointment": "Completed appointments are finalized clinical records and cannot be rescheduled or modified."
                }
            )
        appointment.doctor_name = clean_doctor
        appointment.app_date = parsed_date
        appointment.save()
        return appointment


def delete_appointment(appointment_id: int) -> tuple[int, dict[str, int]]:
    """Delete an appointment record."""
    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        return appointment.delete()


def update_appointment_status(appointment_id: int, new_status: str) -> Appointment:
    """Update an appointment's status following strict clinical state machine rules.

    Valid transitions:
    - Scheduled -> Completed, Cancelled
    - Cancelled -> Scheduled (restoring)
    - Completed -> Immutable (cannot transition to Scheduled or Cancelled)
    """
    clean_status = (new_status or "").strip()
    if clean_status not in AppointmentStatus.values:
        raise ValidationError(
            {
                "status": f"Invalid status '{clean_status}'. Must be Scheduled, Completed, or Cancelled."
            }
        )

    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        current = appointment.status

        # If unchanged, return immediately
        if current == clean_status:
            return appointment

        # Completed is immutable
        if current == AppointmentStatus.COMPLETED:
            raise ValidationError(
                {
                    "status": "Completed appointments are finalized clinical records and cannot be altered or cancelled."
                }
            )

        # Cancelled can only transition to Scheduled
        if current == AppointmentStatus.CANCELLED and clean_status != AppointmentStatus.SCHEDULED:
            raise ValidationError(
                {
                    "status": f"Cancelled appointments can only be restored to 'Scheduled', not directly to '{clean_status}'."
                }
            )

        appointment.status = clean_status
        appointment.save()
        return appointment
