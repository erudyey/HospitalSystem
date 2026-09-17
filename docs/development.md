# Developer guide and local workflow

This guide covers setting up your local environment, running development servers, executing automated tests, and packaging the standalone Windows executable.

---

## 1. Prerequisites

Before starting, install the following tools:
- **Windows 10 or 11 (64-bit)** with Microsoft Edge WebView2 runtime (pre-installed on modern Windows).
- **Python 3.12+** with `uv` for package management.
- **Deno 2+** (`scoop install deno`) for Svelte compilation and frontend tooling.

---

## 2. Quick setup

From the repository root, run the setup task in PowerShell:

```powershell
# Creates .venv, installs Python dependencies, and installs frontend packages
.\run.ps1 setup
```

Alternatively, set up the layers manually:

```powershell
# 1. Python virtual environment
uv venv .venv
uv pip install --python .venv\Scripts\python.exe django waitress pywebview whitenoise pytest pytest-django ruff django-stubs pyinstaller basedpyright

# 2. Frontend dependencies
cd frontend
deno install
cd ..
```

---

## 3. Developer task runner (`run.ps1`)

The PowerShell script `run.ps1` standardizes everyday development workflows:

| Command | Action |
|---|---|
| `.\run.ps1 dev` | Starts Vite HMR on port 5173 and Django development server on port 8000 concurrently. |
| `.\run.ps1 desktop` | Builds production frontend assets and launches the live `pywebview` desktop window. |
| `.\run.ps1 test` | Runs the basedpyright strict type checker and the pytest backend test suite. |
| `.\run.ps1 format` | Formats and lints Python code (Ruff) and frontend code (Deno fmt). |
| `.\run.ps1 package` | Compiles frontend, packages dependencies, and creates `dist/HospitalSystem.exe` via PyInstaller. |

---

## 4. Testing and quality checks

### Automated tests
Run the complete automated test suite:
```powershell
.\run.ps1 test
```

Or run pytest directly:
```powershell
.venv\Scripts\pytest.exe backend/tests/ -v
```

### Type checking
Run basedpyright across all Python files:
```powershell
.venv\Scripts\python.exe -m basedpyright
```

Check frontend TypeScript files:
```powershell
cd frontend
deno check src/main.ts
cd ..
```

### Formatting and linting
Check Python formatting and linting:
```powershell
.venv\Scripts\ruff.exe check
.venv\Scripts\ruff.exe format --check
```

---

## 5. Standalone desktop packaging

To create a self-contained Windows executable:
```powershell
.\run.ps1 package
```

This generates `dist/HospitalSystem.exe`. The executable runs completely offline and writes its SQLite database to `%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3`. It does not require Python, Deno, or external development tools to be installed on target machines.
