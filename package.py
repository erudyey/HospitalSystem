#!/usr/bin/env python
"""One-command standalone executable packaging script."""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for packaging automation."""
    parser = argparse.ArgumentParser(
        description="One-command standalone executable packaging script."
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Fast packaging: reuse PyInstaller build cache and skip frontend if dist/ exists.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Force clean PyInstaller build cache before freezing.",
    )
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="Skip Svelte frontend compilation step.",
    )
    return parser.parse_args()


def run_command(cmd: list[str], cwd: Path) -> None:
    print(f"\n--> Running: {' '.join(cmd)} in {cwd}")
    result = subprocess.run(cmd, cwd=cwd, check=True)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    args = parse_args()
    platform_name = "macOS" if sys.platform == "darwin" else "Windows"
    print(f"=== Packaging HospitalSystem for {platform_name} Desktop ===")

    # 1. Build frontend using Deno (skipped if --no-frontend or (--quick and dist/ exists))
    frontend_dir = REPO_ROOT / "frontend"
    frontend_dist = frontend_dir / "dist" / "index.html"
    should_build_frontend = not args.no_frontend and not (args.quick and frontend_dist.exists())

    if should_build_frontend:
        print("\n[Step 1/3] Compiling Svelte frontend with Deno...")
        run_command(["deno", "task", "build"], cwd=frontend_dir)
    else:
        print("\n[Step 1/3] Reusing existing frontend build in frontend/dist/...")

    # 2. Run PyInstaller
    print("\n[Step 2/3] Freezing desktop bundle with PyInstaller...")
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "desktop.spec",
        "--noconfirm",
    ]
    # Default to --clean for pristine builds unless --quick is passed
    if args.clean or not args.quick:
        pyinstaller_cmd.append("--clean")

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
