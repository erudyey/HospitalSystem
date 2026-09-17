# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

block_cipher = None

REPO_ROOT = Path('.').resolve()
FRONTEND_DIST = REPO_ROOT / 'frontend' / 'dist'

datas = [
    (str(FRONTEND_DIST), 'frontend/dist'),
]

# Add backend migrations and templates if any
datas.append(('backend/clinic/migrations', 'backend/clinic/migrations'))

a = Analysis(
    ['desktop/launcher.py'],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'waitress',
        'whitenoise',
        'django',
        'backend.config.settings',
        'backend.config.urls',
        'backend.config.wsgi',
        'backend.clinic',
        'backend.clinic.apps',
        'backend.clinic.models',
        'backend.clinic.views',
        'backend.clinic.services',
        'backend.clinic.middleware',
        'backend.clinic.importer',
        'webview',
        'clr',
        'pythonnet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HospitalSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
