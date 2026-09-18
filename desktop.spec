# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

REPO_ROOT = Path(__file__).resolve().parent if '__file__' in locals() else Path('.').resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FRONTEND_DIST = REPO_ROOT / 'frontend' / 'dist'

datas = [
    (str(FRONTEND_DIST), 'frontend/dist'),
    ('backend', 'backend'),
]
datas += collect_data_files('webview')

platform_imports = []
if sys.platform == "win32":
    platform_imports = [
        'clr',
        'pythonnet',
    ]
elif sys.platform == "darwin":
    platform_imports = (
        collect_submodules('objc')
        + collect_submodules('WebKit')
        + collect_submodules('Foundation')
        + collect_submodules('AppKit')
    )

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
    + platform_imports
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
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='HospitalSystem.app',
        icon=None,
        bundle_identifier='com.hospitalsystem.clinic',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
        },
    )
