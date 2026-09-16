# Hospital Management System

A desktop coursework application for registering patients and managing their appointments.

## Features

- Register patients with a name, contact detail, and age.
- Book appointments for a selected patient.
- View a patient's appointments and mark them completed or cancelled.
- View all registered patient records.
- Store data locally in SQLite.

## Requirements

- Python 3 with Tkinter support.

## Run

From this folder, run:

```powershell
python main.py
```

The application creates `clinic.db` automatically beside the source files. The database is local application data and is not tracked by Git.

## Project layout

- `main.py` starts the application.
- `gui.py` contains the Tkinter interface.
- `database.py` contains the SQLite queries and schema setup.
- `test_hospital_system.py` contains automated regression tests.

## Usage

1. Register a patient in **Patient Registration**.
2. Select that patient by name and ID in **Book Appointment**.
3. Select the patient in **Appointment Status** to view or update appointments.
4. Use **Patient Records** to view all registrations.

## Current limitations

This is a local single-user desktop application. It does not include authentication, appointment conflict checks, editing or deleting records, or remote backup.
