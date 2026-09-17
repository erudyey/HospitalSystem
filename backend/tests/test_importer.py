"""Tests for the non-destructive legacy SQLite data migration service."""

import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from django.test import TestCase

from backend.clinic import importer
from backend.clinic.models import Appointment, Patient


class LegacyImporterTests(TestCase):
    """Test suite validating non-destructive SQLite snapshot, migration, and anomaly detection."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.legacy_db_file = self.temp_path / "legacy.db"

        # Create a mock legacy database with schema matching original clinic.db
        with closing(sqlite3.connect(str(self.legacy_db_file))) as conn:
            conn.executescript(
                """
                CREATE TABLE patients (
                    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    contact TEXT,
                    age INTEGER
                );
                CREATE TABLE appointments (
                    app_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    doctor_name TEXT NOT NULL,
                    app_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Scheduled',
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                );
                """
            )
            # Insert valid legacy records
            conn.execute(
                "INSERT INTO patients (patient_id, full_name, contact, age) VALUES (1, 'Legacy Alex', '111', 20)"
            )
            conn.execute(
                "INSERT INTO patients (patient_id, full_name, contact, age) VALUES (2, 'Legacy Alex', '222', 21)"
            )
            conn.execute(
                "INSERT INTO appointments (app_id, patient_id, doctor_name, app_date, status) VALUES (10, 1, 'Dr. Cruz', '2026-09-01', 'Completed')"
            )
            conn.execute(
                "INSERT INTO appointments (app_id, patient_id, doctor_name, app_date, status) VALUES (20, 2, 'Dr. Santos', '2026-09-02', 'Scheduled')"
            )
            conn.commit()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_import_legacy_data_preserves_relationships_and_ids(self) -> None:
        # Act: Execute import
        snapshot_dir = self.temp_path / "snapshots"
        result = importer.import_legacy_data(self.legacy_db_file, snapshot_dir)

        # Assert: Successful import counts
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["imported_patients"], 2)
        self.assertEqual(result["imported_appointments"], 2)

        # Assert: Preserved IDs and relationships
        p1 = Patient.objects.get(id=1)
        p2 = Patient.objects.get(id=2)
        self.assertEqual(p1.full_name, "Legacy Alex")
        self.assertEqual(p2.full_name, "Legacy Alex")

        app1 = Appointment.objects.get(id=10)
        app2 = Appointment.objects.get(id=20)
        self.assertEqual(app1.patient_id, 1)
        self.assertEqual(app1.doctor_name, "Dr. Cruz")
        self.assertEqual(app1.status, "Completed")
        self.assertEqual(app2.patient_id, 2)
        self.assertEqual(app2.doctor_name, "Dr. Santos")

    def test_import_detects_and_aborts_on_corrupt_legacy_data(self) -> None:
        # Arrange: Corrupt legacy DB with an orphaned appointment
        with closing(sqlite3.connect(str(self.legacy_db_file))) as conn:
            conn.execute("PRAGMA foreign_keys = OFF;")
            conn.execute(
                "INSERT INTO appointments (app_id, patient_id, doctor_name, app_date) VALUES (99, 999, 'Dr. Ghost', '2026-09-03')"
            )
            conn.commit()

        # Act & Assert: Must raise MigrationAnomalyError without corrupting modern database
        snapshot_dir = self.temp_path / "snapshots"
        with self.assertRaises(importer.MigrationAnomalyError) as ctx:
            importer.import_legacy_data(self.legacy_db_file, snapshot_dir)

        self.assertTrue(len(ctx.exception.anomalies) > 0)
        self.assertEqual(ctx.exception.anomalies[0]["field"], "patient_id")
