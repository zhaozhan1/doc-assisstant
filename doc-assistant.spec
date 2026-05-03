# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path('.').resolve()
FRONTEND_DIST = PROJECT_ROOT / 'frontend' / 'dist'
TEMPLATES_DIR = PROJECT_ROOT / 'backend' / 'app' / 'generation' / 'templates'

a = Analysis(
    ['backend/app/__main__.py'],
    pathex=['backend'],
    binaries=[],
    datas=[
        (str(FRONTEND_DIST), 'frontend'),
        (str(TEMPLATES_DIR), 'app/generation/templates'),
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
        'structlog',
        'structlog.stdlib',
        'structlog.processors',
        'structlog.dev',
        'docx',
        'pdfplumber',
        'pytesseract',
        'openpyxl',
        'pptx',
        'py7zr',
        'pyunpack',
        'PIL',
        'pdf2image',
        'httpx',
        'anthropic',
        'yaml',
        'pydantic',
        'pydantic_settings',
        'chromadb',
        'chromadb.config',
        'chromadb.utils',
        'sqlite3',
        'starlette',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.staticfiles',
        'starlette.responses',
        'fastapi',
        'selectolax',
        'selectors',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy.f2py',
        'scipy',
        'pandas',
        'IPython',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='doc-assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='doc-assistant',
)

app = BUNDLE(
    coll,
    name='公文助手.app',
    icon=None,
    bundle_identifier='com.doc-assistant.app',
    info_plist={
        'CFBundleName': '公文助手',
        'CFBundleDisplayName': '公文助手',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSMinimumSystemVersion': '12.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': False,
    },
)
