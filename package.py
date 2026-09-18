#!/usr/bin/env python
"""One-command standalone executable packaging script."""

import contextlib
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


def ensure_executable_unlocked() -> None:
    """Ensure previous running instances of the executable are terminated before packaging."""
    if sys.platform == "win32":
        exe_path = REPO_ROOT / "dist" / "HospitalSystem.exe"
        if exe_path.exists():
            with contextlib.suppress(Exception):
                subprocess.run(
                    ["taskkill", "/F", "/IM", exe_path.name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
    elif sys.platform == "darwin":
        with contextlib.suppress(Exception):
            subprocess.run(
                ["pkill", "-f", "HospitalSystem"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def main() -> None:
    platform_name = "macOS" if sys.platform == "darwin" else "Windows"
    print(f"=== Packaging HospitalSystem for {platform_name} Desktop ===")

    # 1. Build frontend using Deno
    frontend_dir = REPO_ROOT / "frontend"
    print("\n[Step 1/3] Compiling Svelte frontend with Deno...")
    run_command(["deno", "task", "build"], cwd=frontend_dir)

    # 2. Run PyInstaller
    ensure_executable_unlocked()

    print("\n[Step 2/3] Freezing desktop bundle with PyInstaller...")
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "desktop.spec",
        "--noconfirm",
        "--clean",
    ]
    run_command(pyinstaller_cmd, cwd=REPO_ROOT)

    # 3. Report generated output
    if sys.platform == "darwin":
        app_path = REPO_ROOT / "dist" / "HospitalSystem.app"
        bin_path = REPO_ROOT / "dist" / "HospitalSystem"
        if app_path.exists():
            print(f"\n[Step 3/3] Success! macOS Application bundle generated at:\n  {app_path}")
        elif bin_path.exists():
            size_mb = bin_path.stat().st_size / (1024 * 1024)
            print(
                f"\n[Step 3/3] Success! Standalone executable generated at:\n  {bin_path} ({size_mb:.1f} MB)"
            )
        else:
            print("\nWarning: Execution finished but output bundle was not found.")
    else:
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
