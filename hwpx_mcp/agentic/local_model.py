from __future__ import annotations

import asyncio
import importlib
from importlib.util import find_spec
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Literal
from typing import Protocol


LOCAL_PROVIDER = "local"
LOCAL_MODEL_ENV = "HWPX_LOCAL_MODEL_ID"
LOCAL_MODEL_HOME_ENV = "HWPX_LOCAL_MODEL_HOME"
HF_HOME_ENV = "HF_HOME"
HF_HUB_DISABLE_SYMLINKS_WARNING_ENV = "HF_HUB_DISABLE_SYMLINKS_WARNING"
LOCAL_DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
_WINDOWS_DLL_DIRECTORY_HANDLES: list[object] = []
_WINDOWS_DLL_DIRECTORIES: set[str] = set()


class LocalModelError(RuntimeError):
    pass


@dataclass(slots=True)
class LocalModelSnapshot:
    configured: bool
    ready: bool
    downloaded: bool
    downloading: bool
    model_id: str
    provider: str
    model_home: str
    download_path: str
    detail: str = ""
    error: str = ""
    dependency_installed: bool = False

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "configured": self.configured,
            "ready": self.ready,
            "downloaded": self.downloaded,
            "downloading": self.downloading,
            "model_id": self.model_id,
            "provider": self.provider,
            "model_home": self.model_home,
            "download_path": self.download_path,
            "dependency_installed": self.dependency_installed,
        }
        if self.detail:
            payload["detail"] = self.detail
        if self.error:
            payload["error"] = self.error
        return payload


class LocalModelManagerProtocol(Protocol):
    model_id: str

    def status(self) -> LocalModelSnapshot: ...

    async def ensure_downloaded(self, *, force: bool = False) -> dict[str, object]: ...

    async def chat_completions(
        self,
        *,
        model: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None,
        tool_choice: str | None,
    ) -> dict[str, object]: ...


