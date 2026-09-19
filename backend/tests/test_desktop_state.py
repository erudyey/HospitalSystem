"""Tests for desktop native persistence helpers."""

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from desktop.launcher import DesktopHostApi


class DesktopHostApiTests(SimpleTestCase):
    """Verify remembered desktop state survives origin and process changes."""

    def test_persistent_state_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "persistent_state.json"
            api = DesktopHostApi("loopback-token", state_file=state_file)

            self.assertTrue(api.save_user_token("staff-session-token"))
            self.assertTrue(api.save_demo_mode(False))

            restored = DesktopHostApi("new-loopback-token", state_file=state_file)
            self.assertEqual(
                restored.load_persistent_state(),
                {"user_token": "staff-session-token", "demo_mode": False},
            )
            self.assertEqual(restored.get_session_token(), "new-loopback-token")

    def test_clearing_user_token_preserves_demo_preference(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "persistent_state.json"
            api = DesktopHostApi("loopback-token", state_file=state_file)
            self.assertTrue(api.save_user_token("staff-session-token"))
            self.assertTrue(api.save_demo_mode(True))
            self.assertTrue(api.clear_user_token())

            self.assertEqual(api.load_persistent_state(), {"demo_mode": True})

    def test_blank_user_token_is_not_persisted(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "persistent_state.json"
            api = DesktopHostApi("loopback-token", state_file=state_file)

            self.assertFalse(api.save_user_token("   "))
            self.assertEqual(api.load_persistent_state(), {})
