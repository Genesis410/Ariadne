# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Ariadne (onedir distribution)."""

from PyInstaller.utils.hooks import collect_all

datas = [('src/ariadne/cli/templates', 'ariadne/cli/templates')]
binaries = []
hiddenimports = [
    'ariadne',
    'ariadne.cli.main',
    'ariadne.checker.rules',
    'ariadne.shrinker.bounding_box',
    'ariadne.runner.ipc',
    'ariadne.runner.engine',
    'ariadne.vault.manager',
    'ariadne.license.verifier',
    'ariadne.ui.renderer',
]

# Ensure complete C-extensions and metadata for critical libraries
for pkg in ['pydantic', 'pydantic_core', 'rich', 'cryptography']:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    ['src/ariadne/cli/main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ariadne',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ariadne',
)
