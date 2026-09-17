"""Desktop application launcher for HospitalSystem.

Manages process lifecycle, ephemeral socket pre-binding, Waitress daemon thread,
in-memory session token injection, WebView2 runtime detection, and clean shutdown.
"""

import atexit
import contextlib
import ctypes
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

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Single Instance Check on Windows
MUTEX_NAME = "Local\\HospitalSystem_AppMutex"
kernel32 = ctypes.windll.kernel32
mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    ctypes.windll.user32.MessageBoxW(
        0,
        "Hospital Management System is already running.\n\nPlease check your taskbar.",
        "HospitalSystem - Already Running",
        0x40 | 0x1,  # MB_ICONINFORMATION | MB_OK
    )
    sys.exit(0)


def show_error_dialog(title: str, message: str) -> None:
    """Display a native Windows error dialog."""
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x10 | 0x0)  # MB_ICONERROR | MB_OK


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
                if resp.status == 200:
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

    # 3. Initialize Django and Waitress WSGI server
    try:
        import django

        django.setup()
        from django.core.management import call_command

        call_command("migrate", interactive=False)

        from waitress.server import create_server

        from backend.config.wsgi import application
    except Exception as exc:
        show_error_dialog("Startup Error", f"Failed to initialize server components:\n\n{exc}")
        sys.exit(1)

    server = create_server(application, host="127.0.0.1", port=port, threads=4)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Clean shutdown hook
    def cleanup_server():
        with contextlib.suppress(Exception):
            server.close()

    atexit.register(cleanup_server)

    # 4. Wait for readiness probe
    health_url = f"http://127.0.0.1:{port}/api/health/"
    if not wait_for_server(health_url, timeout_sec=8.0):
        show_error_dialog(
            "Connection Timeout",
            f"The local backend server failed to respond within 8 seconds at {health_url}.\nShutting down.",
        )
        sys.exit(1)

    # 5. Import and verify pywebview / WebView2
    try:
        import webview
    except ImportError as exc:
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

    window = webview.create_window(
        title="Hospital Management System",
        url=f"http://127.0.0.1:{port}/?token={session_token}",
        width=1100,
        height=740,
        min_size=(920, 600),
        js_api=api,
    )
    assert window is not None

    def on_window_loaded():
        """Inject session token into window memory after load."""
        window.evaluate_js(f"window.__SESSION_TOKEN__ = '{session_token}';")

    def on_window_closing():
        """Cleanly close server socket when the user closes the window."""
        cleanup_server()

    window.events.loaded += on_window_loaded
    window.events.closing += on_window_closing

    # 6. Start the desktop event loop on the main thread
    webview.start(debug=False)


if __name__ == "__main__":
    main()
