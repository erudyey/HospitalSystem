#!/usr/bin/env python
"""One-command standalone executable packaging script."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def run_command(cmd: list[str], cwd: Path) -> None:
    print(f"\n--> Running: {' '.join(cmd)} in {cwd}")
    result = subprocess.run(cmd, cwd=cwd, check=True)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    print("=== Packaging HospitalSystem for Windows Desktop ===")

    # 1. Build frontend using Deno
    frontend_dir = REPO_ROOT / "frontend"
    print("\n[Step 1/3] Compiling Svelte frontend with Deno...")
    run_command(["deno", "task", "build"], cwd=frontend_dir)

    # 2. Run PyInstaller
    venv_pyinstaller = REPO_ROOT / ".venv" / "Scripts" / "pyinstaller.exe"
    if not venv_pyinstaller.exists():
        venv_pyinstaller = "pyinstaller"

    print("\n[Step 2/3] Freezing desktop bundle with PyInstaller...")
    run_command([str(venv_pyinstaller), "desktop.spec", "--noconfirm", "--clean"], cwd=REPO_ROOT)

    exe_path = REPO_ROOT / "dist" / "HospitalSystem.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(
            f"\n[Step 3/3] Success! Standalone executable generated at:\n  {exe_path} ({size_mb:.1f} MB)"
        )
    else:
        print("\nWarning: Execution finished but dist/HospitalSystem.exe was not found.")


if __name__ == "__main__":
    main()
