# Experimental Branch Task List: Stabilization & Comprehensive UI/UX Polish

This task list tracks discrete, one-at-a-time engineering tasks for the
`experimental` branch. Its objective is to fix all authentication, API, and
state bugs discovered during manual testing, while standardizing and polishing
all UI/UX workflows to use standard default shadcn-svelte components.

---

## Progress Overview

- Total Tasks: 16
- Completed: 8
- In Progress: 0
- Remaining: 8

---

## Phase 1: Baseline Staff Seeding & Database Bootstrapping

- [x] **Task 1.1: Implement Default Staff Auto-Seeding Service**
  - File: `backend/clinic/services.py`
  - Implement `ensure_default_staff()` wrapped in `transaction.atomic()`.
  - Automatically create baseline staff accounts (`maria`, `dreyes`, `dsantos`, `dtan`) if missing from database.
  - Re-link unassigned legacy appointments matching doctor names (`doctor_id=None` but `doctor_name='Dr. Elena Reyes'`).
  - Add dedicated unit tests in `backend/tests/test_auth.py` to prove idempotent auto-seeding.

- [x] **Task 1.2: Repair Staff Seeding Guard in Seed Command**
  - File: `backend/clinic/management/commands/seed.py`
  - Reorder seeding execution so staff accounts are guaranteed to seed even when existing patients are already present in the database.

- [x] **Task 1.3: Hook Default Staff Seeding into Desktop Launcher and Health Check**
  - Files: `desktop/launcher.py`, `backend/clinic/views.py`
  - In `desktop/launcher.py`, call `services.ensure_default_staff()` immediately after `call_command("migrate")`.
  - In `health_check()` view, call `services.ensure_default_staff()` when `not settings.TESTING`.

---

## Phase 2: Frontend API Client Harmonization & Robustness

- [x] **Task 2.1: Support Flexible Arguments & Session Storage in `api.auth.login`**
  - File: `frontend/src/lib/api.ts`
  - Update `api.auth.login` to accept both positional arguments `(username, password)` and object `{ username, password }`.
  - Ensure returned session token is persisted in storage and attached to subsequent request headers.

- [x] **Task 2.2: Fix Return Value Unwrapping in `api.auth.updateProfile`**
  - File: `frontend/src/lib/api.ts`
  - Ensure `updateProfile` resolves cleanly with `StaffUser` directly (or unwraps `res.user`), preventing session state corruption in caller.

- [x] **Task 2.3: Harmonize Clinical Conflict Check and Doctor Queue Methods**
  - File: `frontend/src/lib/api.ts`
  - Expose `checkScheduleConflict` under both `api` and `api.clinical` supporting `(doctorId, dateStr, timeStr?, duration?, excludeId?)`.
  - Support optional physician ID in `getDoctorQueue(doctorIdOrDate?, dateStr?)` and `getDoctorPatients(doctorIdOrQuery?, query?)` so callers passing doctor ID do not corrupt query parameters.

---

## Phase 3: Auth Flow & Modal State Corrections

- [x] **Task 3.1: Auto-Login on Registration & Shadcn Styling in `AuthModal.svelte`**
  - File: `frontend/src/components/AuthModal.svelte`
  - Fix crash on registration: await registration, then immediately invoke `api.auth.login(username, password)` to establish session and pass authenticated user to `onSuccess`.
  - Replace raw HTML quick-fill buttons with standard shadcn `<Button variant="outline" size="sm">`.
  - Standardize role selection and inputs using shadcn styling conventions.
  - Convert `space-y-*` classes to `flex flex-col gap-3.5`.

- [x] **Task 3.2: Prevent User State Corruption in `SettingsDialog.svelte`**
  - File: `frontend/src/components/SettingsDialog.svelte`
  - Ensure `onProfileUpdated` receives the unwrapped `StaffUser` object, preserving `currentUser.role` and preventing UI state collapse.
  - Standardize logout button with `variant="destructive"` and demo mode toggle controls.

---

## Phase 4: Clinical Appointments & Queue Engine

