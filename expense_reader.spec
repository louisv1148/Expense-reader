# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get the current directory
project_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['expense_reader_app.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        # Include templates
        (os.path.join(project_dir, 'templates'), 'templates'),
        # Include static files
        (os.path.join(project_dir, 'static'), 'static'),
        # Include database file (if exists)
        (os.path.join(project_dir, 'expenses.db'), '.') if os.path.exists(os.path.join(project_dir, 'expenses.db')) else None,
        # Include other Python files
        (os.path.join(project_dir, 'app.py'), '.'),
        (os.path.join(project_dir, 'database.py'), '.'),
        (os.path.join(project_dir, 'expense_reader.py'), '.'),
        (os.path.join(project_dir, 'excel_generator.py'), '.'),
        (os.path.join(project_dir, 'pdf_generator.py'), '.'),
        (os.path.join(project_dir, 'filename_utils.py'), '.'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'jinja2',
        'sqlite3',
        'pandas',
        'openpyxl',
        'reportlab',
        'PIL',
        'openai',
        'pytesseract',
        'threading',
        'webbrowser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Filter out None values from datas
a.datas = [x for x in a.datas if x is not None]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Expense Reader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to True to show terminal output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add an icon file here if you have one
)

# Create a Mac app bundle
app = BUNDLE(
    exe,
    name='Expense Reader.app',
    icon=None,
    bundle_identifier='com.expensereader.app',
    version='1.0.0',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleName': 'Expense Reader',
        'CFBundleDisplayName': 'Expense Reader',
        'CFBundleIdentifier': 'com.expensereader.app',
        'NSHumanReadableCopyright': 'Copyright © 2025',
        'LSMinimumSystemVersion': '10.13.0',
    },
)