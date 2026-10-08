"""Automated end-to-end verification of standalone HospitalSystem.exe bundle."""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_executable_path() -> Path:
    if sys.platform == "win32":
        return REPO_ROOT / "dist" / "HospitalSystem.exe"
    if sys.platform == "darwin":
        app_bin = (
            REPO_ROOT / "dist" / "HospitalSystem.app" / "Contents" / "MacOS" / "HospitalSystem"
        )
        if app_bin.exists():
            return app_bin
    return REPO_ROOT / "dist" / "HospitalSystem"


EXE_PATH = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else get_executable_path()


def log(msg: str) -> None:
    print(f"[VERIFY] {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def main() -> None:
    if not EXE_PATH.exists():
        fail(f"Executable not found at {EXE_PATH}. Run 'python package.py' first.")

    log(f"Found standalone binary: {EXE_PATH} ({EXE_PATH.stat().st_size / (1024 * 1024):.1f} MB)")

    temp_root = REPO_ROOT / "build"
    temp_root.mkdir(exist_ok=True)
    if not temp_root.resolve().is_relative_to(REPO_ROOT.resolve()):
        fail("Verification data must remain inside this checkout.")
    temporary = tempfile.TemporaryDirectory(prefix="bundle-verify-", dir=temp_root)
    temp_dir = temporary.name
    try:
        for mode in ("clinic", "demo"):
            run_verification(Path(temp_dir) / mode, mode)

    finally:
        # Allow Windows a brief interval to release antivirus and SQLite file handles.
        for attempt in range(20):
            try:
                temporary.cleanup()
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.25)


def run_verification(app_dir: Path, mode: str) -> None:
    """Verify a bundle using an isolated app-data directory."""
    app_dir.mkdir(parents=True, exist_ok=True)
    log(f"Verifying isolated {mode} mode...")
    state_file = app_dir / "app_state.json"
    log_file = app_dir / "launcher.log"
    db_file = app_dir / ("clinic_demo.sqlite3" if mode == "demo" else "clinic.sqlite3")
    env = os.environ.copy()
    env.pop("TESTING", None)
    env.pop("DEBUG", None)
    env["HOSPITAL_DATA_DIR"] = str(app_dir)
    env["HOSPITAL_MODE"] = mode

    # Record log file offset for clean test isolation
    initial_log_offset = log_file.stat().st_size if log_file.exists() else 0

    # Phase 1: Test internal bootstrapping and migrations via --verify
    log("Testing internal bootstrapping via '--verify' flag...")
    res = subprocess.run(
        [str(EXE_PATH), "--verify"], capture_output=True, text=True, timeout=45, env=env
    )
    if res.returncode != 0:
        fail(
            f"'--verify' exited with non-zero code {res.returncode}. Output:\n{res.stdout}\n{res.stderr}"
        )
    log("Internal bootstrapping and migrations completed cleanly (exit code 0).")

    # Phase 2: Start background process and test live loopback endpoints
    log("Launching executable in background mode...")
    if state_file.exists():
        state_file.unlink()

    proc = subprocess.Popen([str(EXE_PATH), "--verify-server"], env=env)
    launcher_pid = proc.pid

    try:
        # Wait for state file to be written
        deadline = time.monotonic() + 45.0
        port = None
        token = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                details = (
                    log_file.read_text(encoding="utf-8")
                    if log_file.exists()
                    else "No launcher log."
                )
                fail(
                    f"The launcher exited before becoming ready (code {proc.returncode}).\n{details}"
                )
            if state_file.exists():
                try:
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    port = data.get("port")
                    token = data.get("token")
                    candidate_pid = data.get("pid")
                    if type(candidate_pid) is int and candidate_pid > 0:
                        launcher_pid = candidate_pid
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
            if body.get("mode") != mode:
                fail(f"Expected {mode} mode, got {body.get('mode')}")
        log("Health check returned 200 OK.")

        # Check 2: SPA root HTML and injected token
        root_url = f"http://127.0.0.1:{port}/?token={token}"
        req = urllib.request.Request(root_url)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status != 200:
                fail(f"Root HTML returned status {resp.status}")
            html = resp.read().decode("utf-8")
            if token not in html:
                fail("Session token was not injected into HTML head.")
        log("Root HTML returned 200 OK with synchronously injected session token.")

        # The root must not disclose launch credentials to another local origin.
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3.0)
        except urllib.error.HTTPError as exc:
            if exc.code != 403:
                fail(f"Untrusted root request returned {exc.code}")
        else:
            fail("Untrusted root request exposed launch credentials.")

        # Check 3: Clinic data requires a staff session after loopback authentication.
        api_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/patients/",
            headers={"X-Session-Token": str(token)},
        )
        try:
            urllib.request.urlopen(api_req, timeout=3.0)
        except urllib.error.HTTPError as exc:
            if exc.code != 401:
                fail(f"Unauthenticated staff request returned {exc.code}")
        else:
            fail("Clinic records were accessible without a staff session.")
        log("Clinic staff authentication verified.")

        if mode == "demo":
            accounts_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/demo/accounts/",
                headers={"X-Session-Token": str(token)},
            )
            with urllib.request.urlopen(accounts_req, timeout=3.0) as resp:
                accounts = json.loads(resp.read())
                if len(accounts) != 4:
                    fail("The fresh demo account chooser did not contain all four accounts.")
            if (app_dir / "clinic.sqlite3").exists():
                fail("Demo verification created a clinic database.")
            log("Demo account chooser and separate database verified.")

        # Check 4: SQLite Database creation
        if not db_file.exists():
            fail(f"Database file was not created at {db_file}")
        log(f"Verified SQLite database exists at {db_file} ({db_file.stat().st_size} bytes).")

        # Check 5: Diagnostic log inspection (isolated to current test run)
        if not log_file.exists():
            fail(f"Log file was not created at {log_file}")
        with log_file.open("r", encoding="utf-8") as f:
            f.seek(initial_log_offset)
            current_log_content = f.read()
        if "ERROR" in current_log_content:
            fail(f"Errors detected during test run in {log_file}:\n{current_log_content}")
        log("Verified launcher.log contains zero ERROR entries during verification run.")

    finally:
        log("Terminating background test process...")
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(launcher_pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
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
