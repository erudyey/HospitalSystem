"""Regression checks for desktop database-mode restarts."""

import os
import sys
from unittest.mock import patch

import pytest

from desktop.relaunch import restart_application


@pytest.mark.parametrize("mode", ["clinic", "demo"])
@pytest.mark.parametrize("frozen", [False, True])
def test_restart_uses_fresh_runtime_and_explicit_mode(mode, frozen):
    with (
        patch.object(sys, "frozen", frozen, create=True),
        patch.dict(os.environ, {"HOSPITAL_SESSION_TOKEN": "old-token", "DEBUG": "True"}),
        patch("desktop.relaunch.subprocess.Popen") as launch,
    ):
        restart_application(mode)
    command = launch.call_args.args[0]
    environment = launch.call_args.kwargs["env"]
    assert command[0] == sys.executable
    assert command[-2:] == [f"--{mode}", "--signed-out"]
    assert len(command) == (3 if frozen else 4)
    assert environment["HOSPITAL_MODE"] == mode
    assert environment["DEBUG"] == "False"
    assert environment["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert "HOSPITAL_SESSION_TOKEN" not in environment


def test_invalid_mode_cannot_launch_a_process():
    with patch("desktop.relaunch.subprocess.Popen") as launch:
        with pytest.raises(ValueError):
            restart_application("unknown")
        launch.assert_not_called()
