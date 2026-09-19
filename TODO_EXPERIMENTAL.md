# Experimental Branch Task List: Stabilization & Comprehensive UI/UX Polish

This task list tracks discrete, one-at-a-time engineering tasks for the
`experimental` branch. Its objective is to fix all authentication, API, and
state bugs discovered during manual testing, while standardizing and polishing
all UI/UX workflows to use standard default shadcn-svelte components.

---

## Progress Overview

- Total Tasks: 30
- Completed: 26
- In Progress: 1
- Remaining: 3

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

- [x] **Task 4.1: Fix Schedule Conflict Check in `EditAppointmentDialog.svelte`**
  - File: `frontend/src/components/EditAppointmentDialog.svelte`
  - Correct argument order when calling `api.clinical.checkScheduleConflict`: pass `(selectedDoctorId, appDate, appTime, 15, appointment.id)` so the appointment is excluded from its own conflict check.
  - Auto-select doctor ID by doctor name matching if `appointment.doctor_id` is missing.

- [x] **Task 4.2: Enable Legacy Appointment Visibility in Doctor Services**
  - File: `backend/clinic/services.py`
  - Update `get_doctor_queue` and `get_doctor_patients` to query `Q(doctor_id=doctor_id) | Q(doctor_name__iexact=doc.full_name)` so legacy appointments appear in the doctor roster and queue.

- [x] **Task 4.3: Verify Receptionist Triage & Walk-In Actions**
  - File: `frontend/src/components/AppointmentsWorkspace.svelte`
  - Ensure "Book & Check In" creates appointment with initial status `Checked In`.
  - Ensure in-table "Check In" action for `Scheduled` appointments transitions them to `Checked In` for the waiting room.

---

## Phase 5: Comprehensive UI/UX Polish & Shadcn Standardization

- [x] **Task 5.1: Polish Navigation, Header, and Role Switcher in `App.svelte`**
  - File: `frontend/src/App.svelte`
  - Standardize sidebar navigation with shadcn `<Button variant={active ? "secondary" : "ghost"}>` with icons, badges, and smooth transitions.
  - Standardize quick action CTA button with shadcn `<Button variant="default">`.
  - Refactor top bar 1-click demo switcher using shadcn button variants instead of raw `<button>` elements and hardcoded colors.
  - Clean active user footer card with avatar initials and role badge.

- [x] **Task 5.2: Polish Doctor Workspace & Waiting Room Experience**
  - File: `frontend/src/components/DoctorWorkspace.svelte`
  - Refactor top metrics cards to use clean semantic styling with icons and status indicators.
  - Polish waiting room triage cards with queue numbers, timestamps, complaint quotes, and standard shadcn buttons ("Chart", "Begin Consultation").
  - Polish active consultation banner and today's schedule table.
  - Eliminate all hardcoded palette colors (`bg-purple-700`, `bg-emerald-600`) in favor of semantic design tokens.

- [x] **Task 5.3: Polish Receptionist Appointments & Triage Workspace**
  - File: `frontend/src/components/AppointmentsWorkspace.svelte`
  - Refactor booking modal with clean form fields, date picker, time picker, and real-time conflict alert banner.
  - Refactor appointment status badges and table action buttons ("Check In", "Edit", "Cancel").
  - Standardize filter tabs and search bar.

- [x] **Task 5.4: Polish Consultation (SOAP) & Patient Chart Dialogs**
  - Files: `frontend/src/components/ConsultationDialog.svelte`, `frontend/src/components/PatientChartDialog.svelte`
  - Refactor SOAP inputs (Diagnosis, Symptoms, Notes, Rx, Advice) with clean form layouts and validation feedback.
  - Add collapsible past medical history accordion in consultation dialog.
  - Polish patient chart timeline with visit dates, attending doctor badges, and prescription notes.

---

## Phase 6: Quality Gates & Verification

- [x] **Task 6.1: Run Backend Quality Gates**
  - Run fast test suite: `uv run pytest backend/tests/ -v`.
  - Run strict type checking: `.venv/Scripts/python.exe -m basedpyright` (0 errors).
  - Run style checks: `uv run ruff check backend desktop package.py` and `uv run ruff format --check backend desktop package.py`.

- [x] **Task 6.2: Run Frontend Build & System Quality Gates**
  - Run Deno build: `cd frontend && deno task build && cd ..`.
  - Run zero em/en dash verification script across the entire repository.
  - Run standalone bundle verification: `.venv/Scripts/python.exe desktop/verify_bundle.py`.

---

## Phase 7: Single-Track Filter Tabs & Segmented Control Polish

- [x] **Task 7.1: Single-Track Filter Tabs in `AppointmentsWorkspace.svelte`**
  - File: `frontend/src/components/AppointmentsWorkspace.svelte`
  - Remove `flex-wrap` and `h-auto` from `Tabs.List` to eliminate stacked two-row wrapping.
  - Implement single horizontal segmented track with `flex flex-nowrap items-center h-9 p-0.5 rounded-lg border bg-muted/60 text-muted-foreground w-auto overflow-x-auto no-scrollbar gap-0.5`.
  - Remove rigid min-width styles (`min-w-[110px]`, `min-w-[95px]`) on `Tabs.Trigger` elements.
  - Apply proportional padding (`px-2.5 sm:px-3 text-xs font-medium whitespace-nowrap shrink-0`) and clean count badges (`<span class="ml-1 text-[11px] tabular-nums opacity-75 font-normal">({count})</span>`).

