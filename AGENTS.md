# HospitalSystem Contributor and Agent Entry Point

This document serves as the authoritative entry point for AI agents and human
contributors working on the HospitalSystem codebase.

---

## 1. Reading Order and Documentation Map

1. Read [README.md](README.md) for the runnable application overview, toolchain
   requirements, and task runner commands.
2. Read [PRD.md](PRD.md) for the product scope, core personas (Receptionist and
   Doctor), and release milestones.
3. Read [ARCHITECTURE.md](ARCHITECTURE.md) and
   [docs/system-architecture.md](docs/system-architecture.md) before modifying
   application structure, persistence, or network boundaries.
4. Read [docs/overview.md](docs/overview.md) for clinical operational models and
   front-desk workflows.
5. Read [docs/api-contracts.md](docs/api-contracts.md) for REST API
   specifications, error formats, and validation rules.
6. Read [docs/development.md](docs/development.md) for the local development
   runbook, testing commands, and database seeding procedures.
7. Read [DATA.md](DATA.md) for database schema, SQLite WAL engine settings, and
   storage boundary rules.
8. Read [SKILLS.md](SKILLS.md) for the repository's bundled agent skills catalog
   and workflow runbooks.
9. Read [ROADMAP.md](ROADMAP.md) (or [TODO.md](TODO.md)) for decoupled task
   slices, progress tracking, and active implementation status.
10. Read [docs/git-cheatsheet.md](docs/git-cheatsheet.md) for team Git workflow,
    atomic commit rules, and safe collaboration practices.

---

## 2. Technology Stack and Directory Structure

| Layer           | Technology                                 | Key Location          | Notes                                     |
| :-------------- | :----------------------------------------- | :-------------------- | :---------------------------------------- |
| **Backend**     | Python 3.12+, Django 6.x, Waitress WSGI    | `backend/clinic/`     | Business logic, ORM models, REST views    |
| **Frontend**    | Svelte 5, Tailwind CSS, shadcn-svelte      | `frontend/src/`       | Deno 2 build pipeline (zero Node.js)      |
| **Desktop**     | `pywebview` 6.x (WebView2 / WebKit)        | `desktop/launcher.py` | Single-instance lock, loopback token auth |
| **Persistence** | SQLite with WAL mode & foreign keys        | OS AppData / Library  | Production database: `clinic.sqlite3`     |
| **Packaging**   | PyInstaller 6.x, `package.py`              | `desktop.spec`        | Generates `.exe` (Win) or `.app` (macOS)  |
| **Task Runner** | PowerShell 7+ (`run.ps1`), Bash (`run.sh`) | Repo Root             | Unified CLI task automation               |

---

## 3. Work Boundaries and Architectural Rules

- **Strict Service Layer Isolation**: All business logic, state machine
  transitions, and database writes must reside in `backend/clinic/services.py`
  wrapped in `transaction.atomic()`. Views in `backend/clinic/views.py` are thin
  HTTP adapters that validate requests and serialize responses.
- **Zero Em/En Dash Policy**: All code, comments, docstrings, markdown files,
  YAML workflows, and commit messages must contain strictly zero em dashes
  (`\u2014`) and en dashes (`\u2013`). Use standard double hyphens (`--`),
  colons, or parentheses instead.
- **Protected Production Database**: The database file located in the user's
  operating system directory (`%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3` on
  Windows or `~/Library/Application Support/HospitalSystem/clinic.sqlite3` on
  macOS) contains user data. Never overwrite it during tests or use it as a test
  fixture. Automated tests must execute against in-memory SQLite
  (`TESTING=True`).
- **Single Supported Frontend**: The Svelte 5 Single Page Application in
  `frontend/` is the sole production interface. All frontend dependencies are
  managed through Deno (`deno.json`). Do not introduce Node.js or `npm`.
- **Cross-Platform Compatibility**: Code paths must support both Windows
  (PowerShell, WebView2, Win32 mutex) and macOS (Bash, Apple WebKit, POSIX
  flock). Never hardcode Windows-only path separators or commands without
  platform checks.

---

## 4. Verification and Quality Gates

Before concluding any development task or submitting changes, agents must
execute and pass the following quality gates:

1. **Unit and Integration Tests**:
   ```bash
   uv run pytest backend/tests/ -v
   ```
2. **Code Style and Formatting**:
   ```bash
   uv run ruff check backend desktop package.py
   uv run ruff format --check backend desktop package.py
   ```
3. **Strict Python Type Checking**:
   ```bash
   .venv/Scripts/python.exe -m basedpyright   # Windows
   .venv/bin/python -m basedpyright          # macOS / Linux
   ```
