# Developer Guide and Local Workflow Runbook

This runbook covers setting up your local Windows or macOS environment,
executing development servers, running quality checks, and packaging the
standalone desktop application.

---

## 1. Prerequisites and Toolchain

| Tool                        | Minimum Version                           | Installation / Management                           |
| :-------------------------- | :---------------------------------------- | :-------------------------------------------------- |
| **Windows OS**              | Windows 10 (1809+) or Windows 11 (64-bit) | Pre-installed                                       |
| **Microsoft Edge WebView2** | Evergreen Runtime                         | Included in Windows 10/11                           |
| **macOS**                   | macOS 13 or newer (Ventura, Sonoma, ...)  | Pre-installed with native Apple WebKit              |
| **Python**                  | 3.12 or newer                             | Managed via `uv` or system installer                |
| **uv**                      | 0.4 or newer                              | `scoop install uv` (Win) or `brew install uv` (Mac) |
| **Deno**                    | 2.0 or newer                              | `scoop install deno` (Win) or `brew install deno`   |

---

## 2. Automated Setup

On Windows (PowerShell):

```powershell
.\run.ps1 setup
```

On macOS / Linux (Terminal):

```bash
./run.sh setup
```

This task:

1. Creates a Python virtual environment at `.venv` using `uv`.
2. Installs required Python dependencies (`django`, `waitress`, `pywebview`,
   `whitenoise`, `pytest`, `pytest-django`, `ruff`, `pyinstaller`,
   `basedpyright`, and macOS `pyobjc` WebKit packages when on Darwin).
3. Installs frontend packages in `frontend/` using `deno install`.

### Manual Setup Alternative

If you prefer to configure each layer manually:

Create the Python virtual environment:

```bash
uv venv .venv
```

Install Python packages into `.venv` using the dev extras:

On Windows:

```powershell
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
```

On macOS / Linux:

```bash
uv pip install --python .venv/bin/python -e ".[dev]"
```

Install frontend packages:

```bash
cd frontend; deno install; cd ..
```

---

## 3. Development Execution Modes

### Concurrent Development (Vite HMR + Django API)

Starts Vite Hot Module Replacement on port 5173 and the Django API server on
port 8000 simultaneously:

On Windows:

```powershell
.\run.ps1 dev
```

On macOS / Linux:

```bash
./run.sh dev
```

### Live Desktop Shell

Compiles the frontend assets to `backend/config/static_dist/` and opens the
native `pywebview` window pointing to an embedded Waitress instance:

On Windows:

```powershell
.\run.ps1 desktop
```

On macOS / Linux:

```bash
./run.sh desktop
```

---

## 4. Testing and Quality Verification

### Run Complete Test Suite and Strict Type Checker

Executes both `pytest` and `basedpyright`:

On Windows:

```powershell
.\run.ps1 test
```

On macOS / Linux:

```bash
./run.sh test
```

### Rapid Iterative Testing (Quick TDD Loop)

Runs the backend `pytest` suite in sub-second time (~0.8s), bypassing the 5-second `basedpyright` check during active TDD iteration:

On Windows:

```powershell
.\run.ps1 test -Quick
```

On macOS / Linux:

```bash
./run.sh test --quick
```

> **Note on Test Performance**: Automated tests execute against in-memory SQLite (`TESTING=True`) with 1-round PBKDF2 password hashing in test settings, running all 76 unit and integration tests in ~0.8 seconds without touching user data directories.

### Run Python Unit Tests Only

Run pytest directly against the backend test suite:

On Windows:

```powershell
.venv\Scripts\pytest.exe backend/tests/ -v
```

On macOS / Linux:

```bash
.venv/bin/pytest backend/tests/ -v
```

### Run Strict Python Type Checking

Execute basedpyright across all backend and desktop Python modules:

On Windows:

```powershell
.venv\Scripts\python.exe -m basedpyright
```

On macOS / Linux:

```bash
.venv/bin/python -m basedpyright
```

### Check Frontend TypeScript Types

Type-check Svelte and TypeScript files with Deno:

```bash
cd frontend; deno check src/main.ts; cd ..
```

### Code Formatting and Linting

Format Python files with Ruff and frontend files with Deno:

On Windows:

```powershell
.\run.ps1 format
```

On macOS / Linux:

```bash
./run.sh format
```

Verify Python formatting without modifying files:

On Windows:

```powershell
.venv\Scripts\ruff.exe format --check
```

On macOS / Linux:

```bash
.venv/bin/ruff format --check
```

Verify Python lint rules without modifying files:

On Windows:

```powershell
.venv\Scripts\ruff.exe check
```

On macOS / Linux:

```bash
.venv/bin/ruff check
```

---

## 5. Standalone Executable Packaging

To compile frontend assets and generate the standalone desktop distribution:

On Windows (generates `dist/HospitalSystem.exe`):

```powershell
.\run.ps1 package
```

On macOS (generates `dist/HospitalSystem.app` and `dist/HospitalSystem`):

```bash
./run.sh package
```

### Rapid Iterative Packaging (Quick Mode)

