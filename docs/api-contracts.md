# API contracts and data specifications

This document outlines the REST API endpoints, JSON request and response payloads, error models, and database field constraints for the Hospital Management System.

---

## 1. Data models

### Patient
| Field | Type | Rules |
|---|---|---|
| `id` | Integer (Primary Key) | Auto-incrementing positive integer identifier. |
| `full_name` | String (Max 150) | Required. Leading and trailing whitespace is stripped. Duplicate names are allowed. |
| `contact` | String (Max 100) | Optional string. Leading and trailing whitespace is stripped. |
| `age` | Integer | Required positive whole number greater than 0. |

### Appointment
| Field | Type | Rules |
|---|---|---|
| `id` | Integer (Primary Key) | Auto-incrementing positive integer identifier. |
| `patient_id` | Integer (Foreign Key) | Required. References a valid `Patient.id`. |
| `doctor_name` | String (Max 150) | Required non-blank text identifying the doctor. |
| `app_date` | Date (ISO string) | Required date in `YYYY-MM-DD` format. |
| `status` | String | Default: `Scheduled`. Allowed values: `Scheduled`, `Completed`, `Cancelled`. |

---

## 2. API endpoints

All API routes start with `/api/` and require either the `X-Session-Token` HTTP header or the local loopback session cookie.

### `GET /api/health/`
Readiness check and CSRF cookie initialization. This endpoint is exempt from token verification so the desktop launcher can probe server availability before window display.
- **Status**: `200 OK`
- **Response**:
  ```json
  {
    "status": "ok",
    "version": "2.0.0"
  }
  ```

---

### `GET /api/patients/?q={query}`
List and search patient records.
- **Query parameters**:
  - `q` (optional): Substring filter for `full_name` (case-insensitive) or exact numeric match for `id`.
- **Status**: `200 OK`
- **Response**:
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
- **Request body**:
  ```json
  {
    "full_name": "Maria Santos",
    "contact": "09180000002",
    "age": 34
  }
  ```
- **Status**: `201 Created`
- **Response**: Persisted patient object with newly assigned `id`.

---

### `GET /api/patients/{patient_id}/appointments/`
Retrieve all appointments booked for a specific patient.
- **Status**: `200 OK` (or `404 Not Found` if the patient does not exist)
- **Response**:
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
Book a new appointment for an existing patient.
- **Request body**:
  ```json
  {
    "patient_id": 1,
    "doctor_name": "Dr. Cruz",
    "app_date": "2026-09-25"
  }
  ```
- **Status**: `201 Created`
- **Response**: Persisted appointment object initialized with status `Scheduled`.

---

### `PATCH /api/appointments/{id}/status/`
Update an appointment's status.
- **Request body**:
  ```json
  {
    "status": "Completed"
  }
  ```
- **Rules**: `status` must be either `Completed` or `Cancelled`.
- **Status**: `200 OK` (or `404 Not Found` if the appointment does not exist)
- **Response**: Updated appointment object.

---

## 3. Standard error format

When an API call fails, the response returns a structured JSON error envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted data failed validation.",
    "fields": {
      "age": ["Age must be a positive whole number greater than 0."],
      "doctor_name": ["Doctor name is required."]
    }
  }
}
```

### Common error codes
- `UNAUTHORIZED`: Missing or invalid session token (HTTP 403).
- `VALIDATION_ERROR`: Field validation or domain rule failure (HTTP 400).
- `NOT_FOUND`: Referenced patient or appointment ID does not exist (HTTP 404).
- `BAD_REQUEST`: Malformed JSON or non-object payload (HTTP 400).
- `SERVER_ERROR`: Unhandled internal exception (HTTP 500).
