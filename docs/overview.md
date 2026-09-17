# Hospital Management System: Project overview

The Hospital Management System is a local-first Windows desktop application for clinic receptionists and front-desk staff. It manages patient registration and appointment scheduling without requiring internet access, external database servers, or cloud dependencies.

---

## 1. System background and evolution

### Original coursework implementation
The original coursework application was built with Python and Tkinter, storing data in a single local SQLite file (`clinic.db`). While functionally complete, Tkinter's native widgets made modern layout control, clean input validation, and keyboard-friendly responsive tables difficult to maintain.

### Modern desktop architecture
To keep the application completely offline while offering a modern, accessible interface, the project was restructured:
- **Desktop window**: Uses `pywebview` running on the Windows Microsoft Edge WebView2 runtime.
- **Embedded loopback server**: Runs Waitress WSGI on a private local port (`127.0.0.1`).
- **Backend services**: Built with Django, using pure Python business services, atomic database transactions, and SQLite in Write-Ahead Logging (WAL) mode.
- **Frontend workspaces**: Built with Svelte 5, TypeScript, `shadcn-svelte`, and Tailwind CSS, using a warm clinical palette and locally bundled Inter typography on a 16px base.
- **Tooling**: Built and bundled using Deno 2 for frontend compilation and uv for Python dependency management.

---

## 2. Core features

1. **Patient records and registration**:
   - Register patients with their name, contact detail, and age.
   - Numerical IDs are generated automatically, keeping records distinct even when patients share identical names.
   - Search records by name substring or exact numeric ID.

2. **Appointment booking and status tracking**:
   - Book appointments for any registered patient with doctor name and ISO date (`YYYY-MM-DD`).
   - View appointments filtered by patient.
   - Update appointment status through its workflow: Scheduled to Completed or Cancelled.

3. **Offline reliability and security**:
   - Strict loopback binding to `127.0.0.1` so Windows Defender Firewall never prompts for network access.
   - Random 256-bit session token generated on launch and verified on every API request.
   - Non-destructive migration tool (`backend.clinic.importer`) that can import existing legacy `clinic.db` records into the modernized schema.
   - Automatic database storage in `%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3`.

---

## 3. Repository layout

```text
HospitalSystem/
├── docs/                     # Architecture, API specifications, and workflow guides
├── desktop/                  # Desktop window launcher (pywebview, Waitress, Win32 mutex)
├── backend/                  # Django project, clinic application, services, and tests
│   ├── config/               # Settings, URLs, WSGI, and WhiteNoise static hosting
│   ├── clinic/               # Domain models, services, JSON views, legacy importer
│   └── tests/                # Automated pytest suite
├── frontend/                 # Svelte 5 SPA built with Deno 2 and shadcn-svelte
│   ├── src/                  # Workspaces, UI components, API client, design tokens
│   ├── deno.json             # Deno tasks and compiler options
│   └── tsconfig.json         # TypeScript configuration for editor LSP
├── run.ps1                   # Developer task runner script
├── package.py                # Standalone Windows executable builder (PyInstaller)
├── desktop.spec              # PyInstaller bundle specification
├── pyproject.toml            # Ruff linter, formatter, and pytest configuration
└── pyrightconfig.json        # basedpyright strict type configuration
```
