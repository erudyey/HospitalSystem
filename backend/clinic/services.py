"""Business logic service operations.

All operations execute inside database transactions, perform explicit validation,
and return strongly-typed model instances decoupled from HTTP requests.
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

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
    """Return patients ordered by ID, optionally filtered by substring or exact ID."""
    queryset = Patient.objects.all().order_by("id")
    if query:
        clean_query = query.strip()
        if clean_query.isdigit():
            queryset = queryset.filter(Q(full_name__icontains=clean_query) | Q(id=int(clean_query)))
        else:
            queryset = queryset.filter(full_name__icontains=clean_query)
    return list(queryset)


def get_patient(patient_id: int) -> Patient:
    """Retrieve a single patient by ID or raise Patient.DoesNotExist."""
    return Patient.objects.get(id=patient_id)


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


def list_patient_appointments(patient_id: int) -> list[Appointment]:
    """Return all appointments for a patient ordered by ID."""
    patient = Patient.objects.get(id=patient_id)
    return list(Appointment.objects.filter(patient=patient).order_by("id"))


def update_appointment_status(appointment_id: int, new_status: str) -> Appointment:
    """Update an appointment's status to Completed or Cancelled."""
    clean_status = (new_status or "").strip()
    if clean_status not in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
        raise ValidationError(
            {
                "status": f"Status can only be updated to 'Completed' or 'Cancelled', not '{clean_status}'."
            }
        )

    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        appointment.status = clean_status
        appointment.save()
        return appointment
