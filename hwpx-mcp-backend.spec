# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for hwpx-mcp backend.

Produces a single-directory distribution that can be launched as:
    ./dist/hwpx-mcp-backend/hwpx-mcp-backend [--help]

The binary starts the MCP server using the same entrypoint as
`python -m hwpx_mcp.server`.

Build:
    pyinstaller hwpx-mcp-backend.spec --noconfirm

The resulting dist/hwpx-mcp-backend/ folder is intended to be
copied into electron-ui/resources/backend/ before electron-builder
packages the installer.
"""

import os
import sys
from pathlib import Path

block_cipher = None

repo_root = os.path.abspath(SPECPATH)

templates_source = os.path.join(repo_root, "templates")
security_source = os.path.join(repo_root, "security_module")

datas = []
if os.path.isdir(templates_source):
    datas.append((templates_source, "templates"))
if os.path.isdir(security_source):
    datas.append((security_source, "security_module"))

hidden_imports = [
    "hwpx_mcp",
    "hwpx_mcp.server",
    "hwpx_mcp.config",
    "hwpx_mcp.gateway_server",
    "hwpx_mcp.tools",
    "hwpx_mcp.tools.chart_tools",
    "hwpx_mcp.tools.equation_tools",
    "hwpx_mcp.tools.document_tools",
    "hwpx_mcp.tools.template_tools",
    "hwpx_mcp.tools.unified_tools",
    "hwpx_mcp.tools.hwpx_builder",
    "hwpx_mcp.tools.pyhwp_adapter",
    "hwpx_mcp.tools.cross_platform_controller",
    "hwpx_mcp.tools.controller_factory",
    "hwpx_mcp.tools.hwp_controller_base",
    "hwpx_mcp.tools.hwpx_template_engine",
    "hwpx_mcp.agentic",
    "hwpx_mcp.agentic.gateway",
    "hwpx_mcp.agentic.registry",
    "hwpx_mcp.agentic.retrieval",
    "hwpx_mcp.agentic.router",
    "hwpx_mcp.agentic.grouping",
    "hwpx_mcp.agentic.models",
    "hwpx_mcp.core.xml_parser",
    "hwpx_mcp.core.validator",
    "hwpx_mcp.features.query",
    "hwpx_mcp.features.smart_edit",
    "hwpx_mcp.models.owpml",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "starlette",
    "starlette.applications",
    "starlette.routing",
    "pydantic",
    "pydantic_xml",
    "lxml",
    "lxml.etree",
    "defusedxml",
    "xmlschema",
    "xmldiff",
]

if sys.platform == "win32":
    hidden_imports.extend([
        "hwpx_mcp.tools.windows_hwp_controller",
        "hwpx_mcp.tools.windows_hwp_controller_v2",
        "hwpx_mcp.tools.hwp_table_tools",
        "win32com",
        "win32com.client",
        "pythoncom",
    ])

a = Analysis(
    [os.path.join(repo_root, "hwpx_mcp", "__main__.py")],
    pathex=[repo_root],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        os.path.join(repo_root, "scripts", "pyi_rth_hwpx_patch.py"),
    ],
    excludes=[
        "tkinter",
        "test",
        "unittest",
        "pytest",
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hwpx-mcp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="hwpx-mcp-backend",
)
