"""SQLite storage for the hospital management application."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name("clinic.db")


def get_connection() -> sqlite3.Connection:
    """Return a connection with foreign-key checks enabled."""
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """Commit successful work, roll back errors, and always close the connection."""
    with closing(get_connection()) as connection:
        try:
            yield connection
        except sqlite3.Error:
            connection.rollback()
            raise
        else:
            connection.commit()


def init_db() -> None:
    """Create the application tables when they do not already exist."""
    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                contact TEXT,
                age INTEGER
            );

            CREATE TABLE IF NOT EXISTS appointments (
                app_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                doctor_name TEXT NOT NULL,
                app_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Scheduled',
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
            );
            """
        )


def add_patient(full_name: str, contact: str, age: int) -> int:
    """Add a patient and return the new patient ID."""
    with database_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO patients (full_name, contact, age) VALUES (?, ?, ?)",
            (full_name, contact, age),
        )
        return cursor.lastrowid


def get_all_patients() -> list[tuple[int, str, str, int]]:
    """Return patients ordered by their IDs."""
    with database_connection() as connection:
        return connection.execute(
            "SELECT patient_id, full_name, contact, age FROM patients ORDER BY patient_id"
        ).fetchall()


def add_appointment(patient_id: int, doctor_name: str, appointment_date: str) -> int:
    """Add an appointment for a patient ID and return its appointment ID."""
    with database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO appointments (patient_id, doctor_name, app_date)
            VALUES (?, ?, ?)
            """,
            (patient_id, doctor_name, appointment_date),
        )
        return cursor.lastrowid


def get_appointments_by_patient(
    patient_id: int,
) -> list[tuple[int, str, str, str, str, str]]:
    """Return a patient's appointments with the patient details."""
    with database_connection() as connection:
        return connection.execute(
            """
            SELECT a.app_id, p.full_name, p.contact, a.doctor_name, a.app_date, a.status
            FROM appointments AS a
            JOIN patients AS p ON p.patient_id = a.patient_id
            WHERE p.patient_id = ?
            ORDER BY a.app_id
            """,
            (patient_id,),
        ).fetchall()


def update_appointment_status(appointment_id: int, status: str) -> bool:
    """Set an appointment's status and return whether it was found."""
    with database_connection() as connection:
        cursor = connection.execute(
            "UPDATE appointments SET status = ? WHERE app_id = ?",
            (status, appointment_id),
        )
        return cursor.rowcount == 1
