# Developer Guide & Local Workflow

This guide details environment setup, local development workflows, automated testing, and packaging procedures.

---

## 1. Prerequisites

1. **Python 3.12+** with `uv` installed.
2. **Deno 2+** (`scoop install deno`) for frontend compilation and task running.
3. **Microsoft Edge WebView2 Runtime** (pre-installed on Windows 10/11).

---

## 2. Quick Setup

Clone the repository and run the setup commands:

```powershell
# 1. Create project-local virtual environment and install dependencies
uv venv .venv
uv pip install -r requirements.txt   # or via .\run.ps1 setup

# 2. Install frontend dependencies with Deno
cd frontend
deno install
cd ..
```

---

## 3. Developer Task Runner (`run.ps1`)

The repository includes a PowerShell helper script (`run.ps1`) to standardize all common development tasks:

| Command | Description |
|---|---|
| `.\run.ps1 dev` | Starts concurrent Vite development server (port 5173) and Django API server (port 8000) with hot reloading. |
| `.\run.ps1 desktop` | Builds the frontend and starts the live `pywebview` native desktop shell. |
| `.\run.ps1 test` | Runs the pytest backend test suite and type-checking pass. |
| `.\run.ps1 format` | Runs Ruff (Python formatting/linting) and Deno fmt (frontend). |
| `.\run.ps1 package` | Compiles frontend, collects static assets, and builds `dist/HospitalSystem.exe` via PyInstaller. |

---

## 4. Testing

### Run Backend Tests
```powershell
.venv\Scripts\pytest.exe backend/tests/ -v
```

### Run Baseline Legacy Regression Tests
```powershell
python -m unittest discover -s tests -v
```

---

## 5. Type Checking & Zed IDE Integration

Zed IDE natively reads `.venv` and `pyrightconfig.json`:
- `django-stubs` provides full model attribute and query typing.
- Type annotations are enforced across `backend/clinic/services.py` and `backend/clinic/models.py`.
- Run manual type checks with:
  ```powershell
  .venv\Scripts\pyright.exe
  ```

---

## 6. Standalone Desktop Packaging

To create a self-contained Windows executable:
```powershell
.\run.ps1 package
```
This produces `dist/HospitalSystem.exe`. The output can be copied to any compatible Windows machine without requiring Python, Deno, or external runtimes installed.
