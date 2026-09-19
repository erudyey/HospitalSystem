# Experimental Branch Task List: Stabilization & Shadcn Standardization

This task list tracks discrete, one-at-a-time engineering tasks for the
`experimental` branch. Its objective is to fix all authentication, API, and
state bugs discovered during manual testing, while standardizing all UI
elements to use standard default shadcn-svelte components.

---

## Progress Overview

- Total Tasks: 12
- Completed: 0
- In Progress: 0
- Remaining: 12

---

## Phase 1: Baseline Staff Seeding & Database Bootstrapping

- [ ] **Task 1.1: Implement Default Staff Auto-Seeding Service**
  - File: `backend/clinic/services.py`
  - Implement `ensure_default_staff()` inside `transaction.atomic()`.
  - Automatically create baseline staff accounts (`maria`, `dreyes`, `dsantos`, `dtan`) if `StaffUser.objects.count() == 0`.
  - Re-link unassigned appointments to corresponding doctors by name matching.
  - Verify with a dedicated unit test in `backend/tests/test_auth.py`.

- [ ] **Task 1.2: Repair Staff Seeding Guard in Seed Command**
  - File: `backend/clinic/management/commands/seed.py`
  - Reorder seeding execution so staff accounts are guaranteed to seed even when existing patients are present in the database.

- [ ] **Task 1.3: Hook Default Staff Seeding into Desktop Launcher and Health Check**
  - Files: `desktop/launcher.py`, `backend/clinic/views.py`
  - In `desktop/launcher.py`, call `services.ensure_default_staff()` immediately after `call_command("migrate")`.
  - In `health_check()` view, call `services.ensure_default_staff()` when `not settings.TESTING`.

---

## Phase 2: Frontend API Client Harmonization

- [ ] **Task 2.1: Support Flexible Credentials in `api.auth.login`**
  - File: `frontend/src/lib/api.ts`
  - Update `api.auth.login` to accept both positional arguments `(username, password)` and object `{ username, password }`.
  - Ensure compatibility with both callers without breaking changes.

- [ ] **Task 2.2: Harmonize Clinical Conflict Check and Doctor Queue Methods**
  - File: `frontend/src/lib/api.ts`
  - Expose `checkScheduleConflict` under `api.clinical` and support flexible argument ordering `(doctorId, dateStr, timeStr?, durationOrExcludeId?, excludeId?)`.
  - Support optional physician ID in `getDoctorQueue` and `getDoctorPatients`.

---

## Phase 3: Auth & Modal State Corrections

- [ ] **Task 3.1: Auto-Login on Registration & Component Hardening in `AuthModal.svelte`**
  - File: `frontend/src/components/AuthModal.svelte`
  - Handle registration response correctly without accessing undefined nested properties.
  - Automatically invoke `api.auth.login` upon registration and pass authenticated user to `onSuccess`.
  - Replace raw HTML buttons with standard shadcn `<Button>` components (`variant="outline"`, `variant="default"`, `size="sm"`).
  - Convert `space-y-*` layout classes to `flex flex-col gap-3.5`.

- [ ] **Task 3.2: Fix User State Corruption in `SettingsDialog.svelte`**
  - File: `frontend/src/components/SettingsDialog.svelte`
  - Extract `updated.user` when invoking `onProfileUpdated` to prevent state nesting in `currentUser`.

---

## Phase 4: Clinical Appointments & Queue Repairs

- [ ] **Task 4.1: Fix Schedule Conflict Check in `EditAppointmentDialog.svelte`**
  - File: `frontend/src/components/EditAppointmentDialog.svelte`
  - Correct argument order when calling `api.clinical.checkScheduleConflict`.
  - Auto-select doctor ID by doctor name if `appointment.doctor_id` is missing.

- [ ] **Task 4.2: Enable Legacy Appointment Visibility in Doctor Services**
  - File: `backend/clinic/services.py`
  - Update `get_doctor_queue` and `get_doctor_patients` to query `Q(doctor_id=doctor_id) | Q(doctor_name__iexact=doc.full_name)` so pre-existing appointments appear in the doctor's roster and queue.

---

## Phase 5: Shadcn UI Standardization & Semantic Styling

- [ ] **Task 5.1: Standardize Header, Navigation, and Role Switcher in `App.svelte`**
  - File: `frontend/src/App.svelte`
  - Replace raw `<button>` elements in sidebar, quick switcher, and header with standard shadcn `<Button>` and `<Badge>`.
  - Replace hardcoded palette colors (such as `bg-purple-700`) with semantic design tokens (`bg-primary`, `variant="secondary"`, `variant="ghost"`).

- [ ] **Task 5.2: Audit Workspaces for Standard Shadcn Consistency**
  - Files: `frontend/src/components/AppointmentsWorkspace.svelte`, `frontend/src/components/DoctorWorkspace.svelte`
  - Verify all action buttons, dialogs, badges, and tabs adhere strictly to standard shadcn-svelte conventions.

---

## Phase 6: Quality Gates & Verification

- [ ] **Task 6.1: Run Backend Quality Gates**
  - Run fast test suite: `uv run pytest backend/tests/ -v`.
  - Run type checking: `.venv/Scripts/python.exe -m basedpyright` (0 errors).
  - Run style checks: `uv run ruff check backend desktop package.py` and `uv run ruff format --check backend desktop package.py`.

- [ ] **Task 6.2: Run Frontend Build & System Quality Gates**
  - Run Deno build: `cd frontend && deno task build && cd ..`.
  - Run zero em/en dash verification script across the entire repository.
  - Run standalone bundle verification: `.venv/Scripts/python.exe desktop/verify_bundle.py`.
