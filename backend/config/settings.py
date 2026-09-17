"""Django settings for HospitalSystem."""

import os
import sys
from pathlib import Path

# Base directory: points to repository root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "hospitalsystem-desktop-insecure-key-for-local-loopback"
)
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "backend.clinic.apps.ClinicConfig",
]

MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "backend.clinic.middleware.LoopbackSecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.config.urls"

TEMPLATES = []

WSGI_APPLICATION = "backend.config.wsgi.application"

# Database resolution
if os.environ.get("TESTING") == "True":
    DB_PATH = ":memory:"
elif DEBUG:
    DB_PATH = str(BASE_DIR / "clinic_dev.sqlite3")
else:
    # Desktop / Packaged production mode: %LOCALAPPDATA%\HospitalSystem\clinic.sqlite3
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        app_dir = Path(local_appdata) / "HospitalSystem"
    else:
        app_dir = Path.home() / "AppData" / "Local" / "HospitalSystem"
    app_dir.mkdir(parents=True, exist_ok=True)
    DB_PATH = str(app_dir / "clinic.sqlite3")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
        "OPTIONS": {
            "timeout": 20,
            "init_command": "PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;",
        },
    }
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = False

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Path to frontend production build
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BUNDLE_ROOT = Path(sys._MEIPASS)
else:
    BUNDLE_ROOT = BASE_DIR

FRONTEND_DIST = BUNDLE_ROOT / "frontend" / "dist"

STATICFILES_DIRS = [FRONTEND_DIST] if FRONTEND_DIST.exists() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# CSRF & Security for local loopback
CSRF_COOKIE_HTTPONLY = False  # Allows Svelte frontend to read csrf token cookie
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:*",
    "http://localhost:*",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
