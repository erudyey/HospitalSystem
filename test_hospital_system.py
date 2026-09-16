"""Regression tests for the SQLite storage layer."""

import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

import database as db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = Path(self.temporary_directory.name) / "clinic.db"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.temporary_directory.cleanup()

    def test_duplicate_names_keep_separate_appointments(self):
        first_patient = db.add_patient("Alex Reyes", "09170000001", 20)
        second_patient = db.add_patient("Alex Reyes", "09170000002", 21)
        db.add_appointment(first_patient, "Dr. Santos", "2026-09-17")
        db.add_appointment(second_patient, "Dr. Cruz", "2026-09-18")

        self.assertEqual(db.get_appointments_by_patient(first_patient)[0][3], "Dr. Santos")
        self.assertEqual(db.get_appointments_by_patient(second_patient)[0][3], "Dr. Cruz")

    def test_appointment_status_updates(self):
        patient_id = db.add_patient("Sam Lee", "09170000003", 22)
        appointment_id = db.add_appointment(patient_id, "Dr. Santos", "2026-09-17")

        self.assertTrue(db.update_appointment_status(appointment_id, "Completed"))
        self.assertEqual(db.get_appointments_by_patient(patient_id)[0][-1], "Completed")
        self.assertFalse(db.update_appointment_status(9999, "Cancelled"))

    def test_missing_patient_is_rejected_by_foreign_key(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.add_appointment(9999, "Dr. Santos", "2026-09-17")

    def test_database_path_is_independent_of_working_directory(self):
        original_directory = Path.cwd()
        os.chdir(self.temporary_directory.name)
        try:
            patient_id = db.add_patient("Taylor Kim", "09170000004", 23)
        finally:
            os.chdir(original_directory)

        self.assertTrue(db.DB_PATH.exists())
        self.assertEqual(db.get_all_patients(), [(patient_id, "Taylor Kim", "09170000004", 23)])


if __name__ == "__main__":
    unittest.main()
