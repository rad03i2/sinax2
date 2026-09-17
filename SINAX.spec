# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Bundle the complete PySide6 runtime plus SINAX modules that are imported lazily.
pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all('PySide6')
yaml_datas, yaml_binaries, yaml_hiddenimports = collect_all('yaml')
markdown_datas, markdown_binaries, markdown_hiddenimports = collect_all('markdown')
pptx_datas, pptx_binaries, pptx_hiddenimports = collect_all('pptx')

hiddenimports = list(dict.fromkeys(
    pyside_hiddenimports
    + yaml_hiddenimports
    + markdown_hiddenimports
    + pptx_hiddenimports
    + collect_submodules('app')
    + collect_submodules('psutil')
    + ['psutil']
))

# Keep runtime assets at the same relative paths used by the source tree so
# qml_helper.py and the rest of SINAX can resolve them in a frozen build.
datas = pyside_datas + yaml_datas + markdown_datas + pptx_datas + [
    ('app/ui/qml', 'app/ui/qml'),
    ('app/ui/themes', 'app/ui/themes'),
    ('app/resources', 'app/resources'),
    ('resources', 'resources'),
]


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=pyside_binaries + yaml_binaries + markdown_binaries + pptx_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SINAX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SINAX',
)
