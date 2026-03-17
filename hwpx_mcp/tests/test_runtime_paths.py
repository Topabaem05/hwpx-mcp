from pathlib import Path
import sys

from hwpx_mcp.runtime_paths import (
    get_bundle_root,
    get_security_module_path,
    get_template_index_path,
    get_templates_dir,
)


def test_bundle_root_uses_repo_root_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    expected_root = Path(__file__).resolve().parents[2]

    assert get_bundle_root() == expected_root
    assert get_templates_dir() == expected_root / "templates"
    assert (
        get_template_index_path() == expected_root / "templates" / "template_index.json"
    )


def test_bundle_root_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert get_bundle_root() == tmp_path
    assert get_templates_dir() == tmp_path / "templates"
    assert (
        get_security_module_path()
        == tmp_path / "security_module" / "FilePathCheckerModuleExample.dll"
    )


def test_bundle_root_prefers_executable_parent_when_meipass_has_no_resources(
    monkeypatch, tmp_path
):
    meipass_dir = tmp_path / "_internal"
    exe_dir = tmp_path / "app"
    meipass_dir.mkdir()
    (exe_dir / "templates").mkdir(parents=True)

    monkeypatch.setattr(sys, "_MEIPASS", str(meipass_dir), raising=False)
    monkeypatch.setattr(
        sys,
        "executable",
        str(exe_dir / "hwpx-mcp-backend.exe"),
        raising=False,
    )

    assert get_bundle_root() == exe_dir
