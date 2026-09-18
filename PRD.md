# Product Requirements Document (PRD): Hospital Management System

This document outlines the product scope, core personas, clinical workflows, and
release milestones for the Hospital Management System.

---

## 1. Product Summary

The Hospital Management System is a local-first desktop application designed for
outpatient clinics and healthcare facilities. It operates completely offline on
Windows and macOS without requiring external servers, internet access, or cloud
dependencies. All clinical and operational data is persisted locally in an
embedded SQLite database in Write-Ahead Logging (WAL) mode.

---

## 2. Core Personas and Operational Workflows

### Persona 1: Clinic Receptionist (Front Desk & Triage)

- **Primary Goal**: Rapid patient registration, queue intake, and conflict-free
  appointment booking.
- **Key Workflows**:
  1. **Patient Intake**: Register new patients with full name, contact details,
     and age. Support duplicate patient names while maintaining unique numeric
     patient IDs.
  2. **Appointment Scheduling**: Book appointments with specific doctors,
     selecting both date and time slot, while capturing the patient's chief
     complaint or reason for visit.
  3. **Schedule Conflict Prevention**: Receive immediate alerts if a doctor
     already has an active appointment in the requested time slot.
  4. **Waiting Room Check-In**: Mark arriving patients as `Checked In`,
     instantly notifying the attending doctor via their live waiting queue.

### Persona 2: Attending Physician / Doctor

- **Primary Goal**: Efficient patient consultation, review of past medical
  history, and documentation of clinical diagnoses and prescriptions.
- **Key Workflows**:
  1. **Live Waiting Queue**: View all currently checked-in patients awaiting
     consultation, prioritized by arrival time.
  2. **Patient Medical Chart Review**: Review complete chronological visit
     history, previous diagnoses, and past medications before or during an exam.
  3. **Clinical Documentation**: Document primary diagnosis, symptoms, clinical
     findings (vitals/physical exam), and prescribed treatment plan.
  4. **Consultation Finalization**: One-click completion that updates
     appointment status to `Completed`, archives the medical record, and
     recommends follow-up.

---

## 3. Product Milestones

### Milestone 1: Modern Single-Binary Desktop Baseline (Completed -- v0.0.1)

- **Backend**: Headless Django application running on embedded Waitress WSGI on
  local loopback (`127.0.0.1`).
- **Frontend**: Svelte 5 Single Page Application styled with Tailwind CSS and
  official shadcn-svelte UI components, bundled using Deno 2 (zero Node.js).
- **Desktop Shell**: Native `pywebview` window (Microsoft Edge WebView2 on
  Windows, Apple WebKit on macOS).
- **Packaging & CI/CD**: PyInstaller bundling with automated verification and
  cross-platform GitHub Actions release publishing.
- **Seed Utility**: Management command to populate realistic sample data into
  the OS-specific application directory.

### Milestone 2: Role-Based Clinical Hospital System (In Progress)

- **Staff Authentication**:
  - Secure credential storage using PBKDF2-SHA256 password hashing.
  - Role-based access control distinguishing `Receptionist` and `Doctor` users.
  - Profile modification and password change capabilities.
- **Dual Workspaces**:
  - **Receptionist Workspace**: Directory search, patient registration,
    appointment scheduling with date/time granularity, and front-desk check-in.
  - **Doctor Workspace**: Live waiting room queue, doctor-specific schedules,
    assigned patient roster, and clinical records management.
- **Clinical Records & Diagnoses**:
  - Structured SOAP-lite consultation documentation (Chief Complaint, Clinical
    Notes, Primary Diagnosis, Prescription, Follow-up Advice).
  - Chronological patient medical history chart.
- **Scheduling Refinement**:
  - Date and time slot granularity (`app_date` + `app_time`).
  - Schedule conflict detection for attending doctors.
  - Expanded appointment state machine (`Scheduled` -> `Checked In` ->
    `In Consultation` -> `Completed` / `Cancelled`).

---

## 4. Non-Functional Requirements and Guardrails

1. **Local-First Privacy**: Patient records and clinical notes must never leave
   the local machine. No external telemetry, third-party analytics, or cloud
   sync.
2. **Data Safety**: The production database located in OS application
   directories (`%LOCALAPPDATA%` on Windows, `~/Library/Application Support` on
   macOS) must never be used as a test fixture or overwritten during testing.
3. **Deterministic Testing**: Automated test suites must run against isolated
   in-memory SQLite databases (`TESTING=True`).
4. **Clean Code and Style**: Strict adherence to zero em/en dash conventions,
   Ruff linting and formatting standards, and strict Python typing with
   basedpyright.
