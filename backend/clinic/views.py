"""JSON API Views for HospitalSystem.

These views act as thin adapters mapping HTTP requests to pure Python service functions.
"""

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from backend.clinic import services
from backend.clinic.models import Appointment, Patient


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
        "doctor_name": appointment.doctor_name,
        "app_date": appointment.app_date.isoformat(),
        "status": appointment.status,
    }


@ensure_csrf_cookie
@require_GET
def health_check(_request: HttpRequest) -> JsonResponse:
    """Readiness probe and CSRF cookie setter."""
    return JsonResponse({"status": "ok", "version": "0.0.0-alpha"})


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
        appointment = services.book_appointment(
            patient_id=patient_id_int,
            doctor_name=data.get("doctor_name", ""),
            app_date_str=data.get("app_date", ""),
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
            appointment = services.update_appointment(
                appointment_id=appointment_id,
                doctor_name=data.get("doctor_name", ""),
                app_date_str=data.get("app_date", ""),
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
