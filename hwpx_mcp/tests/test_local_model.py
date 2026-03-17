from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from hwpx_mcp.agentic import local_model


def _fake_torch_spec(torch_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        origin=str(torch_root / "__init__.py"),
        submodule_search_locations=[str(torch_root)],
    )


def test_configure_windows_torch_dll_directories_registers_paths(
    monkeypatch,
    tmp_path: Path,
):
    torch_root = tmp_path / "Lib" / "site-packages" / "torch"
    torch_root.mkdir(parents=True)
    (torch_root / "__init__.py").write_text("", encoding="utf-8")
    torch_lib = torch_root / "lib"
    torch_lib.mkdir()
    torch_bin = torch_root / "bin"
    torch_bin.mkdir()

    monkeypatch.setattr(local_model, "_is_windows", lambda: True)
    monkeypatch.setattr(
        local_model,
        "find_spec",
        lambda name: _fake_torch_spec(torch_root) if name == "torch" else None,
    )
    monkeypatch.setattr(local_model, "_WINDOWS_DLL_DIRECTORY_HANDLES", [])
    monkeypatch.setattr(local_model, "_WINDOWS_DLL_DIRECTORIES", set())

    calls: list[str] = []

    def fake_add_dll_directory(path: str) -> object:
        calls.append(path)
        return object()

    monkeypatch.setattr(
        local_model.os, "add_dll_directory", fake_add_dll_directory, raising=False
    )
    monkeypatch.setenv("PATH", "C:/Windows/System32")

    manager = local_model.LocalTransformersModelManager(
        model_home=str(tmp_path / "models")
    )

    manager._configure_windows_torch_dll_directories()

    assert calls == [str(torch_lib), str(torch_bin)]
    assert manager._dll_directories_configured is True
    assert len(local_model._WINDOWS_DLL_DIRECTORY_HANDLES) == 2
    assert (
        Path(local_model.os.environ["PATH"].split(local_model.os.pathsep)[0])
        == torch_lib
    )
    assert (
        Path(local_model.os.environ["PATH"].split(local_model.os.pathsep)[1])
        == torch_bin
    )


def test_configure_windows_torch_dll_directories_deduplicates_path_entries(
    monkeypatch,
    tmp_path: Path,
):
    torch_root = tmp_path / "Lib" / "site-packages" / "torch"
    torch_root.mkdir(parents=True)
    (torch_root / "__init__.py").write_text("", encoding="utf-8")
    torch_lib = torch_root / "lib"
    torch_lib.mkdir()

    monkeypatch.setattr(local_model, "_is_windows", lambda: True)
    monkeypatch.setattr(
        local_model,
        "find_spec",
        lambda name: _fake_torch_spec(torch_root) if name == "torch" else None,
    )
    monkeypatch.setattr(local_model, "_WINDOWS_DLL_DIRECTORY_HANDLES", [])
    monkeypatch.setattr(local_model, "_WINDOWS_DLL_DIRECTORIES", set())
    monkeypatch.setattr(
        local_model.os, "add_dll_directory", lambda path: object(), raising=False
    )
    monkeypatch.setenv(
        "PATH", local_model.os.pathsep.join([str(torch_lib), "C:/Windows/System32"])
    )

    manager = local_model.LocalTransformersModelManager(
        model_home=str(tmp_path / "models")
    )

    manager._configure_windows_torch_dll_directories()

    path_entries = local_model.os.environ["PATH"].split(local_model.os.pathsep)
    assert path_entries.count(str(torch_lib)) == 1


def test_configure_windows_torch_dll_directories_is_process_idempotent(
    monkeypatch,
    tmp_path: Path,
):
    torch_root = tmp_path / "Lib" / "site-packages" / "torch"
    torch_root.mkdir(parents=True)
    (torch_root / "__init__.py").write_text("", encoding="utf-8")
    torch_lib = torch_root / "lib"
    torch_lib.mkdir()
    torch_bin = torch_root / "bin"
    torch_bin.mkdir()

    monkeypatch.setattr(local_model, "_is_windows", lambda: True)
    monkeypatch.setattr(
        local_model,
        "find_spec",
        lambda name: _fake_torch_spec(torch_root) if name == "torch" else None,
    )
    monkeypatch.setattr(local_model, "_WINDOWS_DLL_DIRECTORY_HANDLES", [])
    monkeypatch.setattr(local_model, "_WINDOWS_DLL_DIRECTORIES", set())

    calls: list[str] = []
    monkeypatch.setattr(
        local_model.os,
        "add_dll_directory",
        lambda path: calls.append(path) or object(),
        raising=False,
    )
    monkeypatch.setenv("PATH", "C:/Windows/System32")

    first = local_model.LocalTransformersModelManager(
        model_home=str(tmp_path / "models-a")
    )
    second = local_model.LocalTransformersModelManager(
        model_home=str(tmp_path / "models-b")
    )

    first._configure_windows_torch_dll_directories()
    second._configure_windows_torch_dll_directories()

    assert calls == [str(torch_lib), str(torch_bin)]
