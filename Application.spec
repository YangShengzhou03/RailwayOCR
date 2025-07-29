# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

a = Analysis(
    ['Application.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/*', 'resources'),
        ('RailwayOCR_version_info.txt', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

coll = COLLECT(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='Application',
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
)