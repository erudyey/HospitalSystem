# Hospital Management System

> Modern, standalone, offline-first Windows desktop coursework application for registering patients and managing appointments: built with Svelte 5, `shadcn-svelte`, Tailwind CSS, Django, SQLite (WAL mode), Waitress, and `pywebview`.

[![CI Status](https://github.com/erudyey/HospitalSystem/actions/workflows/ci.yml/badge.svg)](https://github.com/erudyey/HospitalSystem/actions/workflows/ci.yml)
[![Type Checked with basedpyright](https://img.shields.io/badge/types-basedpyright-blue.svg)](https://github.com/DetachHead/basedpyright)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Highlights and Architecture

- **Desktop Shell (`desktop/`)**: Native Windows desktop window powered by Microsoft Edge WebView2 and `pywebview`. Pre-binds ephemeral loopback sockets, guarantees single-instance execution via Win32 named mutex (`CreateMutexW`), and manages server lifecycle cleanly with zero orphan processes.
- **Backend Service Layer (`backend/`)**: Django with pure Python services, atomic database transactions (`transaction.atomic()`), strict model validation (`full_clean()`), and loopback session token security (`hmac.compare_digest`).
- **Frontend Workspaces (`frontend/`)**: Modern Svelte 5 single-page application built on `shadcn-svelte` (`bits-ui`), styled with the Swiss Medical Red & Pure White / Zinc palette, left sidebar navigation, and progressive disclosure data tables.
- **Zero-Node Runtime**: Built and bundled using **Deno 2** for fast, zero-overhead frontend compilation without a Node.js installation.
- **Local Persistence**: Production database automatically maintained at `%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3` with SQLite Write-Ahead Logging (`WAL` mode).

---

## Quickstart

### Prerequisites

- **OS**: Windows 10 or 11 (64-bit) with Microsoft Edge WebView2 Runtime (pre-installed on modern Windows).
- **Python**: 3.12+ (managed via `uv` or system Python).
- **Deno**: 2.x (`scoop install deno`).

### Development and Automation (`run.ps1`)

A unified PowerShell task runner is provided in the repository root:

```powershell
# 1. First-time setup (virtualenv, python dependencies, and frontend packages)
.\run.ps1 setup

# 2. Launch concurrent Vite HMR and Django API development servers
.\run.ps1 dev

# 3. Launch live pywebview desktop application window
.\run.ps1 desktop

# 4. Run automated test suite (pytest + basedpyright)
.\run.ps1 test

# 5. Format and lint Python (Ruff) and frontend (Deno)
.\run.ps1 format

# 6. Package standalone Windows executable (dist/HospitalSystem.exe)
.\run.ps1 package
```

---

## Project Structure

```text
HospitalSystem/
├── backend/                  # Django backend core
│   ├── config/               # Settings, WSGI, URLs, WhiteNoise static serving
│   ├── clinic/               # Domain models, services, views, loopback middleware, importer
│   └── tests/                # Automated pytest suite (services, API, legacy importer)
├── desktop/                  # Desktop launcher & Windows runtime hardening
│   ├── launcher.py           # Single-instance mutex, ephemeral socket, Waitress thread
│   └── verify_bundle.py      # Automated bundle and runtime verification
├── frontend/                 # Svelte 5 SPA
│   ├── src/
│   │   ├── components/       # PatientsWorkspace & AppointmentsWorkspace
│   │   ├── lib/              # shadcn-svelte UI components, API client, utils
│   │   ├── app.css           # Inter 16px typography & Swiss Medical Red tokens
│   │   └── App.svelte        # Application shell & global error boundary
│   ├── deno.json             # Deno tasks & compiler options
│   ├── tsconfig.json         # TypeScript configuration for editor LSP
│   └── vite.config.ts        # Vite build configuration
├── docs/                     # Technical specifications & design records
│   ├── overview.md           # System overview & migration rationale
│   ├── system-architecture.md# Process lifecycle & security boundaries
│   ├── api-contracts.md      # REST endpoints & JSON error envelopes
│   └── development.md        # Contributor guide & packaging workflow
├── package.py                # Standalone PyInstaller freeze script
├── desktop.spec              # PyInstaller Windows desktop specification
├── pyproject.toml            # Ruff and pytest configuration
├── pyrightconfig.json        # basedpyright strict type configuration
└── run.ps1                   # Ergonomic task runner script
```

---

## Verification and Quality Gates

Run all automated checks from the project root:

```powershell
# Run backend test suite (15 tests) & basedpyright type checker
.\run.ps1 test

# Run Ruff linter and format verification
.venv\Scripts\ruff.exe check
.venv\Scripts\ruff.exe format --check

# Run basedpyright strict type checker directly
.venv\Scripts\python.exe -m basedpyright
```

---

## Legacy Data Migration

A dedicated migration service (`backend.clinic.importer`) is available to inspect and import legacy `clinic.db` SQLite records into the modernized database. It uses Python's atomic `sqlite3.Connection.backup()` API to take a read-only snapshot before validating row integrity, preserving patient IDs, duplicate-name records, and appointment relationships.
