"""Pytest configuration and test environment initialization."""

import os

# Guarantee that tests always execute against in-memory SQLite and isolated settings
os.environ["TESTING"] = "True"
