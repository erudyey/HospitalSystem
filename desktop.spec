# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

REPO_ROOT = Path('.').resolve()
FRONTEND_DIST = REPO_ROOT / 'frontend' / 'dist'

datas = [
    (str(FRONTEND_DIST), 'frontend/dist'),
    ('backend/clinic/migrations', 'backend/clinic/migrations'),
]
datas += collect_data_files('webview')

hiddenimports = (
    collect_submodules('whitenoise')
    + collect_submodules('backend')
    + collect_submodules('django.middleware')
    + collect_submodules('django.contrib.staticfiles')
    + collect_submodules('django.db.backends.sqlite3')
    + collect_submodules('django.db.migrations')
    + collect_submodules('django.core.management')
    + collect_submodules('waitress')
    + collect_submodules('webview')
    + [
        'clr',
        'pythonnet',
    ]
)

a = Analysis(
    ['desktop/launcher.py'],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
