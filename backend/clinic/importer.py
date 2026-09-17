"""Safe, non-destructive legacy SQLite data migration service.

Uses Python's sqlite3.Connection.backup() API to create an atomic snapshot,
validates integrity, maps legacy IDs, and imports records into the Django database.
"""

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any

from django.db import transaction

from backend.clinic.models import Appointment, AppointmentStatus, Patient


class MigrationAnomalyError(Exception):
    """Raised when legacy data contains corrupt, orphaned, or incompatible values."""

    def __init__(self, message: str, anomalies: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.anomalies = anomalies


def snapshot_legacy_db(source_db_path: Path, snapshot_dest_path: Path) -> None:
    """Create a consistent snapshot of the legacy database using SQLite backup API."""
    if not source_db_path.exists():
        raise FileNotFoundError(f"Source database not found at {source_db_path}")

    snapshot_dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Open source in read-only mode to prevent write locks or accidental modifications
    src_uri = f"file:{source_db_path.resolve().as_posix()}?mode=ro"
    with (
        closing(sqlite3.connect(src_uri, uri=True)) as src_conn,
        closing(sqlite3.connect(str(snapshot_dest_path))) as dst_conn,
    ):
        src_conn.backup(dst_conn)


def validate_legacy_snapshot(
    snapshot_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Inspect and validate snapshot rows, returning (patients, appointments, anomalies)."""
    anomalies: list[dict[str, Any]] = []
    patients_data: list[dict[str, Any]] = []
    appointments_data: list[dict[str, Any]] = []

    with closing(
        sqlite3.connect(f"file:{snapshot_path.resolve().as_posix()}?mode=ro", uri=True)
    ) as conn:
        conn.row_factory = sqlite3.Row

        # 1. Inspect patients table
        patient_rows = conn.execute("SELECT * FROM patients ORDER BY patient_id").fetchall()
        valid_patient_ids = set()

        for row in patient_rows:
            p_id = row["patient_id"]
            name = row["full_name"]
            age = row["age"]
            contact = row["contact"] or ""

            if not name or not str(name).strip():
                anomalies.append(
                    {
                        "table": "patients",
                        "id": p_id,
                        "field": "full_name",
                        "issue": "Missing or blank name",
                    }
                )

            try:
                age_val = int(age)
                if age_val <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                anomalies.append(
                    {
                        "table": "patients",
                        "id": p_id,
                        "field": "age",
                        "issue": f"Invalid age value: {age}",
                    }
                )
                age_val = None

            if age_val is not None and name:
                valid_patient_ids.add(p_id)
                patients_data.append(
                    {
                        "id": p_id,
                        "full_name": str(name).strip(),
                        "contact": str(contact).strip(),
                        "age": age_val,
                    }
                )

        # 2. Inspect appointments table
        app_rows = conn.execute("SELECT * FROM appointments ORDER BY app_id").fetchall()
        for row in app_rows:
            a_id = row["app_id"]
            p_id = row["patient_id"]
            doctor = row["doctor_name"]
            app_date = row["app_date"]
            status = row["status"] or "Scheduled"

            if p_id not in valid_patient_ids:
                anomalies.append(
                    {
                        "table": "appointments",
                        "id": a_id,
                        "field": "patient_id",
                        "issue": f"Orphaned appointment for non-existent patient {p_id}",
                    }
                )

            if not doctor or not str(doctor).strip():
                anomalies.append(
                    {
                        "table": "appointments",
                        "id": a_id,
                        "field": "doctor_name",
                        "issue": "Missing doctor name",
                    }
                )

            try:
                parsed_date = date.fromisoformat(str(app_date))
                canonical_date = parsed_date.isoformat()
            except (ValueError, TypeError):
                anomalies.append(
                    {
                        "table": "appointments",
                        "id": a_id,
                        "field": "app_date",
                        "issue": f"Non-ISO date format: {app_date}",
                    }
                )
                canonical_date = None

            if status not in AppointmentStatus.values:
                anomalies.append(
                    {
                        "table": "appointments",
                        "id": a_id,
                        "field": "status",
                        "issue": f"Invalid status: {status}",
                    }
                )

            if (
                canonical_date
                and doctor
                and (p_id in valid_patient_ids)
                and (status in AppointmentStatus.values)
            ):
                appointments_data.append(
                    {
                        "id": a_id,
                        "patient_id": p_id,
                        "doctor_name": str(doctor).strip(),
                        "app_date": canonical_date,
                        "status": status,
                    }
                )

    return patients_data, appointments_data, anomalies


def import_legacy_data(source_db_path: Path, snapshot_dir: Path) -> dict[str, Any]:
    """Execute full migration from legacy database into the modern database."""
    snapshot_file = snapshot_dir / f"legacy_snapshot_{date.today().isoformat()}.sqlite3"
    snapshot_legacy_db(source_db_path, snapshot_file)

    patients, appointments, anomalies = validate_legacy_snapshot(snapshot_file)
    if anomalies:
        raise MigrationAnomalyError(
            f"Found {len(anomalies)} integrity anomalies in legacy database. Aborting to prevent corruption.",
            anomalies=anomalies,
        )

    with transaction.atomic():
        imported_patients = 0
        for p in patients:
            Patient.objects.update_or_create(
                id=p["id"],
                defaults={"full_name": p["full_name"], "contact": p["contact"], "age": p["age"]},
            )
            imported_patients += 1

        imported_appointments = 0
        for a in appointments:
            patient_obj = Patient.objects.get(id=a["patient_id"])
            Appointment.objects.update_or_create(
                id=a["id"],
                defaults={
                    "patient": patient_obj,
                    "doctor_name": a["doctor_name"],
                    "app_date": a["app_date"],
                    "status": a["status"],
                },
            )
            imported_appointments += 1

    return {
        "status": "success",
        "imported_patients": imported_patients,
        "imported_appointments": imported_appointments,
        "snapshot_path": str(snapshot_file),
    }