- [x] **Task 7.2: Responsive Toolbar & Action Row Geometry**
  - File: `frontend/src/components/AppointmentsWorkspace.svelte`
  - Refactor the filter tab and search toolbar container to maintain clean horizontal spacing without clipping search inputs or pagination controls.
  - Ensure zero horizontal or vertical page scrolling occurs on smaller window viewports.

---

## Phase 8: Unified Contextual Settings Architecture & Shell Consolidation

- [x] **Task 8.1: Consolidate Shell Settings Buttons in `App.svelte`**
  - File: `frontend/src/App.svelte`
  - Remove redundant Settings gear button from the sidebar top brand header. Keep brand header clean and focused.
  - Transform sidebar bottom user card into an interactive account trigger that opens the Settings dialog with the "Staff Profile" tab preselected.
  - Update top-right header controls:
    - When logged in: Display a single unified Settings button (`variant="outline" size="sm"`).
    - When logged out: Display an accessible System Settings button (`variant="ghost" size="icon"`, title="System & Demo Settings") alongside the primary "Sign In" button.

- [x] **Task 8.2: Contextual Accessibility & Logged-Out Adaptation in `SettingsDialog.svelte`**
  - File: `frontend/src/components/SettingsDialog.svelte`
  - Support `initialTab?: "profile" | "system"` prop to allow callers (like user footer vs. top-bar system icon) to open directly to the appropriate view.
  - When user is logged out (`currentUser === null`):
    - Hide the "Staff Profile" tab and automatically default to "System & Demo Mode".
    - Adapt modal header title to "System Settings" and description to "Runtime configuration and database status".
    - Hide the "Log Out Staff Session" destructive button from footer.
    - Show "Guest / Not Signed In" badge and provide a "Sign In" action button in the footer.
  - When user is logged in (`currentUser !== null`):
    - Show both "Staff Profile" and "System & Demo Mode" tabs.
    - Display user role badge and active session credentials.
    - Provide "Log Out Staff Session" button in dialog footer.

- [x] **Task 8.3: Sidebar Bottom State Adaptation for Logged-Out State**
  - File: `frontend/src/App.svelte`
  - When logged out, render a clean guest card in the sidebar footer with a "Sign In" button and database connection indicator, ensuring consistent visual geometry in both authenticated and unauthenticated states.

---

## Phase 9: Desktop Application Startup & Runtime Acceleration

- [x] **Task 9.1: Persistent WebView2 Storage & Asset Caching**
  - File: `desktop/launcher.py`
  - Pass `private_mode=False` and `storage_path=str(APP_DIR / "webview_cache")` to `webview.start()`.
  - Enable persistent caching of parsed JavaScript bundles, CSS stylesheets, and V8 bytecode across desktop app launches to reduce warm startup by ~1.0s.

- [x] **Task 9.2: Micro-Polling Server Readiness Probe**
  - File: `desktop/launcher.py`
  - Optimize `wait_for_server()`: reduce retry interval from 100ms to 10ms micro-polling and eliminate the post-success 50ms artificial sleep.
  - Shave 100-150ms of dead latency during desktop boot.

- [x] **Task 9.3: Streamline Desktop Middleware Stack**
  - File: `backend/config/settings.py`
  - Remove redundant `CsrfViewMiddleware` from `MIDDLEWARE` for the desktop token-authenticated loopback environment, eliminating first-request CSRF overhead and 403 rejections.

---

## Phase 10: Authoritative 6-Gate Verification & Desktop Packaging

- [ ] **Task 10.1: Full Repository Quality Gates**
  - Execute backend pytest suite: `uv run pytest backend/tests/ -v` (100% pass rate).
  - Execute strict type checking: `.venv/Scripts/python.exe -m basedpyright` (0 errors).
  - Execute style checks: `uv run ruff check` and `uv run ruff format --check`.
  - Execute frontend build: `cd frontend && deno task build && cd ..`.
  - Execute zero em/en dash verification script across repository.
  - Execute standalone bundle verification: `.venv/Scripts/python.exe desktop/verify_bundle.py`.

- [ ] **Task 10.2: Clean Standalone Desktop Packaging**
  - Run packaging script: `python package.py --clean`.
  - Verify generated `dist/HospitalSystem.exe` launches instantly, respects persistent cache, displays single-track filter tabs, and provides unified contextual settings.

---

## Phase 11: Experimental Pre-Release Packaging & GitHub Release (`v0.0.2-rc`)

- [x] **Task 11.1: Enhance Release Workflow for Pre-Releases**
  - File: `.github/workflows/release.yml`
  - In `pre-flight-check`, detect pre-release tags containing `-` (e.g. `v0.0.2-rc`) and output `is_prerelease=true` and `make_latest=false`.
  - In `publish-release`, conditionally set `prerelease` and `make_latest` flags based on pre-flight detection so experimental releases never overwrite the `latest` production release (`v0.0.1`).
  - Format with `deno fmt .github/workflows/` and verify zero em/en dashes.

- [ ] **Task 11.2: Tag and Trigger Experimental Pre-Release**
  - Tag verified commit on `experimental` branch as `v0.0.2-rc`.
  - Push tag to origin: `git push origin v0.0.2-rc` (or trigger workflow dispatch on `experimental`).

- [ ] **Task 11.3: Inspect and Verify GitHub Pre-Release**
  - Run `gh pr checks` / `gh run list --workflow=release.yml` to track build completion.
  - Verify attached Windows and macOS binaries and SHA-256 integrity checksums under the `v0.0.2-rc` pre-release tag.
