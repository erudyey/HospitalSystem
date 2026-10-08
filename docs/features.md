# HospitalSystem -- Feature Overview

Role-based clinical desktop app. Single `.exe` / `.app`. No server install required.

---

## Roles

| Role | Access |
| :--- | :--- |
| **Receptionist** | Patient registry, appointment booking, check-in triage, conflict detection |
| **Doctor** | Waiting room queue, consultation dialog, SOAP notes, patient chart |

---

## Authentication

- Staff login with username + password (PBKDF2-hashed).
- "Keep me signed in" checkbox -- persists token in `localStorage`; unchecked uses `sessionStorage`.
- Default startup: logged out. No auto-login into demo account.
- Session validated on launch; expired/invalid tokens silently cleared.
- Staff register, update profile, change password, log out.

---

## Patient Registry

- Register patients: full name, contact, age.
- Search by name, ID, or phone number.
- Edit patient record.
- Delete patient -- blocked if completed appointments or medical records exist (audit trail protection).
- Active and total appointment counts displayed per patient row.

---

## Appointments

- Book appointment: patient, doctor (from staff list), date, time, reason for visit.
- **5-state lifecycle**: Scheduled -- Checked In -- In Consultation -- Completed -- Cancelled.
- Completed appointments are immutable -- cannot be edited, rescheduled, or deleted.
- **Schedule conflict detection**: doctor cannot have overlapping appointments within +/- 15 min window on same date. Real-time conflict warning banner in booking form.
- "Book & Check In" triage shortcut.
- Filter tabs: All / Waiting Room / Scheduled / Consulting / Completed / Cancelled -- full tab bar, no truncation.
- Pagination, search by patient name or ID, refresh.

---

## Doctor Workspace

- **Waiting Room queue**: patients checked in or in consultation.
- **Today's Schedule**: all appointments for current date.
- **My Patients**: roster of all patients ever seen by this doctor.
- Tabs with live counts. Scroll affordances on narrow viewports.
- Start / end consultation actions update appointment state.

---

## SOAP Consultation Notes (Medical Records)

- Create medical record per completed consultation.
- Fields: diagnosis, symptoms/subjective, clinical notes, prescription, follow-up date.
- Only authoring doctor can update own records.
- Patient chart shows full medical history ordered by date.
- Records protect patient from deletion.

---

## Settings

Unified contextual settings dialog:

- **When logged in**: Staff Profile tab (edit name, specialty, license, password) + System & Demo Mode tab + Log Out button.
- **When logged out**: System Settings only (demo mode toggle, database status) + Sign In CTA.
- Single settings entry point -- no duplicate gear icons.

---

## System & Demo Mode

- Demo mode populates seed patients and appointments for evaluation.
- Toggle persisted in `localStorage`.
- SQLite WAL status indicator shows database health.
- Demo toggle never bypasses explicit logout.

---

## Desktop Shell

- Single-window `pywebview` app (WebView2 on Windows, WebKit on macOS).
- Single-instance lock -- second launch shows dialog and exits cleanly.
- Loopback token auth -- all API calls require session token; no open ports.
- Persistent WebView2 cache -- warm boots ~1s faster.
- Auto-runs DB migrations on launch. No manual setup.
- Clean shutdown: server closed, state file removed, mutex/lock handle released.

---

## Persistence

- SQLite with WAL mode and foreign key enforcement.
- DB stored in OS app data directory (`%LOCALAPPDATA%\HospitalSystem\` on Windows, `~/Library/Application Support/HospitalSystem/` on macOS).
- Production DB never touched by tests.

---

## Packaging & Distribution

- Standalone single-file `.exe` (Windows) or `.app` (macOS) -- no Python or Node install needed.
- CI/CD via GitHub Actions: multi-platform builds, SHA-256 checksums, pre-release vs. release detection.
- Pre-releases tagged `vX.Y.Z-alpha.N`; production releases tagged `vX.Y.Z`.
