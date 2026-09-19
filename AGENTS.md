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
| **Packaging**   | PyInstaller 6.x, `package.py`              | `desktop.spec`        | Generates `.exe` (Win) or `.app` (macOS), supports `--quick` / `--clean` |
| **CI/CD**       | GitHub Actions (`ci.yml`, `release.yml`)   | `.github/workflows/`  | Multi-OS quality gates, pre-flight checks, SHA-256 release assets |
| **Task Runner** | PowerShell 7+ (`run.ps1`), Bash (`run.sh`) | Repo Root             | Unified CLI automation with `-Quick` / `--quick` iteration modes         |

---

## 3. Work Boundaries and Architectural Rules

- **Strict Service Layer Isolation**: All business logic, state machine
  transitions, and database writes must reside in `backend/clinic/services.py`
  wrapped in `transaction.atomic()`. Views in `backend/clinic/views.py` are thin
  HTTP adapters that validate requests and serialize responses.
- **Strict Working Branch Discipline & Flow Direction**:
  - Always verify the active branch with `git branch --show-current` before making
    edits or packaging.
  - `master` is the hardened, production-grade clinical core (Slices 1 to 3 + core UI).
    Never introduce unfinished experimental feature slices directly into `master`.
  - `experimental` is the active feature branch (Slices 4 to 7).
  - All bug fixes, optimizations, and invariant hardenings must be made on `master`
    first, verified against quality gates, and then rebased onto `experimental`
    (`git checkout experimental && git rebase master`).
  - **Immediate Branch Return**: After executing a downstream rebase on `experimental`,
    agents must immediately checkout `master` (`git checkout master`) unless explicitly
    instructed by the user to stay on `experimental`.
  - **No Force Pushes to Master**: Force pushes (`--force`, `--force-with-lease`) are
    strictly forbidden on `master`. `--force-with-lease` is only permitted on
    `experimental` after a verified downstream rebase.
- **Clinical Data Immutability & Deletion Protection**:
  - **Completed Visit Immutability**: Appointments in the `Completed` state represent
    official medical encounters and are legally and clinically immutable. They cannot
    be edited, rescheduled, or deleted under any circumstance.
  - **Cascade Deletion Protection**: A patient who has existing completed appointments
    or medical records cannot be deleted. Deletion requests must be rejected with an
    HTTP 400 validation error to preserve the clinical audit trail.
  - **Schedule Conflict Window**: Doctors cannot have overlapping appointments within
    a +/- 15 minute window on the same date. When rescheduling an existing appointment,
    the appointment itself must be excluded from conflict detection.
- **Zero Outer Page Scroll (Desktop Viewport Containment)**:
  - The entire desktop application must behave as a native window shell without
    outer vertical window scrolling:
    - Root layout container must use `h-screen overflow-hidden min-h-0`.
    - Main workspace container must use `flex-1 min-h-0 overflow-hidden flex flex-col`.
    - Top metrics cards and toolbars must use `shrink-0`.
    - Tables must scroll internally via `<Table containerClass="flex-1 min-h-0 overflow-y-auto">`
      with sticky headers (`sticky top-0 bg-card z-10`) and pinned pagination controls.
- **Latin-Scoped Typography**:
  - Font imports in `frontend/src/app.css` must remain strictly scoped to Latin
    subsets (`@fontsource/inter/latin-*.css`). Never import unscoped `400.css`,
    `500.css`, etc., which forces Vite to bundle 48 unused Cyrillic, Greek, and
    Vietnamese font files into `dist/assets/`.
- **Zero Em/En Dash Policy**: All code, comments, docstrings, markdown files,
  YAML workflows, and commit messages must contain strictly zero em dashes
  (`\u2014`) and en dashes (`\u2013`). Use standard double hyphens (`--`),
  colons, or parentheses instead.
- **Protected Production Database**: The database file located in the user's
  operating system directory (`%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3` on
  Windows or `~/Library/Application Support/HospitalSystem/clinic.sqlite3` on
  macOS) contains user data. Never overwrite it during tests or use it as a test
  fixture. Automated tests must execute against in-memory SQLite
  (`TESTING=True`) with 1-round PBKDF2 password hashing for sub-second execution.
- **Single Supported Frontend**: The Svelte 5 Single Page Application in
  `frontend/` is the sole production interface. All frontend dependencies are
  managed through Deno (`deno.json`). Do not introduce Node.js or `npm`.