During local testing of desktop changes, you can bypass the clean rebuild and reuse PyInstaller's module graph cache to package in ~10-15 seconds (skipping frontend compilation if `frontend/dist/` already exists):

On Windows:

```powershell
.\run.ps1 package -Quick
```

On macOS:

```bash
./run.sh package --quick
```

Or directly via `package.py`:

```bash
.venv\Scripts\python.exe package.py --quick      # Windows
.venv/bin/python package.py --quick             # macOS
```

### Build Pipeline Stages

1. **Frontend Compilation**: Deno executes `deno task build` in `frontend/`,
   writing production HTML, CSS, and JS bundles to
   `backend/config/static_dist/`.
2. **Collect Static**: Django gathers static files into the configured
   distribution path.
3. **PyInstaller Freeze**: PyInstaller processes `desktop.spec`, bundling the
   Python interpreter, Django framework, Waitress server, WhiteNoise middleware,
   and frontend assets into an executable or macOS `.app` bundle.

### Automated Bundle Verification

Verify the compiled bundle by running the automated runtime check suite:

On Windows:

```powershell
.venv\Scripts\python.exe desktop/verify_bundle.py
```

On macOS / Linux:

```bash
.venv/bin/python desktop/verify_bundle.py
```

This verification script tests:

1. Executable or application bundle presence in `dist/`.
2. Executable architecture and format integrity.
3. Digital bundle integrity and internal manifest.
4. Clean launch and loopback socket binding on `127.0.0.1`.
5. Health endpoint response (`/api/health/`).
6. Session token rejection (`403 Forbidden` on invalid tokens).
7. Clean shutdown and zero process leakage.

---

## 6. Continuous Integration & Release Automation

The repository utilizes GitHub Actions to enforce quality gates and automate
cross-platform desktop releases:

### Continuous Integration (`.github/workflows/ci.yml`)

- **Trigger Scope**: Executes automatically on pushes to `master`, `experimental`,
  and `feature/**` branches, and on pull requests targeting `master` or
  `experimental`.
- **Multi-OS Quality Matrix**: Runs across both `windows-latest` and `macos-latest`
  to ensure cross-platform compatibility.
- **Concurrency Control**: Automatically cancels outdated in-progress runs when
  new commits are pushed (`cancel-in-progress: true`).
- **Pipeline Stages**:
  1. Sets up `uv` package manager with persistent dependency caching.
  2. Verifies zero em/en dash policy across code and documentation.
  3. Verifies Ruff code formatting and linting rules.
  4. Runs strict Python static type checking with `basedpyright`.
  5. Validates GitHub workflow formatting with Deno (`deno fmt`).
  6. Compiles Svelte 5 frontend with Deno 2.
  7. Executes the full 76-test unit and integration test suite with `pytest`.

### Release Workflow (`.github/workflows/release.yml`)

- **Trigger Scope**: Executes on version tag pushes (`v*`) or manual execution via
  `workflow_dispatch`.
- **Naming Standard**: All releases are published with the title `Release vX.Y.Z`
  (e.g. `Release v0.0.1`).
- **Pre-Flight Quality Gate**: Before allocating build machines, the workflow runs
  all 6 quality gates and validates SemVer tag compliance. If any check fails, the
  release aborts immediately.
- **Cross-Platform Bundling & Verification**:
  - Windows: Freezes `dist/HospitalSystem-Windows-x64.exe` and verifies via
    `desktop/verify_bundle.py`.
  - macOS: Freezes `dist/HospitalSystem.app`, verifies bootstrapping via
    `dist/HospitalSystem.app/Contents/MacOS/HospitalSystem --verify`, and zips to
    `HospitalSystem-macOS.zip`.
- **Integrity Checksums**: Computes SHA-256 hashes for all binaries, creates an
  attached `SHA256SUMS.txt`, and embeds a markdown verification table directly in
  the release notes.

---

## 7. Database Seeding

The `seed` management command populates your local database with realistic
sample patients and appointments so the application looks and behaves like a
live clinic without manual data entry.

> **Note:** The command writes to your real AppData database
> (`%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3` on Windows,
> `~/Library/Application Support/HospitalSystem/clinic.sqlite3` on macOS).
> Use `--clear` only when a fresh dataset is acceptable.

### Add sample data (skips if records already exist)

```powershell
uv run python backend/manage.py seed
```

### Wipe all data and re-seed from scratch

```powershell
uv run python backend/manage.py seed --clear
```

### Control the number of patients (default is 15)

```powershell
uv run python backend/manage.py seed --clear --count 30
```

### What gets created

| Detail              | Value                                              |
| :------------------ | :------------------------------------------------- |
| Patients            | 15 (default) with names, ages, and optional contacts |
| Appointments        | 1 to 4 per patient, spread over -180 to +60 days  |
| Past appointments   | Mostly `Completed`, occasionally `Cancelled`       |
| Future appointments | Mostly `Scheduled`, occasionally `Cancelled`       |
| Doctors             | 6 rotating sample doctors                          |
| Reproducibility     | Fixed random seed -- same names every run          |
