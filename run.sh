#!/usr/bin/env bash
# Task runner script for HospitalSystem development, testing, and packaging on macOS and Linux.
# Usage:
#   ./run.sh setup
#   ./run.sh dev
#   ./run.sh desktop
#   ./run.sh test
#   ./run.sh format
#   ./run.sh package
#   ./run.sh test-package

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

COMMAND="${1:-}"
OPTION="${2:-}"

if [ -z "$COMMAND" ]; then
    echo "Usage: ./run.sh [setup|dev|desktop|test|format|package|test-package] [--quick]"
    exit 1
fi

VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
VENV_PYTEST="$REPO_ROOT/.venv/bin/pytest"
VENV_RUFF="$REPO_ROOT/.venv/bin/ruff"

case "$COMMAND" in
    setup)
        echo "Setting up project dependencies..."
        if ! command -v uv >/dev/null 2>&1; then
            echo "Error: 'uv' is required but not installed."
            echo "Install via Homebrew: brew install uv"
            echo "Or via curl: curl -LsSf https://astral.sh/uv/install.sh | sh"
            exit 1
        fi
        if ! command -v deno >/dev/null 2>&1; then
            echo "Error: 'deno' is required but not installed."
            echo "Install via Homebrew: brew install deno"
            echo "Or via curl: curl -fsSL https://deno.land/install.sh | sh"
            exit 1
        fi

        if [ ! -d "$REPO_ROOT/.venv" ]; then
            uv venv "$REPO_ROOT/.venv"
        fi

        uv pip install --python "$VENV_PYTHON" -e ".[dev]"
        (cd "$REPO_ROOT/frontend" && deno install)
        echo "Setup complete!"
        ;;

    dev)
        echo "Starting development servers (Vite + Django)..."
        export DJANGO_SETTINGS_MODULE="backend.config.settings"
        export DEBUG="True"

        "$VENV_PYTHON" "$REPO_ROOT/backend/manage.py" migrate

        # Trap signals to terminate background Vite server cleanly
        trap 'kill $(jobs -p) 2>/dev/null || true' EXIT INT TERM

        (cd "$REPO_ROOT/frontend" && deno task dev) &
        "$VENV_PYTHON" "$REPO_ROOT/backend/manage.py" runserver 127.0.0.1:8000
        ;;

    desktop)
        echo "Launching HospitalSystem Desktop..."
        if [ ! -f "$REPO_ROOT/frontend/dist/index.html" ]; then
            echo "Building frontend bundle first..."
            (cd "$REPO_ROOT/frontend" && deno task build)
        fi
        "$VENV_PYTHON" "$REPO_ROOT/desktop/launcher.py"
        ;;

    test)
        if [ "$OPTION" != "--quick" ]; then
            echo "Running basedpyright strict type checks..."
            "$VENV_PYTHON" -m basedpyright
            echo ""
        fi
        echo "Running backend automated test suite..."
        TESTING="True" "$VENV_PYTEST" "$REPO_ROOT/backend/tests"
        ;;

    format)
        echo "Running Ruff linter and formatter..."
        "$VENV_RUFF" check --fix "$REPO_ROOT/backend" "$REPO_ROOT/desktop"
        "$VENV_RUFF" format "$REPO_ROOT/backend" "$REPO_ROOT/desktop"
        (cd "$REPO_ROOT/frontend" && deno fmt)
        ;;

    package)
        echo "Packaging HospitalSystem desktop bundle..."
        PACKAGE_ARGS=()
        if [ "$OPTION" = "--quick" ]; then
            PACKAGE_ARGS+=("--quick")
        fi
        "$VENV_PYTHON" "$REPO_ROOT/package.py" "${PACKAGE_ARGS[@]}"
        echo ""
        echo "Running automated bundle verification..."
        "$VENV_PYTHON" "$REPO_ROOT/desktop/verify_bundle.py"
        ;;

    test-package)
        echo "Running automated bundle verification..."
        "$VENV_PYTHON" "$REPO_ROOT/desktop/verify_bundle.py"
        ;;

    *)
        echo "Unknown command: $COMMAND"
        echo "Usage: ./run.sh [setup|dev|desktop|test|format|package|test-package]"
        exit 1
        ;;
esac
