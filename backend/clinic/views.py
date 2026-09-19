"""JSON API Views for HospitalSystem.

These views act as thin adapters mapping HTTP requests to pure Python service functions.
"""

import contextlib
import json
from datetime import date
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from backend.clinic import services
from backend.clinic.models import (
    Appointment,
    AppointmentStatus,
    MedicalRecord,
    Patient,
    StaffRole,
    StaffUser,
)


def format_error(
    code: str, message: str, fields: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """Format standardized error dictionary."""
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
        }
    }


def validation_error_response(err: ValidationError, message: str) -> JsonResponse:
    """Construct standardized 400 JsonResponse for a ValidationError."""
    fields = (
        {k: list(v) if isinstance(v, list) else [str(v)] for k, v in err.message_dict.items()}
        if hasattr(err, "message_dict")
        else {"general": err.messages}
    )
    return JsonResponse(format_error("VALIDATION_ERROR", message, fields), status=400)


def parse_json(request: HttpRequest) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    """Safely parse request body as JSON."""
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            return None, JsonResponse(
                format_error("BAD_REQUEST", "JSON body must be an object."),
                status=400,
            )
        return data, None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse(
            format_error("BAD_REQUEST", "Malformed JSON in request body."),
            status=400,
        )


def serialize_patient(patient: Patient) -> dict[str, Any]:
    """Serialize Patient instance to dictionary."""
    return {
        "id": patient.id,
        "full_name": patient.full_name,
        "contact": patient.contact,
        "age": patient.age,
        "appointment_count": getattr(patient, "appointment_count", 0),
        "active_appointment_count": getattr(patient, "active_appointment_count", 0),
    }


def serialize_appointment(appointment: Appointment) -> dict[str, Any]:
    """Serialize Appointment instance to dictionary."""
    return {
        "id": appointment.id,
        "patient_id": appointment.patient_id,
        "patient_name": appointment.patient.full_name,
        "doctor_id": appointment.doctor_id,
        "doctor_name": appointment.doctor_name,
        "app_date": appointment.app_date.isoformat(),
        "app_time": appointment.app_time.strftime("%H:%M"),
        "reason_for_visit": appointment.reason_for_visit,
        "status": appointment.status,
    }


def serialize_staff_user(user: StaffUser) -> dict[str, Any]:
    """Serialize StaffUser instance to dictionary."""
    role_label = StaffRole(user.role).label if user.role in StaffRole.values else user.role
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "role_label": role_label,
        "specialty": user.specialty,
        "license_number": user.license_number,
        "contact": user.contact,
        "created_at": user.created_at.isoformat(),
    }