def _sanitize_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def _default_model_home() -> Path:
    explicit = os.getenv(LOCAL_MODEL_HOME_ENV, "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data).expanduser().resolve() / "HWPX MCP" / "models"

    return Path.home().resolve() / ".cache" / "hwpx-mcp" / "models"


def _default_hf_home() -> Path:
    explicit = os.getenv(HF_HOME_ENV, "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data).expanduser().resolve() / "HWPX MCP" / "hf"

    return Path.home().resolve() / ".cache" / "hwpx-mcp" / "hf"


def _is_windows() -> bool:
    return os.name == "nt"


def _torch_runtime_directories() -> list[Path]:
    try:
        spec = find_spec("torch")
    except (ImportError, AttributeError, ValueError):
        return []
    if spec is None:
        return []

    torch_root: Path | None = None
    search_locations = spec.submodule_search_locations
    if search_locations:
        torch_root = Path(next(iter(search_locations))).resolve()
    elif spec.origin:
        torch_root = Path(spec.origin).resolve().parent
    if torch_root is None:
        return []

    candidates = [
        torch_root / "lib",
        torch_root / "bin",
    ]
    directories: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.is_dir() or candidate in seen:
            continue
        seen.add(candidate)
        directories.append(candidate)
    return directories


class LocalTransformersModelManager:
    def __init__(
        self,
        *,
        model_id: str | None = None,
        model_home: str | None = None,
        hf_home: str | None = None,
    ):
        configured_model = model_id or os.getenv(LOCAL_MODEL_ENV, "")
        self.model_id = configured_model.strip() or LOCAL_DEFAULT_MODEL
        self.model_home = (
            Path(model_home).expanduser().resolve()
            if isinstance(model_home, str) and model_home.strip()
            else _default_model_home()
        )
        self.hf_home = (
            Path(hf_home).expanduser().resolve()
            if isinstance(hf_home, str) and hf_home.strip()
            else _default_hf_home()
        )
        self._download_lock = asyncio.Lock()
        self._loaded_model: Any = None
        self._loaded_tokenizer: Any = None
        self._last_error = ""
        self._dll_directories_configured = False

    @property
    def local_dir(self) -> Path:
        return self.model_home / _sanitize_model_id(self.model_id)

    def _set_hf_environment(self) -> None:
        os.environ.setdefault(HF_HOME_ENV, str(self.hf_home))
        os.environ.setdefault(HF_HUB_DISABLE_SYMLINKS_WARNING_ENV, "1")
        os.environ.setdefault(LOCAL_MODEL_HOME_ENV, str(self.model_home))
        os.environ.setdefault(LOCAL_MODEL_ENV, self.model_id)

    def _dependency_error(self) -> str:
        required_modules = (
            "huggingface_hub",
            "torch",
            "transformers",
        )
        for module_name in required_modules:
            try:
                spec = find_spec(module_name)
            except (ImportError, AttributeError, ValueError) as error:
                return str(error)
            if spec is None:
                return f"No module named '{module_name}'"
        return ""

    def _configure_windows_torch_dll_directories(self) -> None:
        if not _is_windows() or self._dll_directories_configured:
            return

        directories = _torch_runtime_directories()
        if not directories:
            self._dll_directories_configured = True
            return

        add_dll_directory = getattr(os, "add_dll_directory", None)
        if callable(add_dll_directory):
            for directory in directories:
                normalized = os.path.normcase(os.path.normpath(str(directory)))
                if normalized in _WINDOWS_DLL_DIRECTORIES:
                    continue
                _WINDOWS_DLL_DIRECTORY_HANDLES.append(add_dll_directory(str(directory)))
                _WINDOWS_DLL_DIRECTORIES.add(normalized)

        current_path = os.environ.get("PATH", "")
        path_entries = [entry for entry in current_path.split(os.pathsep) if entry]
        normalized_entries = {
            os.path.normcase(os.path.normpath(entry)) for entry in path_entries
        }

        missing_entries: list[str] = []
        for directory in directories:
            directory_str = str(directory)
            normalized = os.path.normcase(os.path.normpath(directory_str))
            if normalized in normalized_entries:
                continue
            normalized_entries.add(normalized)
            missing_entries.append(directory_str)

        if missing_entries:
            os.environ["PATH"] = os.pathsep.join([*missing_entries, *path_entries])

        self._dll_directories_configured = True

    def _is_downloaded(self) -> bool:
        target = self.local_dir
        return target.exists() and (target / "config.json").exists()

    def status(self) -> LocalModelSnapshot:
        dependency_error = self._dependency_error()
        downloaded = self._is_downloaded()
        ready = downloaded and dependency_error == ""
        detail = ""
        if dependency_error:
            detail = f"local_dependencies_missing: {dependency_error}"
        elif downloaded:
            detail = "local_model_ready"
        else:
            detail = "local_model_not_downloaded"
        if self._last_error:
            detail = self._last_error
        return LocalModelSnapshot(
            configured=ready,
            ready=ready,
            downloaded=downloaded,
            downloading=self._download_lock.locked(),
            model_id=self.model_id,
            provider=LOCAL_PROVIDER,
            model_home=str(self.model_home),
            download_path=str(self.local_dir),
            detail=detail,
            error=self._last_error,
            dependency_installed=dependency_error == "",
        )

    async def ensure_downloaded(self, *, force: bool = False) -> dict[str, object]:
        async with self._download_lock:
            self._last_error = ""
            status = self.status()
            if status.downloaded and not force:
                return status.to_payload()

            dependency_error = self._dependency_error()
            if dependency_error:
                self._last_error = f"local_dependencies_missing: {dependency_error}"
                raise LocalModelError(self._last_error)

            self._set_hf_environment()
            self.local_dir.mkdir(parents=True, exist_ok=True)

            def _download() -> str:
                huggingface_hub = importlib.import_module("huggingface_hub")
                snapshot_download = getattr(huggingface_hub, "snapshot_download")

                return snapshot_download(
                    repo_id=self.model_id,
                    local_dir=str(self.local_dir),
                    local_dir_use_symlinks=False,
                    resume_download=True,
                )

            try:
                await asyncio.to_thread(_download)
            except Exception as error:
                self._last_error = f"local_model_download_failed: {error}"
                raise LocalModelError(self._last_error) from error

            self._last_error = ""
            return self.status().to_payload()

    async def ensure_loaded(self) -> None:
        if self._loaded_model is not None and self._loaded_tokenizer is not None:
            return

        status = self.status()
        if not status.downloaded:
            raise LocalModelError("local_model_not_downloaded")
        dependency_error = self._dependency_error()
        if dependency_error:
            raise LocalModelError(f"local_dependencies_missing: {dependency_error}")

        self._set_hf_environment()
        self._configure_windows_torch_dll_directories()

        def _load() -> tuple[Any, Any]:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
            auto_model_cls = getattr(transformers, "AutoModelForCausalLM")
            auto_tokenizer_cls = getattr(transformers, "AutoTokenizer")

            tokenizer = auto_tokenizer_cls.from_pretrained(
                str(self.local_dir),
                trust_remote_code=True,
                local_files_only=True,
            )
            model = auto_model_cls.from_pretrained(
                str(self.local_dir),
                trust_remote_code=True,
                torch_dtype="auto",
                local_files_only=True,
            )
            if not torch.cuda.is_available():
                model.to("cpu")
            model.eval()
            return tokenizer, model

        self._loaded_tokenizer, self._loaded_model = await asyncio.to_thread(_load)

    async def chat_completions(
        self,
        *,
        model: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None,
        tool_choice: str | None,
    ) -> dict[str, object]:
        _ = (model, tool_choice)
        await self.ensure_loaded()
        tokenizer: Any = self._loaded_tokenizer
        local_model: Any = self._loaded_model
        if tokenizer is None or local_model is None:
            raise LocalModelError("local_model_not_loaded")

        rendered_messages = self._prepare_messages(messages, tools)

        def _generate() -> str:
            prompt = tokenizer.apply_chat_template(
                rendered_messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            encoded = tokenizer(prompt, return_tensors="pt")
            input_ids = encoded["input_ids"]
            attention_mask = encoded.get("attention_mask")
            if hasattr(local_model, "device"):
                device = local_model.device
                input_ids = input_ids.to(device)
                if attention_mask is not None:
                    attention_mask = attention_mask.to(device)
            outputs = local_model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=512,
                do_sample=False,
            )
            generated = outputs[0][input_ids.shape[-1] :]
            return tokenizer.decode(generated, skip_special_tokens=True).strip()

        output_text = await asyncio.to_thread(_generate)
        return self._to_openai_payload(output_text, tools)

    def _prepare_messages(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None,
    ) -> list[dict[str, str]]:
        rendered: list[dict[str, str]] = []
        tool_block = ""
        if tools:
            rendered_tools = json.dumps(tools, ensure_ascii=False)
            tool_block = (
                "\nYou may call tools by responding with JSON only in this exact format: "
                '{"tool_calls":[{"name":"tool_name","arguments":{}}]}.'
                "\nIf no tool is needed, respond with JSON only in this exact format: "
                '{"reply":"your reply"}.\nAvailable tools: ' + rendered_tools
            )

        for index, message in enumerate(messages):
            role_value = message.get("role")
            content_value = message.get("content")
            role = role_value if isinstance(role_value, str) else "user"
            content = (
                content_value
                if isinstance(content_value, str)
                else json.dumps(content_value, ensure_ascii=False)
            )
            if index == 0 and role == "system" and tool_block:
                content += tool_block
            rendered.append({"role": role, "content": content})
        return rendered

    def _to_openai_payload(
        self,
        output_text: str,
        tools: list[dict[str, object]] | None,
    ) -> dict[str, object]:
        if tools:
            envelope = self._parse_json_envelope(output_text)
            if isinstance(envelope, dict):
                raw_tool_calls = envelope.get("tool_calls")
                if isinstance(raw_tool_calls, list) and raw_tool_calls:
                    tool_calls: list[dict[str, object]] = []
                    for index, item in enumerate(raw_tool_calls, start=1):
                        if not isinstance(item, dict):
                            continue
                        name = item.get("name")
                        arguments = item.get("arguments")
                        if not isinstance(name, str) or not name.strip():
                            continue
                        normalized_arguments = (
                            arguments if isinstance(arguments, dict) else {}
                        )
                        tool_calls.append(
                            {
                                "id": f"local_call_{index}",
                                "type": "function",
                                "function": {
                                    "name": name.strip(),
                                    "arguments": json.dumps(
                                        normalized_arguments, ensure_ascii=False
                                    ),
                                },
                            }
                        )
                    if tool_calls:
                        return {
                            "choices": [
                                {
                                    "finish_reason": "tool_calls",
                                    "message": {
                                        "role": "assistant",
                                        "tool_calls": tool_calls,
                                    },
                                }
                            ]
                        }

                reply_value = envelope.get("reply")
                if isinstance(reply_value, str) and reply_value.strip():
                    return {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": reply_value.strip(),
                                },
                            }
                        ]
                    }

        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": output_text,
                    },
                }
            ]
        }

    @staticmethod
    def _parse_json_envelope(text: str) -> dict[str, object] | None:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start : end + 1]
        try:
            payload = json.loads(stripped)
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None
