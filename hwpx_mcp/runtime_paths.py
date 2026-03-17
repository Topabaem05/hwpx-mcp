from __future__ import annotations

import sys
from pathlib import Path


def get_bundle_root() -> Path:
    """Return the runtime root for source and frozen builds."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_path = Path(meipass)
        if (meipass_path / "templates").exists() or (
            meipass_path / "security_module"
        ).exists():
            return meipass_path

        executable = getattr(sys, "executable", "")
        if executable:
            executable_parent = Path(executable).resolve().parent
            if (executable_parent / "templates").exists() or (
                executable_parent / "security_module"
            ).exists():
                return executable_parent

        return meipass_path
    return Path(__file__).resolve().parent.parent


def get_templates_dir() -> Path:
    """Return the bundled templates directory."""
    return get_bundle_root() / "templates"


def get_template_index_path() -> Path:
    """Return the bundled template index path."""
    return get_templates_dir() / "template_index.json"


def get_security_module_path() -> Path:
    """Return the bundled Windows security module DLL path."""
    return get_bundle_root() / "security_module" / "FilePathCheckerModuleExample.dll"
