# API Contracts & Data Specifications

This document outlines the REST API endpoints, request/response formats, error payloads, and database entity schemas.

---

## 1. Data Models

### Patient
| Field | Type | Rules |
|---|---|---|
| `id` | Integer (Primary Key) | Auto-incrementing positive integer identifier. |
| `full_name` | String (Max 150) | Required; trimmed of leading/trailing whitespace. Identical names permitted. |
| `contact` | String (Max 100) | Optional; stored as string; trimmed. |
| `age` | Integer | Required positive whole number ($> 0$). |

### Appointment
| Field | Type | Rules |
|---|---|---|
| `id` | Integer (Primary Key) | Auto-incrementing positive integer identifier. |
| `patient_id` | Integer (Foreign Key) | Required; points to a valid `Patient.id`. Cascades on patient deletion if ever implemented. |
| `doctor_name` | String (Max 150) | Required non-blank text identifying the doctor. |
| `app_date` | Date (ISO string) | Required canonical `YYYY-MM-DD` date. |
| `status` | String (Choices) | Default: `Scheduled`. Valid values: `Scheduled`, `Completed`, `Cancelled`. |

---

## 2. API Endpoints

All API endpoints are prefixed with `/api/` and require the `X-Session-Token` header.

### `GET /api/health/`
Readiness probe and CSRF cookie initialization.
- **Status**: `200 OK`
- **Response Body**:
  ```json
  {
    "status": "ok",
    "version": "2.0.0"
  }
  ```

---

### `GET /api/patients/?q={query}`
List and search registered patients.
- **Query Parameters**:
  - `q` (optional): Filter substring against `full_name` (case-insensitive) or exact numeric match against `id`.
- **Status**: `200 OK`
- **Response Body**:
  ```json
  [
    {
      "id": 1,
      "full_name": "Alex Reyes",
      "contact": "09170000001",
      "age": 28
    }
  ]
  ```

---

### `POST /api/patients/`
Register a new patient.
- **Request Body**:
  ```json
  {
    "full_name": "Maria Santos",
    "contact": "09180000002",
    "age": 34
  }
  ```
- **Status**: `201 Created`
- **Response Body**: Persisted patient object with allocated `id`.

---

### `GET /api/patients/{patient_id}/appointments/`
Retrieve all appointments for a specific patient.
- **Status**: `200 OK` (or `404 Not Found` if patient does not exist)
- **Response Body**:
  ```json
  [
    {
      "id": 10,
      "patient_id": 1,
      "patient_name": "Maria Santos",
      "doctor_name": "Dr. Cruz",
      "app_date": "2026-09-25",
      "status": "Scheduled"
    }
  ]
  ```

---

### `POST /api/appointments/`
Book a new appointment.
- **Request Body**:
  ```json
  {
    "patient_id": 1,
    "doctor_name": "Dr. Cruz",
    "app_date": "2026-09-25"
  }
  ```
- **Status**: `201 Created`
- **Response Body**: Persisted appointment object with status `Scheduled`.

---

### `PATCH /api/appointments/{id}/status/`
Update an appointment's status.
- **Request Body**:
  ```json
  {
    "status": "Completed"
  }
  ```
- **Rules**: Status must be `Completed` or `Cancelled`.
- **Status**: `200 OK` (or `404 Not Found` if appointment ID does not exist)
- **Response Body**: Updated appointment object.

---

## 3. Standard Error Format

All error responses return structured JSON with clear field-level breakdowns:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted data failed validation.",
    "fields": {
      "age": ["Age must be a positive whole number."],
      "doctor_name": ["Doctor name is required."]
    }
  }
}
```

### Error Codes
- `UNAUTHORIZED`: Missing or invalid `X-Session-Token` (HTTP 403).
- `VALIDATION_ERROR`: Malformed fields or business rule violation (HTTP 400).
- `NOT_FOUND`: Patient or appointment record does not exist (HTTP 404).
- `BAD_REQUEST`: Invalid JSON payload or unparseable request (HTTP 400).
- `SERVER_ERROR`: Unexpected internal error (HTTP 500).