4. **Frontend Build & Format**:
   ```bash
   cd frontend && deno task build && cd ..
   deno fmt .github/workflows/
   ```

---

## 5. Current Active Milestone: Role-Based Clinical Hospital System

The system is transitioning from a single-window desktop baseline into a dual-role
hospital management application with separate workspaces for **Receptionists** and
**Doctors**.

### What Has Been Completed (Slices 1 to 3 -- 100% Backend Complete)

- **Slice 1: Database Schema & Migrations**:
  - Models: `StaffRole`, `StaffUser` (PBKDF2 passwords), `UserSession` (URL tokens),
    `MedicalRecord` (SOAP notes).
  - Enriched `Appointment`: added `app_time` (`TimeField`), `reason_for_visit`,
    `doctor` FK, and 5-state lifecycle (`Scheduled`, `Checked In`,
    `In Consultation`, `Completed`, `Cancelled`).
  - Migration `0002` applied and verified.
- **Slice 2: Authentication & Staff Service Layer**:
  - Services: `register_staff()`, `authenticate_staff()`, `validate_session()`,
    `logout_staff()`, `update_staff_profile()`, `list_doctors()`.
  - Endpoints: `/api/auth/register/`, `/api/auth/login/`, `/api/auth/me/`,
    `/api/auth/logout/`, `/api/auth/profile/`, `/api/doctors/`.
- **Slice 3: Clinical Logic & Schedule Conflict Engine**:
  - Services: `check_schedule_conflict()` (+/- 15 min overlap detection),
    `update_appointment_status()` (5-state lifecycle matrix, immutable completed
    records, protected deletion), `get_doctor_queue()`, `get_doctor_patients()`,
    `create_medical_record()`, `update_medical_record()`.
  - Endpoints: `/api/appointments/conflict-check/`, `/api/doctor/queue/`,
    `/api/doctor/patients/`, `/api/doctor/appointments/`, `/api/medical-records/`,
    `/api/patients/<id>/medical-records/`.
  - Test Suite: **64 passing tests** in `backend/tests/` (100% pass rate).

### What Is In Progress and Yet to Be Done (Slices 4 to 7)

1. **Slice 4: Receptionist Workspace UI**:
   - Files: `frontend/src/components/AppointmentsWorkspace.svelte`,
     `EditAppointmentDialog.svelte`, `frontend/src/lib/api.ts`.
   - Tasks: Doctor dropdown from `/api/doctors/`, time input `<Input type="time">`,
     real-time schedule conflict warning banner, "Book & Check In" triage action,
     and waiting room "Check In" table action button.
2. **Slice 5: Doctor Workspace UI**:
   - Files: `frontend/src/components/DoctorWorkspace.svelte`,
     `ConsultationDialog.svelte`, `PatientChartDialog.svelte`.
   - Tasks: Tabbed physician dashboard (Waiting Room queue, today's schedule,
     my patients roster, clinical notes log), SOAP consultation dialog
     (Diagnosis, Symptoms, Notes, Prescription, Follow-up), and patient chart.
3. **Slice 6: Auth Gateway & Settings Suite**:
   - Files: `frontend/src/components/AuthModal.svelte`, `SettingsDialog.svelte`,
     `frontend/src/App.svelte`.
   - Tasks: Sign In / Register staff modal with demo quick-fill buttons, unified
     Settings dialog with Demo Mode toggle, and role-based workspace mounting.
4. **Slice 7: Seed Data & Final Packaging Proof**:
   - Files: `backend/clinic/management/commands/seed.py`, `docs/`, `package.py`.
   - Tasks: Multi-role seed data fixtures, documentation sync, and standalone
     `.exe` bundle verification.

---

## 6. Bundled Skills and Agent Workflows

The repository bundles core engineering skills under `.agents/skills/`:

- **ponytail**: Enforces code minimalism and YAGNI. Reject premature
  abstractions.
- **git-maestro**: Standards for atomic commits and Conventional Commits
  formatting.
- **shadcn-svelte**: Best practices for Svelte 5 runes, bits-ui, and Tailwind
  styling.
- **test-master**: Guidelines for high-coverage, deterministic pytest fixtures.
- **surgical-patch**: Narrow bug fixes and behavioral changes at the responsible
  layer.
- **verify-and-stop**: Rigorous proof across quality gates without expanding
  scope.
- **security-reviewer**: Security auditing for authentication, tokens, and data
  access.
- **investigate-first**: Diagnostic root-cause investigation prior to code
  edits.

Consult [SKILLS.md](SKILLS.md) for full descriptions and usage patterns.
