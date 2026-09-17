# Hospital Management System: Project Overview

The **Hospital Management System** is a lightweight, local-first Windows desktop coursework application designed for front-desk clinic operations. It provides reliable patient record management and appointment tracking without requiring internet connectivity, external servers, or complicated database administration.

---

## 1. System Background & Evolution

### The Baseline
The legacy application was implemented as a Python script utilizing **Tkinter** for its graphical interface and a single SQLite file (`clinic.db`) for persistence. While functionally complete, Tkinter’s native widget limitations restrict modern accessibility, visual styling, responsive layouts, and scalable component separation.

### The Modernized Architecture
To retain full desktop offline autonomy while providing a modern user experience, the system was re-architected as a web-rendered desktop application:
- **Desktop Window**: Built with **`pywebview`**, utilizing the Windows Microsoft Edge WebView2 runtime.
- **Embedded Server**: Local Python loopback server running **Waitress** WSGI.
- **Backend**: **Django** with pure Python services, strict validation, and SQLite Write-Ahead Logging (WAL).
- **Frontend**: **Svelte** with TypeScript, **`shadcn-svelte`**, and **Tailwind CSS**, styled in a **Warm Clinical Palette** with locally-bundled **Inter** typography on a universal $16\text{px}$ base.
- **Runtime**: Built and bundled using **Deno 2** for frontend compilation and **uv** for Python virtual environments.

---

## 2. Core Capabilities

1. **Patient Directory & Registration**:
   - Register patients with their full name, contact information, and positive whole-number age.
   - Distinct auto-incrementing numerical IDs prevent collisions between patients sharing identical names.
   - Real-time search by substring matching across patient names and exact numerical ID lookup.

2. **Appointment Scheduling & Management**:
   - Book appointments for a selected patient with doctor assignment and ISO date (`YYYY-MM-DD`).
   - Filter appointment history per patient.
   - Update appointment status across the lifecycle: `Scheduled` $\rightarrow$ `Completed` or `Cancelled`.

3. **Data Safety & Single-User Desktop Integrity**:
   - Complete offline execution with loopback socket binding (`127.0.0.1`).
   - Zero external cloud services, authentication bloat, or remote APIs.
   - Automated legacy database import that non-destructively migrates historical `clinic.db` records to the new schema.
   - Persistent application storage in `%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3`.

---

## 3. Directory Layout

```text
HospitalSystem/
├── docs/                     # Technical documentation & architecture references
├── desktop/                  # Desktop window runner (pywebview + Waitress + Win32 hooks)
├── backend/                  # Django project, clinic application, services, and tests
│   ├── config/               # Django settings, URLs, WSGI configuration
│   ├── clinic/               # Models, business services, API views, legacy importer
│   └── tests/                # Unit and integration test suites
├── frontend/                 # Svelte SPA built with Deno 2 and shadcn-svelte
│   ├── src/                  # Workspaces, UI components, API client, design tokens
│   └── dist/                 # Compiled production assets served by WhiteNoise
├── run.ps1                   # Ergonomic developer task runner
├── package.py                # PyInstaller standalone executable builder
└── pyproject.toml            # Ruff linter, formatter, and pytest configuration
```