- **Cross-Platform Compatibility**: Code paths must support both Windows
  (PowerShell, WebView2, Win32 mutex) and macOS (Bash, Apple WebKit, POSIX
  flock). Never hardcode Windows-only path separators or commands without
  platform checks.
- **CI/CD Pipeline and Release Invariants**:
  - **Release Naming Convention**: All releases published via GitHub Actions must
    be named `Release vX.Y.Z` (e.g. `Release v0.0.1`), never `(Project Name) vx.x.x`.
  - **Mandatory Pre-Flight Gate**: The `release.yml` pipeline executes all 6 quality
    gates and verifies SemVer tag compliance (`^v[0-9]+\.[0-9]+\.[0-9]+.*$`) before
    invoking multi-platform build runners.
  - **Cross-Platform Bundle Verification**:
    - Windows builds are verified via `desktop/verify_bundle.py`.
    - macOS application bundles are verified via `dist/HospitalSystem.app/Contents/MacOS/HospitalSystem --verify`.
  - **Artifact Integrity & Checksums**: Every release must generate `SHA256SUMS.txt`
    containing SHA-256 digests for all attached binaries, accompanied by an inline
    verification markdown table in the release notes.
  - **Concurrency Protection**: Releases serialize on `release-${{ github.ref_name }}`
    to eliminate parallel publishing races and duplicated release notes.

---

## 4. Verification and Quality Gates

### Rapid Inner-Loop Iteration (TDD & Fast Packaging)
During active development, use fast modes to keep feedback turnaround under 2 seconds:
- **Fast Test Loop (~1.0s)** (sub-second pytest without basedpyright):
  ```bash
  .\run.ps1 test -Quick       # Windows (PowerShell)
  ./run.sh test --quick       # macOS / Linux (Bash)
  uv run pytest backend/tests/ -v
  ```
- **Fast Desktop Packaging (~10-15s)** (reuses PyInstaller cache & skips Deno if built):
  ```bash
  .\run.ps1 package -Quick    # Windows (PowerShell)
  ./run.sh package --quick    # macOS / Linux (Bash)
  ```

### Authoritative Quality Gates
Before concluding any task, submitting changes, or approving Pull Requests,
agents must execute and pass the full 6-gate verification:

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
5. **Zero Em/En Dash Compliance**:
   ```bash
   python -c "import os; [print(f'Dash in {f}') for r, _, fs in os.walk('.') if not any(ign in r for ign in ['.git', '.venv', 'dist', 'build', 'node_modules', '.gemini']) for fn in fs for f in [os.path.join(r, fn)] if f.endswith(('.py', '.svelte', '.ts', '.css', '.ps1', '.sh', '.md', '.json', '.html')) if '\u2014' in open(f, 'r', encoding='utf-8', errors='ignore').read() or '\u2013' in open(f, 'r', encoding='utf-8', errors='ignore').read()]; print('Dash check completed.')"
   ```
6. **Standalone Bundle Bootstrapping & Verification**:
   ```bash
   .venv/Scripts/python.exe desktop/verify_bundle.py   # Windows
   .venv/bin/python desktop/verify_bundle.py          # macOS
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
  - Test Suite: **76 passing tests** in `backend/tests/` (100% pass rate).

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

## 6. GitHub CLI Pull Request Review Protocol

When requested to review or evaluate Pull Requests on GitHub using the `gh` CLI:

1. **Inspect PR and CI Status**:
   ```bash
   gh pr status
   gh pr view <pr-number>
   gh pr checks <pr-number>
   ```
2. **Inspect Exact Diff**:
   ```bash
   gh pr diff <pr-number>
   ```
3. **Mandatory Approval Conditions**:
   Agents are authorized by the maintainer to approve Pull Requests provided that:
   - All GitHub Actions CI checks (`gh pr checks`) are green.
   - Strictly zero em dashes (`\u2014`) and en dashes (`\u2013`) exist in the PR diff or commit messages.
   - Strict `basedpyright` type checks pass with 0 errors.
   - All backend tests pass with 100% pass rate.
   - Code strictly adheres to service layer isolation (writes in `services.py` with `transaction.atomic()`).
   - Architectural invariants (completed visit immutability, cascade deletion protection, viewport containment) are preserved.
4. **Submit Approval**:
   ```bash
   gh pr review <pr-number> --approve --body "Reviewed and verified across all repository quality gates and architectural invariants."
   ```

---

## 7. Bundled Skills and Agent Workflows

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
