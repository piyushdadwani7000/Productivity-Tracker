# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [('static', 'static')]
datas += collect_data_files('sklearn')

hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'starlette',
    'pydantic',
    'pydantic_core',
    'bs4',
    'soupsieve',
    'uiautomation',
    'comtypes',
    'win32gui',
    'win32process',
    'win32api',
    'psutil',
    'sklearn',
    'sklearn.feature_extraction.text',
    'sklearn.naive_bayes',
    'sklearn.pipeline',
    'sklearn.utils._typedefs',
    'pandas',
    'numpy',
]

excludes = [
    'tkinter',
    'customtkinter',
    'matplotlib',
    'IPython',
    'pytest',
    'unittest',
    'scipy.stats.tests',
    'pandas.tests',
    'sklearn.tests',
    'scipy.tests',
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FocusTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
