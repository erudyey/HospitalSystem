"""Automated end-to-end verification of standalone HospitalSystem.exe bundle."""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXE_PATH = REPO_ROOT / "dist" / "HospitalSystem.exe"
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
APP_DIR = Path(LOCAL_APPDATA) / "HospitalSystem"
STATE_FILE = APP_DIR / "app_state.json"
LOG_FILE = APP_DIR / "launcher.log"
DB_FILE = APP_DIR / "clinic.sqlite3"


def log(msg: str) -> None:
    print(f"[VERIFY] {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def main() -> None:
    if not EXE_PATH.exists():
        fail(f"Executable not found at {EXE_PATH}. Run 'python package.py' first.")

    log(f"Found standalone binary: {EXE_PATH} ({EXE_PATH.stat().st_size / (1024 * 1024):.1f} MB)")

    # Record log file offset for clean test isolation
    initial_log_offset = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

    # Phase 1: Test internal bootstrapping and migrations via --verify
    log("Testing internal bootstrapping via '--verify' flag...")
    res = subprocess.run([str(EXE_PATH), "--verify"], capture_output=True, text=True, timeout=20)
    if res.returncode != 0:
        fail(
            f"'--verify' exited with non-zero code {res.returncode}. Output:\n{res.stdout}\n{res.stderr}"
        )
    log("Internal bootstrapping and migrations completed cleanly (exit code 0).")

    # Phase 2: Start background process and test live loopback endpoints
    log("Launching executable in background mode...")
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    proc = subprocess.Popen([str(EXE_PATH)])

    try:
        # Wait for state file to be written
        deadline = time.time() + 10.0
        port = None
        token = None
        while time.time() < deadline:
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    port = data.get("port")
                    token = data.get("token")
                    if port and token:
                        break
                except Exception:
                    pass
            time.sleep(0.2)

        if not port or not token:
            fail("Timed out waiting for state file to be written by launcher.")

        log(f"Discovered active server at 127.0.0.1:{port} (PID: {proc.pid})")

        # Check 1: Health endpoint
        health_url = f"http://127.0.0.1:{port}/api/health/"
        with urllib.request.urlopen(health_url, timeout=3.0) as resp:
            if resp.status != 200:
                fail(f"Health endpoint returned status {resp.status}")
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("status") != "ok":
                fail(f"Health check status unexpected: {body}")
        log("Health check returned 200 OK.")

        # Check 2: SPA root HTML and injected token
        root_url = f"http://127.0.0.1:{port}/"
        req = urllib.request.Request(root_url)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status != 200:
                fail(f"Root HTML returned status {resp.status}")
            html = resp.read().decode("utf-8")
            if token not in html:
                fail("Session token was not injected into HTML head.")
        log("Root HTML returned 200 OK with synchronously injected session token.")

        # Check 3: Authenticated API endpoint (/api/patients/)
        api_url = f"http://127.0.0.1:{port}/api/patients/"
        api_req = urllib.request.Request(api_url, headers={"X-Session-Token": str(token)})
        with urllib.request.urlopen(api_req, timeout=3.0) as resp:
            if resp.status != 200:
                fail(f"API patients endpoint returned status {resp.status}")
            patients = json.loads(resp.read().decode("utf-8"))
            if not isinstance(patients, list):
                fail("API patients response was not a list.")
        log(f"Authenticated API returned 200 OK ({len(patients)} records).")

        # Check 4: SQLite Database creation
        if not DB_FILE.exists():
            fail(f"Database file was not created at {DB_FILE}")
        log(f"Verified SQLite database exists at {DB_FILE} ({DB_FILE.stat().st_size} bytes).")

        # Check 5: Diagnostic log inspection (isolated to current test run)
        if not LOG_FILE.exists():
            fail(f"Log file was not created at {LOG_FILE}")
        with LOG_FILE.open("r", encoding="utf-8") as f:
            f.seek(initial_log_offset)
            current_log_content = f.read()
        if "ERROR" in current_log_content:
            fail(f"Errors detected during test run in {LOG_FILE}:\n{current_log_content}")
        log("Verified launcher.log contains zero ERROR entries during verification run.")

    finally:
        log("Terminating background test process...")
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        log("Process terminated cleanly.")

    print("\n" + "=" * 60)
    print("ALL STANDALONE BUNDLE VERIFICATION CHECKS PASSED!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