def serialize_medical_record(record: MedicalRecord) -> dict[str, Any]:
    """Serialize MedicalRecord clinical documentation to dictionary."""
    return {
        "id": record.id,
        "patient_id": record.patient_id,
        "patient_name": record.patient.full_name,
        "doctor_id": record.doctor_id,
        "doctor_name": record.doctor.full_name,
        "doctor_specialty": record.doctor.specialty,
        "appointment_id": record.appointment_id,
        "diagnosis": record.diagnosis,
        "symptoms": record.symptoms,
        "clinical_notes": record.clinical_notes,
        "prescription": record.prescription,
        "follow_up_advice": record.follow_up_advice,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def get_authenticated_user(request: HttpRequest) -> StaffUser | None:
    """Extract and validate UserSession token from request headers."""
    auth_header = request.headers.get("X-User-Token") or request.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else auth_header.strip()
    if not token:
        return None
    return services.validate_session(token)


@ensure_csrf_cookie
@require_GET
def health_check(_request: HttpRequest) -> JsonResponse:
    """Readiness probe and CSRF cookie setter."""
    if not getattr(settings, "IS_TESTING", False):
        services.ensure_default_staff()
    return JsonResponse({"status": "ok", "version": "0.0.1"})


@require_http_methods(["GET", "POST"])
def patients_collection(request: HttpRequest) -> JsonResponse:
    """List/search patients (GET) or register a new patient (POST)."""
    if request.method == "GET":
        query = request.GET.get("q", "").strip() or None
        patients = services.list_patients(query=query)
        return JsonResponse([serialize_patient(p) for p in patients], safe=False, status=200)

    # POST: register patient
    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    try:
        patient = services.register_patient(
            full_name=data.get("full_name", ""),
            contact=data.get("contact", ""),
            age=data.get("age", 0),
        )
        return JsonResponse(serialize_patient(patient), status=201)
    except ValidationError as err:
        return validation_error_response(err, "Patient registration failed validation.")


@require_http_methods(["GET", "PUT", "DELETE"])
def patient_detail(request: HttpRequest, patient_id: int) -> JsonResponse:
    """Retrieve (GET), update (PUT), or delete (DELETE) a single patient."""
    try:
        if request.method == "GET":
            patient = services.get_patient(patient_id=patient_id)
            return JsonResponse(serialize_patient(patient), status=200)

        elif request.method == "PUT":
            data, err_response = parse_json(request)
            if err_response or data is None:
                return err_response or JsonResponse(
                    format_error("BAD_REQUEST", "Request body must not be empty."), status=400
                )
            patient = services.update_patient(
                patient_id=patient_id,
                full_name=data.get("full_name", ""),
                contact=data.get("contact", ""),
                age=data.get("age", 0),
            )
            return JsonResponse(serialize_patient(patient), status=200)

        elif request.method == "DELETE":
            services.delete_patient(patient_id=patient_id)
            return JsonResponse({}, status=204)

    except Patient.DoesNotExist:
        return JsonResponse(
            format_error("NOT_FOUND", f"Patient #{patient_id} does not exist."),
            status=404,
        )
    except ValidationError as err:
        return validation_error_response(err, "Patient operation failed validation.")

    return JsonResponse(format_error("METHOD_NOT_ALLOWED", "Method not allowed."), status=405)


@require_GET
def patient_appointments(request: HttpRequest, patient_id: int) -> JsonResponse:
    """Retrieve all appointments for a given patient ID."""
    try:
        appointments = services.list_patient_appointments(patient_id=patient_id)
        return JsonResponse(
            [serialize_appointment(a) for a in appointments], safe=False, status=200
        )
    except Patient.DoesNotExist:
        return JsonResponse(
            format_error("NOT_FOUND", f"Patient #{patient_id} does not exist."),
            status=404,
        )


@require_http_methods(["GET", "POST"])
def appointments_collection(request: HttpRequest) -> JsonResponse:
    """List all appointments (GET) or book a new appointment (POST)."""
    if request.method == "GET":
        appointments = services.list_all_appointments()
        return JsonResponse(
            [serialize_appointment(a) for a in appointments], safe=False, status=200
        )

    # POST: book appointment
    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    patient_id = data.get("patient_id")
    if patient_id is None:
        return JsonResponse(
            format_error(
                "VALIDATION_ERROR",
                "Missing required field.",
                {"patient_id": ["Patient ID is required."]},
            ),
            status=400,
        )

    try:
        patient_id_int = int(patient_id)
    except (ValueError, TypeError):
        return JsonResponse(
            format_error(
                "VALIDATION_ERROR",
                "Invalid field format.",
                {"patient_id": ["Patient ID must be an integer."]},
            ),
            status=400,
        )

    try:
        raw_doc_id = data.get("doctor_id")
        doc_id_val: int | None = int(raw_doc_id) if raw_doc_id is not None else None
    except (ValueError, TypeError):
        doc_id_val = None

    try:
        appointment = services.book_appointment(
            patient_id=patient_id_int,
            doctor_name=data.get("doctor_name", ""),
            app_date_str=data.get("app_date", ""),
            app_time_str=data.get("app_time", "09:00"),
            reason_for_visit=data.get("reason_for_visit", ""),
            doctor_id=doc_id_val,
            initial_status=data.get("initial_status", AppointmentStatus.SCHEDULED),
        )
        return JsonResponse(serialize_appointment(appointment), status=201)
    except ValidationError as err:
        return validation_error_response(err, "Appointment booking failed validation.")


@require_http_methods(["GET", "PUT", "DELETE"])
def appointment_detail(request: HttpRequest, appointment_id: int) -> JsonResponse:
    """Retrieve (GET), update/reschedule (PUT), or delete (DELETE) a single appointment."""
    try:
        if request.method == "GET":
            appointment = Appointment.objects.select_related("patient").get(id=appointment_id)
            return JsonResponse(serialize_appointment(appointment), status=200)

        elif request.method == "PUT":
            data, err_response = parse_json(request)
            if err_response or data is None:
                return err_response or JsonResponse(
                    format_error("BAD_REQUEST", "Request body must not be empty."), status=400
                )

            raw_doc_id = data.get("doctor_id")
            doc_id_val = int(raw_doc_id) if raw_doc_id is not None else None

            appointment = services.update_appointment(
                appointment_id=appointment_id,
                doctor_name=data.get("doctor_name"),
                app_date_str=data.get("app_date"),
                app_time_str=data.get("app_time"),
                reason_for_visit=data.get("reason_for_visit"),
                doctor_id=doc_id_val,
            )
            return JsonResponse(serialize_appointment(appointment), status=200)

        elif request.method == "DELETE":
            services.delete_appointment(appointment_id=appointment_id)
            return JsonResponse({}, status=204)

    except Appointment.DoesNotExist:
        return JsonResponse(
            format_error("NOT_FOUND", f"Appointment #{appointment_id} does not exist."),
            status=404,
        )
    except ValidationError as err:
        return validation_error_response(err, "Appointment operation failed validation.")

    return JsonResponse(format_error("METHOD_NOT_ALLOWED", "Method not allowed."), status=405)


@require_http_methods(["PATCH"])
def appointment_status(request: HttpRequest, appointment_id: int) -> JsonResponse:
    """Update an appointment's status following state machine rules."""
    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    new_status = data.get("status", "")
    try:
        appointment = services.update_appointment_status(
            appointment_id=appointment_id,
            new_status=new_status,
        )
        return JsonResponse(serialize_appointment(appointment), status=200)
    except Appointment.DoesNotExist:
        return JsonResponse(
            format_error("NOT_FOUND", f"Appointment #{appointment_id} does not exist."),
            status=404,
        )
    except ValidationError as err:
        return validation_error_response(err, "Status update failed validation.")


# Authentication and Staff Views


@require_http_methods(["POST"])
def auth_register(request: HttpRequest) -> JsonResponse:
    """Register a new staff account (Receptionist or Doctor)."""
    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    try:
        staff = services.register_staff(
            username=data.get("username", ""),
            password=data.get("password", ""),
            full_name=data.get("full_name", ""),
            role=data.get("role", StaffRole.RECEPTIONIST),
            specialty=data.get("specialty", ""),
            license_number=data.get("license_number", ""),
            contact=data.get("contact", ""),
        )
        return JsonResponse(serialize_staff_user(staff), status=201)
    except ValidationError as err:
        return validation_error_response(err, "Staff registration failed validation.")


@require_http_methods(["POST"])
def auth_login(request: HttpRequest) -> JsonResponse:
    """Authenticate staff credentials and issue a new session token."""
    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    username = data.get("username", "")
    password = data.get("password", "")

    try:
        staff, session = services.authenticate_staff(username=username, password=password)
        return JsonResponse(
            {
                "token": session.token,
                "user": serialize_staff_user(staff),
            },
            status=200,
        )
    except ValidationError as err:
        return validation_error_response(err, "Authentication failed.")


@require_GET
def auth_me(request: HttpRequest) -> JsonResponse:
    """Return the currently authenticated staff profile."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )
    return JsonResponse({"user": serialize_staff_user(user)}, status=200)


@require_http_methods(["POST"])
def auth_logout(request: HttpRequest) -> JsonResponse:
    """Terminate the active session token."""
    auth_header = request.headers.get("X-User-Token") or request.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else auth_header.strip()
    if token:
        services.logout_staff(token)
    return JsonResponse({"status": "ok", "message": "Successfully logged out."}, status=200)


@require_http_methods(["PUT"])
def auth_profile(request: HttpRequest) -> JsonResponse:
    """Update active staff profile details and change password."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )

    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    try:
        updated_user = services.update_staff_profile(
            user_id=user.id,
            full_name=data.get("full_name", user.full_name),
            contact=data.get("contact", user.contact),
            specialty=data.get("specialty", user.specialty),
            license_number=data.get("license_number", user.license_number),
            current_password=data.get("current_password") or None,
            new_password=data.get("new_password") or None,
        )
        return JsonResponse({"user": serialize_staff_user(updated_user)}, status=200)
    except ValidationError as err:
        return validation_error_response(err, "Profile update failed validation.")


@require_GET
def doctors_collection(_request: HttpRequest) -> JsonResponse:
    """Return list of active physician accounts for appointment scheduling."""
    doctors = services.list_doctors()
    return JsonResponse([serialize_staff_user(d) for d in doctors], safe=False, status=200)


# Clinical Views, Conflict Engine, and Medical Records


@require_GET
def check_conflict(request: HttpRequest) -> JsonResponse:
    """Check for schedule conflicts for a doctor on a given date and time."""
    raw_doc_id = request.GET.get("doctor_id")
    if not raw_doc_id:
        return JsonResponse(
            format_error("BAD_REQUEST", "doctor_id query parameter is required."),
            status=400,
        )

    try:
        doctor_id = int(raw_doc_id)
    except (ValueError, TypeError):
        return JsonResponse(
            format_error("BAD_REQUEST", "doctor_id must be an integer."),
            status=400,
        )

    date_str = request.GET.get("date", "")
    try:
        app_date = date.fromisoformat(date_str.strip())
    except (ValueError, TypeError):
        return JsonResponse(
            format_error("BAD_REQUEST", "date must be in YYYY-MM-DD format."),
            status=400,
        )

    time_str = request.GET.get("time", "09:00")
    try:
        app_time = services._parse_time(time_str)
    except ValidationError:
        return JsonResponse(
            format_error("BAD_REQUEST", "time must be in HH:MM format."),
            status=400,
        )

    duration = 15
    if "duration" in request.GET:
        try:
            duration = int(request.GET["duration"])
        except ValueError:
            duration = 15

    exclude_id = None
    if "exclude_id" in request.GET:
        try:
            exclude_id = int(request.GET["exclude_id"])
        except ValueError:
            exclude_id = None

    conflicts = services.check_schedule_conflict(
        doctor_id=doctor_id,
        app_date=app_date,
        app_time=app_time,
        slot_duration_minutes=duration,
        exclude_id=exclude_id,
    )

    return JsonResponse(
        {
            "has_conflict": len(conflicts) > 0,
            "conflicts": [serialize_appointment(a) for a in conflicts],
        },
        status=200,
    )


@require_GET
def doctor_queue(request: HttpRequest) -> JsonResponse:
    """Return today's clinical triage queue for the authenticated physician."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )
    if user.role != StaffRole.DOCTOR:
        return JsonResponse(
            format_error("FORBIDDEN", "Only physician accounts can access the clinical queue."),
            status=403,
        )

    target_date: date | None = None
    date_str = request.GET.get("date")
    if date_str:
        with contextlib.suppress(ValueError, TypeError):
            target_date = date.fromisoformat(date_str.strip())

    queue = services.get_doctor_queue(doctor_id=user.id, target_date=target_date)
    serialized_queue = {
        category: [serialize_appointment(a) for a in appts] for category, appts in queue.items()
    }
    return JsonResponse({"queue": serialized_queue}, status=200)


@require_GET
def doctor_patients(request: HttpRequest) -> JsonResponse:
    """Return the roster of patients under the authenticated physician's care."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )
    if user.role != StaffRole.DOCTOR:
        return JsonResponse(
            format_error("FORBIDDEN", "Only physician accounts can access patient rosters."),
            status=403,
        )

    query = request.GET.get("q", "").strip() or None
    patients = services.get_doctor_patients(doctor_id=user.id, query=query)
    return JsonResponse([serialize_patient(p) for p in patients], safe=False, status=200)


@require_GET
def doctor_appointments(request: HttpRequest) -> JsonResponse:
    """Return all appointments assigned to the authenticated physician."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )
    if user.role != StaffRole.DOCTOR:
        return JsonResponse(
            format_error("FORBIDDEN", "Only physician accounts can access doctor appointments."),
            status=403,
        )

    appointments = list(
        Appointment.objects.select_related("patient")
        .filter(doctor_id=user.id)
        .order_by("app_date", "app_time", "id")
    )
    return JsonResponse([serialize_appointment(a) for a in appointments], safe=False, status=200)


@require_GET
def patient_medical_records(request: HttpRequest, patient_id: int) -> JsonResponse:
    """Return all clinical medical records for a specific patient ID."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )
    records = services.get_patient_medical_history(patient_id=patient_id)
    return JsonResponse([serialize_medical_record(r) for r in records], safe=False, status=200)


@require_http_methods(["POST"])
def medical_records_collection(request: HttpRequest) -> JsonResponse:
    """Create a new clinical medical record (Physicians only)."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )
    if user.role != StaffRole.DOCTOR:
        return JsonResponse(
            format_error(
                "FORBIDDEN", "Only registered doctors can author clinical medical records."
            ),
            status=403,
        )

    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    patient_id = data.get("patient_id")
    if patient_id is None:
        return JsonResponse(
            format_error(
                "VALIDATION_ERROR",
                "Patient ID is required.",
                {"patient_id": ["Patient ID is required."]},
            ),
            status=400,
        )

    try:
        patient_id_int = int(patient_id)
    except (ValueError, TypeError):
        return JsonResponse(
            format_error(
                "VALIDATION_ERROR",
                "Invalid Patient ID.",
                {"patient_id": ["Patient ID must be an integer."]},
            ),
            status=400,
        )

    raw_appt_id = data.get("appointment_id")
    appt_id_val: int | None = int(raw_appt_id) if raw_appt_id is not None else None

    try:
        record = services.create_medical_record(
            patient_id=patient_id_int,
            doctor_id=user.id,
            diagnosis=data.get("diagnosis", ""),
            symptoms=data.get("symptoms", ""),
            clinical_notes=data.get("clinical_notes", ""),
            prescription=data.get("prescription", ""),
            follow_up_advice=data.get("follow_up_advice", ""),
            appointment_id=appt_id_val,
        )
        return JsonResponse(serialize_medical_record(record), status=201)
    except ValidationError as err:
        return validation_error_response(err, "Medical record creation failed validation.")


@require_http_methods(["GET", "PUT"])
def medical_record_detail(request: HttpRequest, record_id: int) -> JsonResponse:
    """Retrieve or update an existing clinical medical record."""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse(
            format_error("UNAUTHENTICATED", "Active session required. Please sign in."),
            status=401,
        )

    try:
        record = MedicalRecord.objects.select_related("patient", "doctor", "appointment").get(
            id=record_id
        )
    except MedicalRecord.DoesNotExist:
        return JsonResponse(
            format_error("NOT_FOUND", f"Medical record #{record_id} does not exist."),
            status=404,
        )

    if request.method == "GET":
        return JsonResponse(serialize_medical_record(record), status=200)

    if user.role != StaffRole.DOCTOR:
        return JsonResponse(
            format_error("FORBIDDEN", "Only physician accounts can edit medical records."),
            status=403,
        )

    data, err_response = parse_json(request)
    if err_response or data is None:
        return err_response or JsonResponse(
            format_error("BAD_REQUEST", "Request body must not be empty."), status=400
        )

    try:
        updated = services.update_medical_record(
            record_id=record_id,
            doctor_id=user.id,
            diagnosis=data.get("diagnosis", ""),
            symptoms=data.get("symptoms", ""),
            clinical_notes=data.get("clinical_notes", ""),
            prescription=data.get("prescription", ""),
            follow_up_advice=data.get("follow_up_advice", ""),
        )
        return JsonResponse(serialize_medical_record(updated), status=200)
    except ValidationError as err:
        return validation_error_response(err, "Medical record update failed validation.")