- [ ] **Task 4.1: Fix Schedule Conflict Check in `EditAppointmentDialog.svelte`**
  - File: `frontend/src/components/EditAppointmentDialog.svelte`
  - Correct argument order when calling `api.clinical.checkScheduleConflict`: pass `(selectedDoctorId, appDate, appTime, 15, appointment.id)` so the appointment is excluded from its own conflict check.
  - Auto-select doctor ID by doctor name matching if `appointment.doctor_id` is missing.

- [ ] **Task 4.2: Enable Legacy Appointment Visibility in Doctor Services**
  - File: `backend/clinic/services.py`
  - Update `get_doctor_queue` and `get_doctor_patients` to query `Q(doctor_id=doctor_id) | Q(doctor_name__iexact=doc.full_name)` so legacy appointments appear in the doctor roster and queue.

- [ ] **Task 4.3: Verify Receptionist Triage & Walk-In Actions**
  - File: `frontend/src/components/AppointmentsWorkspace.svelte`
  - Ensure "Book & Check In" creates appointment with initial status `Checked In`.
  - Ensure in-table "Check In" action for `Scheduled` appointments transitions them to `Checked In` for the waiting room.

---

## Phase 5: Comprehensive UI/UX Polish & Shadcn Standardization

- [ ] **Task 5.1: Polish Navigation, Header, and Role Switcher in `App.svelte`**
  - File: `frontend/src/App.svelte`
  - Standardize sidebar navigation with shadcn `<Button variant={active ? "secondary" : "ghost"}>` with icons, badges, and smooth transitions.
  - Standardize quick action CTA button with shadcn `<Button variant="default">`.
  - Refactor top bar 1-click demo switcher using shadcn button variants instead of raw `<button>` elements and hardcoded colors.
  - Clean active user footer card with avatar initials and role badge.

- [ ] **Task 5.2: Polish Doctor Workspace & Waiting Room Experience**
  - File: `frontend/src/components/DoctorWorkspace.svelte`
  - Refactor top metrics cards to use clean semantic styling with icons and status indicators.
  - Polish waiting room triage cards with queue numbers, timestamps, complaint quotes, and standard shadcn buttons ("Chart", "Begin Consultation").
  - Polish active consultation banner and today's schedule table.
  - Eliminate all hardcoded palette colors (`bg-purple-700`, `bg-emerald-600`) in favor of semantic design tokens.

- [ ] **Task 5.3: Polish Receptionist Appointments & Triage Workspace**
  - File: `frontend/src/components/AppointmentsWorkspace.svelte`
  - Refactor booking modal with clean form fields, date picker, time picker, and real-time conflict alert banner.
  - Refactor appointment status badges and table action buttons ("Check In", "Edit", "Cancel").
  - Standardize filter tabs and search bar.

- [ ] **Task 5.4: Polish Consultation (SOAP) & Patient Chart Dialogs**
  - Files: `frontend/src/components/ConsultationDialog.svelte`, `frontend/src/components/PatientChartDialog.svelte`
  - Refactor SOAP inputs (Diagnosis, Symptoms, Notes, Rx, Advice) with clean form layouts and validation feedback.
  - Add collapsible past medical history accordion in consultation dialog.
  - Polish patient chart timeline with visit dates, attending doctor badges, and prescription notes.

---

## Phase 6: Quality Gates & Verification

- [ ] **Task 6.1: Run Backend Quality Gates**
  - Run fast test suite: `uv run pytest backend/tests/ -v`.
  - Run strict type checking: `.venv/Scripts/python.exe -m basedpyright` (0 errors).
  - Run style checks: `uv run ruff check backend desktop package.py` and `uv run ruff format --check backend desktop package.py`.

- [ ] **Task 6.2: Run Frontend Build & System Quality Gates**
  - Run Deno build: `cd frontend && deno task build && cd ..`.
  - Run zero em/en dash verification script across the entire repository.
  - Run standalone bundle verification: `.venv/Scripts/python.exe desktop/verify_bundle.py`.
