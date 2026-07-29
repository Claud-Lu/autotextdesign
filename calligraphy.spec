# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 书法字体制作器"""

import os
import sys

app_version = os.environ.get('APP_VERSION', '1.2.0').removeprefix('v')

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app', 'app'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'multipart',
        'app.main',
        'app.api.routes.font',
        'app.api.routes.preprocess',
        'app.middleware.request_guard',
        'app.services.font_importer',
        'app.services.preprocessor',
        'app.services.contour_fitter',
        'app.services.font_builder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='书法字体制作器',
    debug=False,
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
    upx=True,
    upx_exclude=[],
    name='书法字体制作器',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='书法字体制作器.app',
        info_plist={
            'CFBundleShortVersionString': app_version,
            'CFBundleVersion': app_version,
            'CFBundleIdentifier': 'com.autotextdesign.app',
            'NSHighResolutionCapable': True,
        },
    )
