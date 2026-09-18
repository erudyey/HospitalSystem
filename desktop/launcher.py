"""Desktop application launcher for HospitalSystem.

Manages process lifecycle, ephemeral socket pre-binding, Waitress daemon thread,
in-memory session token injection, WebView2 runtime detection, diagnostic logging,
and clean shutdown.
"""

import atexit
import contextlib
import ctypes
import json
import logging
import os
import secrets
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.request import urlopen


class _NullWriter:
    """Safe fallback for sys.stdout/stderr in PyInstaller --noconsole mode."""

    def write(self, _s: str) -> int:
        return 0

    def flush(self) -> None:
        pass


# Fix for PyInstaller --noconsole mode where sys.stdout/stderr are None
if sys.stdout is None:
    sys.stdout = _NullWriter()  # type: ignore[assignment]
if sys.stderr is None:
    sys.stderr = _NullWriter()  # type: ignore[assignment]

# Ensure bundle / repository root is on sys.path
meipass = getattr(sys, "_MEIPASS", None)
if getattr(sys, "frozen", False) and meipass:
    BUNDLE_ROOT = Path(str(meipass))
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent.parent

if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))

# Diagnostic File Logger in OS-specific app directory
def get_app_dir() -> Path:
    """Resolve application data directory based on operating system."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        base = Path(local_appdata) if local_appdata else (Path.home() / "AppData" / "Local")
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg_data) if xdg_data else (Path.home() / ".local" / "share")
    app_dir = base / "HospitalSystem"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APP_DIR = get_app_dir()
LOG_FILE = APP_DIR / "launcher.log"
STATE_FILE = APP_DIR / "app_state.json"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("HospitalLauncher")
logger.info("Initializing HospitalSystem launcher (PID: %d)...", os.getpid())

# Single Instance Check (bypassed if running verification mode)
IS_VERIFY_MODE = "--verify" in sys.argv
_INSTANCE_LOCK_HANDLE = None


def show_error_dialog(title: str, message: str) -> None:
    """Display a native platform error dialog."""
    logger.error("Error dialog presented [%s]: %s", title, message)
    if IS_VERIFY_MODE:
        sys.stderr.write(f"[{title}] {message}\n")
        return

    if sys.platform == "win32" and hasattr(ctypes, "windll"):
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10 | 0x0)  # MB_ICONERROR | MB_OK
    elif sys.platform == "darwin":
        try:
            clean_title = title.replace('"', '\\"')
            clean_msg = message.replace('"', '\\"')
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display alert "{clean_title}" message "{clean_msg}" as critical',
                ],
                check=False,
                timeout=5,
            )
        except Exception:
            sys.stderr.write(f"[{title}] {message}\n")
    else:
        sys.stderr.write(f"[{title}] {message}\n")


if not IS_VERIFY_MODE:
    if sys.platform == "win32" and hasattr(ctypes, "windll"):
        MUTEX_NAME = "Local\\HospitalSystem_AppMutex"
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            logger.warning("Application already running; secondary instance exited.")
            ctypes.windll.user32.MessageBoxW(
                0,
                "Hospital Management System is already running.\n\nPlease check your taskbar.",
                "HospitalSystem - Already Running",
                0x40 | 0x1,  # MB_ICONINFORMATION | MB_OK
            )
            sys.exit(0)
    else:
        # POSIX file locking via fcntl for macOS and Linux
        try:
            import fcntl

            lock_file_path = APP_DIR / "app.lock"
            _INSTANCE_LOCK_HANDLE = open(lock_file_path, "w")  # noqa: SIM115
            try:
                fcntl.flock(_INSTANCE_LOCK_HANDLE.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError):
                logger.warning("Application already running on POSIX/macOS; secondary instance exited.")
                if sys.platform == "darwin":
                    with contextlib.suppress(Exception):
                        import subprocess

                        subprocess.run(
                            [
                                "osascript",
                                "-e",
                                'display alert "Hospital Management System" message "The application is already running." as informational',
                            ],
                            check=False,
                            timeout=5,
                        )
                sys.exit(0)
        except Exception as exc:
            logger.warning("Could not acquire POSIX instance lock: %s", exc)


def find_available_port() -> int:
    """Pre-bind an ephemeral socket to find and reserve an unused local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout_sec: float = 10.0) -> bool:
    """Poll readiness endpoint until the local server confirms 200 OK."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=0.5) as resp:
                resp.read()
                if resp.status == 200:
                    time.sleep(0.05)
                    return True
        except Exception:
            time.sleep(0.1)
    return False


def main() -> None:
    # 1. Generate 256-bit cryptographically secure session token
    session_token = secrets.token_urlsafe(32)
    os.environ["HOSPITAL_SESSION_TOKEN"] = session_token
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")

    # 2. Allocate loopback port
    port = find_available_port()
    logger.info("Allocated ephemeral loopback port: %d", port)

    # 3. Initialize Django and Waitress WSGI server
    try:
        import django

        django.setup()
        from django.core.management import call_command

        logger.info("Executing database migrations...")
        call_command("migrate", interactive=False)

        from waitress.server import create_server

        from backend.config.wsgi import application
    except Exception as exc:
        logger.exception("Failed to initialize server components: %s", exc)
        show_error_dialog("Startup Error", f"Failed to initialize server components:\n\n{exc}")
        sys.exit(1)

    try:
        server = create_server(application, host="127.0.0.1", port=port, threads=4)
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()
        logger.info("Waitress WSGI server started on 127.0.0.1:%d", port)
    except Exception as exc:
        logger.exception("Failed to start Waitress server: %s", exc)
        show_error_dialog(
            "Server Socket Error", f"Could not bind server to 127.0.0.1:{port}:\n\n{exc}"
        )
        sys.exit(1)

    # Write state file for verification discovery
    state_data = {
        "port": port,
        "pid": os.getpid(),
        "started_at": time.time(),
        "token": session_token,
    }
    with contextlib.suppress(Exception):
        STATE_FILE.write_text(json.dumps(state_data), encoding="utf-8")

    # Clean shutdown hook
    def cleanup_server():
        logger.info("Executing server cleanup...")
        with contextlib.suppress(Exception):
            server.close()
        with contextlib.suppress(Exception):
            if STATE_FILE.exists():
                STATE_FILE.unlink()

    atexit.register(cleanup_server)

    # 4. Wait for readiness probe
    health_url = f"http://127.0.0.1:{port}/api/health/"
    if not wait_for_server(health_url, timeout_sec=8.0):
        logger.error("Readiness probe timed out at %s", health_url)
        show_error_dialog(
            "Connection Timeout",
            f"The local backend server failed to respond within 8 seconds at {health_url}.\nShutting down.",
        )
        sys.exit(1)

    logger.info("Backend readiness verified successfully.")

    # Headless verification mode exits cleanly here without opening GUI
    if IS_VERIFY_MODE:
        logger.info("Verification check completed successfully. Exiting cleanly.")
        time.sleep(0.05)
        sys.exit(0)

    # 5. Import and verify pywebview / WebView2
    try:
        import webview
    except ImportError as exc:
        logger.exception("Could not import pywebview: %s", exc)
        show_error_dialog(
            "Missing Dependencies",
            f"Could not load desktop webview module:\n\n{exc}\n\nPlease install pywebview.",
        )
        sys.exit(1)

    class DesktopHostApi:
        """Expose safe, minimal JS bridge."""

        def get_session_token(self) -> str:
            return session_token

    api = DesktopHostApi()

    try:
        window = webview.create_window(
            title="Hospital Management System",
            url=f"http://127.0.0.1:{port}/?token={session_token}",
            width=1320,
            height=840,
            min_size=(1024, 700),
            js_api=api,
        )
        assert window is not None

        def on_window_loaded():
            """Inject session token into window memory after load."""
            with contextlib.suppress(Exception):
                window.evaluate_js(f"window.__SESSION_TOKEN__ = '{session_token}';")

        def on_window_closing():
            """Cleanly close server socket when the user closes the window."""
            cleanup_server()

        window.events.loaded += on_window_loaded
        window.events.closing += on_window_closing

        logger.info("Starting pywebview desktop event loop...")
        webview.start(debug=False)
        logger.info("pywebview event loop finished cleanly.")
    except Exception as exc:
        logger.exception("Fatal error during desktop window lifecycle: %s", exc)
        show_error_dialog("Desktop Window Error", f"Fatal error during desktop execution:\n\n{exc}")
        sys.exit(1)


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    main()
