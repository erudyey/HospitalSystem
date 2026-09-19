"""Restart the desktop process with an explicit, isolated database mode."""

import os
import subprocess
import sys
from pathlib import Path


def restart_application(mode: str) -> None:
    """Launch a fresh process after the previous window and instance lock close."""
    if mode not in ("clinic", "demo"):
        raise ValueError("Unknown application mode.")
    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command.append(str(Path(__file__).with_name("launcher.py")))
    command.extend([f"--{mode}", "--signed-out"])
    environment = os.environ.copy()
    environment["HOSPITAL_MODE"] = mode
    environment["DEBUG"] = "False"
    environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    environment.pop("HOSPITAL_SESSION_TOKEN", None)
    subprocess.Popen(command, env=environment)
