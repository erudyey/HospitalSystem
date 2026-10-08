"""Pytest configuration and test environment initialization."""

import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

# Guarantee that tests always execute against in-memory SQLite and isolated settings
os.environ["TESTING"] = "True"


@pytest.fixture(autouse=True)
def clinic_clock():
    """Keep appointment fixtures independent of the workstation date."""
    with (
        patch.dict(os.environ, {"HOSPITAL_TIME_ZONE": "UTC"}),
        patch(
            "backend.clinic.services.clinic_now", return_value=datetime(2026, 9, 1, 8, tzinfo=UTC)
        ),
    ):
        yield
