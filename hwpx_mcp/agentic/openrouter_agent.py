from __future__ import annotations

import json
import os
from dataclasses import dataclass
from dataclasses import field
import re
from typing import Literal

import httpx

from .gateway import AgenticGateway
from .gateway import BackendServer
from .local_model import LOCAL_DEFAULT_MODEL
from .local_model import LOCAL_PROVIDER
from .local_model import LocalModelError
from .local_model import LocalModelManagerProtocol
from .local_model import LocalTransformersModelManager
from .models import JsonValue

CaseName = Literal[
    "windows_com_full",
    "cross_platform_hwpx",
    "template_workflow",
    "query_analyze_only",
    "no_document_context",
    "degraded_recovery",
]

IntentName = Literal[
    "status",
    "capabilities",
    "template",
    "open_document",
    "table",
    "field_form",
    "create",
    "insert_text",
    "save",
    "export_pdf",
    "search",
    "unknown",
]

SubagentName = Literal[
    "status_agent",
    "template_agent",
    "document_agent",
    "export_agent",
    "search_agent",
    "recovery_agent",
]

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_OAUTH_TOKEN_ENV = "OPENAI_OAUTH_TOKEN"
CODEX_OAUTH_TOKEN_ENV = "CODEX_OAUTH_TOKEN"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
AGENT_PROVIDER_ENV = "HWPX_AGENT_PROVIDER"
AGENT_MODEL_ENV = "HWPX_AGENT_MODEL"
CODEX_PROXY_URL_ENV = "HWPX_CODEX_PROXY_URL"
CODEX_PROXY_ACCESS_TOKEN_ENV = "HWPX_CODEX_PROXY_ACCESS_TOKEN"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
OPENROUTER_DEFAULT_MODEL = "openai/gpt-oss-120b"
CODEX_PROXY_DEFAULT_MODEL = "gpt-5"
CODEX_PROXY_DEFAULT_URL = "http://127.0.0.1:2455/v1/chat/completions"

OPENAI_PROVIDER = "openai"
OPENROUTER_PROVIDER = "openrouter"
CODEX_PROXY_PROVIDER = "codex-proxy"
SUPPORTED_PROVIDERS = {
    OPENAI_PROVIDER,
    OPENROUTER_PROVIDER,
    CODEX_PROXY_PROVIDER,
    LOCAL_PROVIDER,
}

DEFAULT_MODEL = OPENAI_DEFAULT_MODEL
DEFAULT_PROVIDER = OPENAI_PROVIDER


JsonObject = dict[str, JsonValue]
MessageRole = Literal["system", "user", "assistant", "tool"]


class AgentAuthError(RuntimeError):
    pass


class LlmRequestError(RuntimeError):
    def __init__(self, *, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class LocalModelNotReadyError(RuntimeError):
    pass


@dataclass(slots=True)
class ToolCall:
    tool_call_id: str
    name: str
    arguments: JsonObject


@dataclass(slots=True)
class ToolCallResult:
    tool_call_id: str
    name: str
    arguments: JsonObject
    result: object


@dataclass(slots=True)
class PlanStep:
    id: str
    title: str
    objective: str
    tool_hint: str | None = None


@dataclass(slots=True)
class ExecutionPlan:
    summary: str
    steps: list[PlanStep]
    raw_text: str = ""

    def to_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "steps": [
                {
                    "id": step.id,
                    "title": step.title,
                    "objective": step.objective,
                    "tool_hint": step.tool_hint,
                }
                for step in self.steps
            ],
        }


def _extract_quoted_text(message: str) -> str | None:
    match = re.search(r'"([^"]+)"', message)
    if match:
        return match.group(1).strip()
    match = re.search(r"'([^']+)'", message)
    if match:
        return match.group(1).strip()
    return None


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _has_table_keywords(lowered: str) -> bool:
    return _contains_any(
        lowered,
        ("table", "표", "테이블", "셀", "cell", "행"),
    )


def _has_field_keywords(lowered: str) -> bool:
    return _contains_any(
        lowered,
        ("field", "필드", "누름틀", "입력란"),
    )


def _has_template_keywords(lowered: str) -> bool:
    return _contains_any(
        lowered,
        ("template", "템플릿", "목록", "list", "search", "검색"),
    )


def _has_edit_keywords(lowered: str) -> bool:
    return _contains_any(
        lowered,
        ("open", "열", "불러", "수정", "편집", "변경", "update", "edit"),
    )


def _looks_like_document_target(message: str) -> bool:
    quoted = _extract_quoted_text(message)
    if isinstance(quoted, str) and quoted.lower().endswith((".hwp", ".hwpx")):
        return True
    lowered = message.lower()
    return _contains_any(lowered, (".hwp", ".hwpx", "기존 문서", "문서 수정"))


def _looks_like_search_request(lowered: str) -> bool:
    return _contains_any(lowered, ("find", "search", "찾기", "검색"))


def _parse_intent(message: str) -> IntentName:
    lowered = message.lower()
    if any(token in lowered for token in ("status", "ping", "상태", "헬스")):
        return "status"
    if any(
        token in lowered for token in ("capability", "capabilities", "지원", "가능")
    ):
        return "capabilities"
    if _looks_like_search_request(lowered):
        return "search"
    if _has_field_keywords(lowered):
        return "field_form"
    if _has_table_keywords(lowered):
        return "table"
    if "양식" in lowered and (
        _has_table_keywords(lowered) or _has_field_keywords(lowered)
    ):
        return "table" if _has_table_keywords(lowered) else "field_form"
    if "양식" in lowered and _has_edit_keywords(lowered):
        if _has_table_keywords(lowered):
            return "table"
        if _has_field_keywords(lowered):
            return "field_form"
    if _looks_like_document_target(message) and (
        _has_edit_keywords(lowered) or _extract_quoted_text(message) is not None
    ):
        return "open_document"
    if any(token in lowered for token in ("template", "템플릿")):
        return "template"
    if "양식" in lowered and _has_template_keywords(lowered):
        return "template"
    if any(token in lowered for token in ("export pdf", "pdf", "내보내기")):
        return "export_pdf"
    if any(token in lowered for token in ("save", "저장")):
        return "save"
    if _looks_like_search_request(lowered):
        return "search"
    if any(token in lowered for token in ("insert", "write", "작성", "추가", "입력")):
        return "insert_text"
    if any(
        token in lowered for token in ("create", "new", "문서 생성", "새 문서", "만들")
    ):
        return "create"
    return "unknown"


def _detect_case(message: str, tool_names: set[str]) -> CaseName:
    lowered = message.lower()
    has_windows = any(name.startswith("hwp_windows_") for name in tool_names)
    has_templates = "hwp_list_templates" in tool_names
    has_hwpx = "hwp_create_hwpx" in tool_names
    has_doc_ops = any(
        name in tool_names for name in ("hwp_create", "hwp_insert_text", "hwp_save")
    )
    has_xml_only = bool(tool_names) and all(
        ("xml" in name) or ("xpath" in name) or ("smart_patch" in name)
        for name in tool_names
    )

    if (
        (
            any(token in lowered for token in ("template", "템플릿"))
            or ("양식" in lowered and _has_template_keywords(lowered))
        )
        and not _has_table_keywords(lowered)
        and not _has_field_keywords(lowered)
        and has_templates
    ):
        return "template_workflow"
    if has_windows:
        return "windows_com_full"
    if has_xml_only:
        return "query_analyze_only"
    if has_hwpx:
        return "cross_platform_hwpx"
    if has_doc_ops:
        return "no_document_context"
    return "degraded_recovery"


def _route_subagent(intent: IntentName, case: CaseName) -> SubagentName:
    if intent in ("status", "capabilities"):
        return "status_agent"
    if intent == "template" or case == "template_workflow":
        return "template_agent"
    if intent == "export_pdf":
        return "export_agent"
    if intent == "search":
        return "search_agent"
    if intent in (
        "create",
        "insert_text",
        "save",
        "open_document",
        "table",
        "field_form",
    ):
        return "document_agent"
    return "recovery_agent"


def _subagent_tool_allowlist(subagent: SubagentName, intent: IntentName) -> list[str]:
    if subagent == "status_agent":
        if intent == "capabilities":
            return [
                "hwp_capabilities",
                "hwp_get_capabilities",
                "hwp_platform_info",
            ]
        return ["hwp_ping", "hwp_platform_info", "hwp_capabilities"]
    if subagent == "template_agent":
        return [
            "hwp_list_templates",
            "hwp_search_template",
            "hwp_create_from_template",
        ]
    if subagent == "document_agent":
        if intent == "open_document":
            return [
                "hwp_platform_info",
                "hwp_open",
                "hwp_insert_text",
                "hwp_windows_insert_text",
                "hwp_save",
                "hwp_save_document",
            ]
        if intent == "table":
            return [
                "hwp_platform_info",
                "hwp_create_table",
                "hwp_set_cell_text",
                "hwp_save",
                "hwp_save_document",
            ]
        if intent == "field_form":
            return [
                "hwp_platform_info",
                "hwp_create_field",
                "hwp_put_field_text",
                "hwp_save",
                "hwp_save_document",
            ]
        return [
            "hwp_platform_info",
            "hwp_create_hwpx",
            "hwp_create",
            "hwp_insert_text",
            "hwp_windows_insert_text",
            "hwp_save",
            "hwp_save_document",
        ]
    if subagent == "export_agent":
        return ["hwp_export_pdf", "hwp_save_as"]
    if subagent == "search_agent":
        return ["hwp_find", "hwp_search_text"]
    return []


def _base_system_prompt() -> str:
    return (
        "You are HWPX MCP Assistant. You help users create and edit HWP/HWPX documents.\n"
        "You have access to tools for document operations.\n"
        "When you need to perform an action, call the appropriate tool.\n"
        "Always respond in the same language as the user's message.\n"
        "When showing tool results, explain them clearly and concisely.\n"
    )


def _planner_system_prompt() -> str:
    return (
        "You are the planning phase of HWPX MCP Assistant.\n"
        "Create a short execution plan before any tool can be used.\n"
        "Do not call tools. Do not mention tool call syntax.\n"
        "Return JSON only with this shape:\n"
        '{"summary": "...", "steps": ['
        '{"id": "step-1", "title": "...", "objective": "...", "tool_hint": "optional_tool_name_or_null"}'
        "]}.\n"
        "Keep steps concrete, ordered, and minimal.\n"
        "Use the same language as the user.\n"
    )


def _subagent_system_prompt(subagent: SubagentName) -> str:
    if subagent == "status_agent":
        return (
            "Focus: backend status and capabilities. Use status/capabilities tools when needed.\n"
            "Keep replies short.\n"
        )
    if subagent == "template_agent":
        return (
            "Focus: templates. Prefer listing/searching templates using available tools.\n"
            "If the user asks for a specific template, search by keywords and summarize results.\n"
        )
    if subagent == "document_agent":
        return (
            "Focus: creating or editing documents. Use open/create/table/field/insert/save tools as needed.\n"
            "If the user wants to edit an existing file, check document state first and open the target document before writing.\n"
            "If opening the target fails, ask for a valid document path instead of creating a new document automatically.\n"
            "For tables, prefer table tools over plain text insertion. For form fields, prefer field tools over plain text insertion.\n"
            "If the user provides text in quotes, treat it as the exact content to insert or use.\n"
            "When multiple tool calls are needed, do them step-by-step.\n"
        )
    if subagent == "export_agent":
        return (
            "Focus: exporting documents (e.g., PDF). Use export tools.\n"
            "If an output path is required, choose a reasonable default and report it.\n"
        )
    if subagent == "search_agent":
        return (
            "Focus: searching within the current document. Use search tools.\n"
            "If the keyword is missing or unclear, ask the user for the exact keyword.\n"
        )
    return (
        "If you cannot route confidently, ask one precise clarifying question.\n"
        "Do not hallucinate tool results.\n"
    )


def _tool_record_to_openai_tool(record: object) -> dict[str, object]:
    name = getattr(record, "name", "")
    description = getattr(record, "description", "")
    schema = getattr(record, "input_schema", None)
    parameters: dict[str, object]
    if isinstance(schema, dict) and schema:
        parameters = schema
    else:
        parameters = {"type": "object", "properties": {}}

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def _format_allowlist(allowlist: list[str]) -> str:
    if not allowlist:
        return "none"
    return ", ".join(allowlist)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _extract_json_object(text: str) -> str:
    stripped = _strip_json_fence(text)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def _coerce_plan_step(raw: object, index: int) -> PlanStep | None:
    if not isinstance(raw, dict):
        return None

    title_value = raw.get("title")
    objective_value = raw.get("objective")
    if not isinstance(title_value, str) or not title_value.strip():
        return None

    title = title_value.strip()
    objective = (
        objective_value.strip()
        if isinstance(objective_value, str) and objective_value.strip()
        else title
    )
    tool_hint = raw.get("tool_hint")
    normalized_tool_hint = (
        tool_hint.strip() if isinstance(tool_hint, str) and tool_hint.strip() else None
    )
    step_id = raw.get("id")
    normalized_id = (
        step_id.strip()
        if isinstance(step_id, str) and step_id.strip()
        else f"step-{index}"
    )
    return PlanStep(
        id=normalized_id,
        title=title,
        objective=objective,
        tool_hint=normalized_tool_hint,
    )


def _fallback_plan(
    *,
    message: str,
    intent: IntentName,
    subagent: SubagentName,
    allowlist: list[str],
) -> ExecutionPlan:
    summary = f"요청을 처리하기 위한 실행 계획을 준비합니다: {message.strip()}"
    steps: list[PlanStep]

    if subagent == "status_agent":
        steps = [
            PlanStep(
                id="step-1",
                title="상태 확인",
                objective="백엔드 상태 또는 지원 기능을 확인합니다.",
                tool_hint=allowlist[0] if allowlist else None,
            )
        ]
    elif subagent == "template_agent":
        steps = [
            PlanStep(
                id="step-1",
                title="템플릿 확인",
                objective="요청에 맞는 템플릿 목록이나 검색 결과를 확인합니다.",
                tool_hint=allowlist[0] if allowlist else None,
            )
        ]
    elif subagent == "document_agent":
        steps = [
            PlanStep(
                id="step-1",
                title="문서 작업 준비",
                objective="요청된 문서 작업에 필요한 생성 또는 편집 단계를 정리합니다.",
                tool_hint=allowlist[0] if allowlist else None,
            ),
            PlanStep(
                id="step-2",
                title="문서 반영",
                objective="정리한 계획에 따라 실제 문서 내용을 반영합니다.",
                tool_hint=allowlist[1]
                if len(allowlist) > 1
                else allowlist[0]
                if allowlist
                else None,
            ),
        ]
        if intent == "save":
            steps.append(
                PlanStep(
                    id="step-3",
                    title="문서 저장",
                    objective="변경된 문서를 지정된 형식으로 저장합니다.",
                    tool_hint=allowlist[-1] if allowlist else None,
                )
            )
    elif subagent == "export_agent":
        steps = [
            PlanStep(
                id="step-1",
                title="내보내기 준비",
                objective="요청된 형식으로 문서를 내보낼 수 있도록 출력 경로와 방식을 정합니다.",
                tool_hint=allowlist[0] if allowlist else None,
            )
        ]
    elif subagent == "search_agent":
        steps = [
            PlanStep(
                id="step-1",
                title="검색 실행",
                objective="문서에서 필요한 키워드나 텍스트를 찾습니다.",
                tool_hint=allowlist[0] if allowlist else None,
            )
        ]
    else:
        steps = [
            PlanStep(
                id="step-1",
                title="요청 해석",
                objective="현재 요청을 처리할 수 있는 방법을 확인합니다.",
                tool_hint=allowlist[0] if allowlist else None,
            )
        ]

    return ExecutionPlan(summary=summary, steps=steps, raw_text="")


def _parse_plan_response(
    *,
    raw_text: str,
    message: str,
    intent: IntentName,
    subagent: SubagentName,
    allowlist: list[str],
) -> ExecutionPlan:
    fallback = _fallback_plan(
        message=message,
        intent=intent,
        subagent=subagent,
        allowlist=allowlist,
    )
    if not raw_text.strip():
        return fallback

    candidate = _extract_json_object(raw_text)
    try:
        payload = json.loads(candidate)
    except ValueError:
        fallback.raw_text = raw_text
        return fallback

    if not isinstance(payload, dict):
        fallback.raw_text = raw_text
        return fallback

    summary_value = payload.get("summary")
    raw_steps = payload.get("steps")
    steps: list[PlanStep] = []
    if isinstance(raw_steps, list):
        for index, item in enumerate(raw_steps, start=1):
            step = _coerce_plan_step(item, index)
            if step is not None:
                steps.append(step)

    if not steps:
        fallback.raw_text = raw_text
        return fallback

    summary = (
        summary_value.strip()
        if isinstance(summary_value, str) and summary_value.strip()
        else fallback.summary
    )
    return ExecutionPlan(summary=summary, steps=steps, raw_text=raw_text)


def _render_plan_for_execution(plan: ExecutionPlan) -> str:
    rendered_steps = []
    for step in plan.steps:
        line = f"- {step.id}: {step.title} | objective={step.objective}"
        if step.tool_hint:
            line += f" | tool_hint={step.tool_hint}"
        rendered_steps.append(line)
    body = "\n".join(rendered_steps) if rendered_steps else "- no steps"
    return f"Execution plan summary: {plan.summary}\n{body}"


class OpenRouterClient:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key
        self._runtime_openai_api_key = ""
        self._runtime_openai_oauth_token = ""
        self._runtime_codex_oauth_token = ""
        self._runtime_openrouter_api_key = ""
        self._runtime_codex_proxy_access_token = ""

    @staticmethod
    def normalize_provider(value: str | None) -> str:
        normalized = value.strip().lower() if isinstance(value, str) else ""
        if normalized in SUPPORTED_PROVIDERS:
            return normalized
        return DEFAULT_PROVIDER

    @staticmethod
    def _normalize_token(value: str | None, *, trim_bearer: bool = False) -> str:
        normalized = value.strip() if isinstance(value, str) else ""
        if trim_bearer and normalized.lower().startswith("bearer "):
            return normalized[7:].strip()
        return normalized

    def set_runtime_auth(
        self,
        *,
        openai_api_key: str | None = None,
        openai_oauth_token: str | None = None,
        codex_oauth_token: str | None = None,
        openrouter_api_key: str | None = None,
        codex_proxy_access_token: str | None = None,
    ) -> None:
        if openai_api_key is not None:
            self._runtime_openai_api_key = self._normalize_token(openai_api_key)

        if openai_oauth_token is not None:
            self._runtime_openai_oauth_token = self._normalize_token(
                openai_oauth_token,
                trim_bearer=True,
            )

        if codex_oauth_token is not None:
            self._runtime_codex_oauth_token = self._normalize_token(
                codex_oauth_token,
                trim_bearer=True,
            )

        if openrouter_api_key is not None:
            self._runtime_openrouter_api_key = self._normalize_token(openrouter_api_key)

        if codex_proxy_access_token is not None:
            self._runtime_codex_proxy_access_token = self._normalize_token(
                codex_proxy_access_token,
                trim_bearer=True,
            )

    def _auth_candidates(self, provider: str) -> list[tuple[str, str]]:
        normalized_provider = self.normalize_provider(provider)

        if normalized_provider == LOCAL_PROVIDER:
            return [("local-transformers", "")]

        if normalized_provider == CODEX_PROXY_PROVIDER:
            codex_proxy_access_token = (
                self._runtime_codex_proxy_access_token
                or os.getenv(CODEX_PROXY_ACCESS_TOKEN_ENV, "").strip()
            )
            if codex_proxy_access_token.lower().startswith("bearer "):
                codex_proxy_access_token = codex_proxy_access_token[7:].strip()
            if codex_proxy_access_token:
                return [("codex-proxy-token", codex_proxy_access_token)]

            raise AgentAuthError(f"{CODEX_PROXY_ACCESS_TOKEN_ENV} is not set")

        if normalized_provider == OPENROUTER_PROVIDER:
            openrouter_api_key = (
                self._runtime_openrouter_api_key
                or os.getenv(OPENROUTER_API_KEY_ENV, "").strip()
            )
            if openrouter_api_key:
                return [("openrouter-api-key", openrouter_api_key)]

            raise AgentAuthError(f"{OPENROUTER_API_KEY_ENV} is not set")

        candidates: list[tuple[str, str]] = []

        oauth_token = (
            self._runtime_openai_oauth_token
            or os.getenv(OPENAI_OAUTH_TOKEN_ENV, "").strip()
        )
        if oauth_token.lower().startswith("bearer "):
            oauth_token = oauth_token[7:].strip()
        if oauth_token:
            candidates.append(("openai-oauth", oauth_token))

        codex_oauth_token = (
            self._runtime_codex_oauth_token
            or os.getenv(CODEX_OAUTH_TOKEN_ENV, "").strip()
        )
        if codex_oauth_token.lower().startswith("bearer "):
            codex_oauth_token = codex_oauth_token[7:].strip()
        if codex_oauth_token:
            candidates.append(("codex-oauth", codex_oauth_token))

        openai_api_key = (
            self._runtime_openai_api_key
            or (self._api_key or os.getenv(OPENAI_API_KEY_ENV, "")).strip()
        )
        if openai_api_key:
            candidates.append(("openai-api-key", openai_api_key))

        unique_candidates: list[tuple[str, str]] = []
        seen_tokens: set[str] = set()
        for mode, token in candidates:
            if token in seen_tokens:
                continue
            seen_tokens.add(token)
            unique_candidates.append((mode, token))

        if unique_candidates:
            return unique_candidates

        raise AgentAuthError(
            f"{OPENAI_OAUTH_TOKEN_ENV} or {CODEX_OAUTH_TOKEN_ENV} or {OPENAI_API_KEY_ENV} is not set"
        )

    def auth_status(self, provider: str) -> dict[str, object]:
        normalized_provider = self.normalize_provider(provider)
        if normalized_provider == LOCAL_PROVIDER:
            accepted_env: list[str] = []
        elif normalized_provider == CODEX_PROXY_PROVIDER:
            accepted_env = [CODEX_PROXY_ACCESS_TOKEN_ENV]
        elif normalized_provider == OPENROUTER_PROVIDER:
            accepted_env = [OPENROUTER_API_KEY_ENV]
        else:
            accepted_env = [
                OPENAI_OAUTH_TOKEN_ENV,
                CODEX_OAUTH_TOKEN_ENV,
                OPENAI_API_KEY_ENV,
            ]

        try:
            candidates = self._auth_candidates(normalized_provider)
        except AgentAuthError as error:
            return {
                "configured": False,
                "mode": "none",
                "detail": str(error),
                "available_modes": [],
                "accepted_env": accepted_env,
            }

        modes = [mode for mode, _token in candidates]
        return {
            "configured": True,
            "mode": modes[0],
            "available_modes": modes,
            "accepted_env": accepted_env,
        }

    def _resolve_auth(self, provider: str) -> tuple[str, str]:
        return self._auth_candidates(provider)[0]

    @staticmethod
    def _is_insufficient_quota(status_code: int, response_text: str) -> bool:
        if status_code != 429:
            return False

        lowered = response_text.lower()
        if "insufficient_quota" in lowered:
            return True

        try:
            payload = json.loads(response_text)
        except (TypeError, ValueError):
            return False

        if not isinstance(payload, dict):
            return False

        error = payload.get("error")
        if not isinstance(error, dict):
            return False

        error_type = error.get("type")
        return isinstance(error_type, str) and error_type == "insufficient_quota"

    @staticmethod
    def _parse_error_fields(response_text: str) -> tuple[str, str]:
        try:
            payload = json.loads(response_text)
        except (TypeError, ValueError):
            return "", ""

        if not isinstance(payload, dict):
            return "", ""

        error = payload.get("error")
        if not isinstance(error, dict):
            return "", ""

        error_type = error.get("type")
        error_code = error.get("code")

        normalized_type = error_type if isinstance(error_type, str) else ""
        normalized_code = error_code if isinstance(error_code, str) else ""
        return normalized_type, normalized_code

    @classmethod
    def _can_try_next_auth(cls, *, status_code: int, response_text: str) -> bool:
        if status_code == 401:
            return True

        error_type, error_code = cls._parse_error_fields(response_text)

        if status_code == 403:
            auth_like_markers = {
                "invalid_api_key",
                "invalid_authentication",
                "authentication_error",
                "insufficient_permissions",
            }
            return error_type in auth_like_markers or error_code in auth_like_markers

        if status_code == 429 and cls._is_insufficient_quota(
            status_code, response_text
        ):
            return True

        return False

    @classmethod
    def _append_quota_hint(
        cls,
        *,
        message: str,
        auth_mode: str,
        status_code: int,
        response_text: str,
    ) -> str:
        if auth_mode not in ("openai-oauth", "codex-oauth"):
            return message
        if not cls._is_insufficient_quota(status_code, response_text):
            return message
        return (
            f"{message} | quota_hint: OAuth token has no API quota. "
            f"Configure {OPENAI_API_KEY_ENV} with API billing or use another token."
        )

    async def _post_chat_completion(
        self,
        *,
        target_url: str,
        headers: dict[str, str],
        body: dict[str, object],
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=60.0) as client:
            return await client.post(target_url, headers=headers, json=body)

    @staticmethod
    def _resolve_openai_model(model: str) -> str:
        candidate = model.strip()
        if candidate and "/" not in candidate:
            return candidate

        override = os.getenv("OPENAI_MODEL", "").strip()
        if override:
            return override

        return OPENAI_DEFAULT_MODEL

    @staticmethod
    def _resolve_openrouter_model(model: str) -> str:
        candidate = model.strip()
        if candidate:
            return candidate

        override = os.getenv("OPENROUTER_MODEL", "").strip()
        if override:
            return override

        return OPENROUTER_DEFAULT_MODEL

    @staticmethod
    def _resolve_codex_proxy_model(model: str) -> str:
        candidate = model.strip()
        if candidate:
            return candidate

        return CODEX_PROXY_DEFAULT_MODEL

    @staticmethod
    def _resolve_codex_proxy_url(proxy_url: str | None) -> str:
        candidate = proxy_url.strip() if isinstance(proxy_url, str) else ""
        if not candidate:
            candidate = os.getenv(CODEX_PROXY_URL_ENV, "").strip()
        if not candidate:
            candidate = CODEX_PROXY_DEFAULT_URL

        normalized = candidate.rstrip("/")
        if normalized.lower().endswith("/chat/completions"):
            return normalized
        if normalized.lower().endswith("/v1"):
            return f"{normalized}/chat/completions"
        return f"{normalized}/chat/completions"

    @classmethod
    def _resolve_model(cls, provider: str, model: str) -> str:
        normalized_provider = cls.normalize_provider(provider)
        if normalized_provider == LOCAL_PROVIDER:
            candidate = model.strip()
            return candidate or LOCAL_DEFAULT_MODEL
        if normalized_provider == CODEX_PROXY_PROVIDER:
            return cls._resolve_codex_proxy_model(model)
        if normalized_provider == OPENROUTER_PROVIDER:
            return cls._resolve_openrouter_model(model)
        return cls._resolve_openai_model(model)

    @classmethod
    def _target_url_for_provider(
        cls, provider: str, proxy_url: str | None = None
    ) -> str:
        normalized_provider = cls.normalize_provider(provider)
        if normalized_provider == LOCAL_PROVIDER:
            return "local://transformers"
        if normalized_provider == CODEX_PROXY_PROVIDER:
            return cls._resolve_codex_proxy_url(proxy_url)
        if normalized_provider == OPENROUTER_PROVIDER:
            return OPENROUTER_URL
        return OPENAI_URL

    async def chat_completions(
        self,
        *,
        model: str,
        provider: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None,
        tool_choice: str | None,
        proxy_url: str | None = None,
    ) -> dict[str, object]:
        normalized_provider = self.normalize_provider(provider)
        auth_candidates = self._auth_candidates(normalized_provider)
        attempted_modes: list[str] = []

        body: dict[str, object]
        body = {
            "model": self._resolve_model(normalized_provider, model),
            "messages": messages,
            "stream": False,
        }
        target_url = self._target_url_for_provider(normalized_provider, proxy_url)

        if tools:
            body["tools"] = tools
            body["tool_choice"] = tool_choice or "auto"

        total_candidates = len(auth_candidates)
        for index, (auth_mode, auth_token) in enumerate(auth_candidates):
            attempted_modes.append(auth_mode)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            }

            if normalized_provider == OPENROUTER_PROVIDER:
                headers["X-Title"] = "HWPX MCP"
            try:
                response = await self._post_chat_completion(
                    target_url=target_url,
                    headers=headers,
                    body=body,
                )
            except httpx.HTTPError as error:
                raise LlmRequestError(
                    status_code=502,
                    message=f"llm_network_error[{auth_mode}]: {error}",
                ) from error

            if response.status_code >= 400:
                message = f"llm_error[{auth_mode}]: {response.status_code}: {response.text[:300]}"
                message = self._append_quota_hint(
                    message=message,
                    auth_mode=auth_mode,
                    status_code=response.status_code,
                    response_text=response.text,
                )

                if index + 1 < total_candidates and self._can_try_next_auth(
                    status_code=response.status_code,
                    response_text=response.text,
                ):
                    continue

                raise LlmRequestError(
                    status_code=response.status_code,
                    message=f"{message} | attempted_auth={','.join(attempted_modes)}",
                )

            try:
                return response.json()
            except ValueError as error:
                raise LlmRequestError(
                    status_code=502,
                    message=f"llm_invalid_json[{auth_mode}]: {response.text[:300]}",
                ) from error

        raise LlmRequestError(
            status_code=500,
            message="llm_error[unknown]: no_auth_candidate_succeeded",
        )


@dataclass(slots=True)
class OpenRouterToolAgent:
    backend_server: BackendServer
    client: OpenRouterClient = field(default_factory=OpenRouterClient)
    local_model_manager: LocalModelManagerProtocol = field(
        default_factory=LocalTransformersModelManager
    )
    model: str = ""
    provider: str = DEFAULT_PROVIDER
    codex_proxy_url: str = ""
    max_rounds: int = 8
    _gateway: AgenticGateway = field(init=False, repr=False)

    def __post_init__(self) -> None:
        configured_provider = self.provider
        env_provider = os.getenv(AGENT_PROVIDER_ENV, "").strip()
        if env_provider:
            configured_provider = env_provider

        configured_model = self.model
        env_model = os.getenv(AGENT_MODEL_ENV, "").strip()
        if env_model:
            configured_model = env_model

        configured_codex_proxy_url = self.codex_proxy_url
        env_codex_proxy_url = os.getenv(CODEX_PROXY_URL_ENV, "").strip()
        if env_codex_proxy_url:
            configured_codex_proxy_url = env_codex_proxy_url

        self.provider = self.client.normalize_provider(configured_provider)
        self.model = self._normalize_model_for_provider(
            self.provider,
            configured_model,
        )
        self.codex_proxy_url = self._normalize_codex_proxy_url(
            self.provider,
            configured_codex_proxy_url,
        )
        self._gateway = AgenticGateway(self.backend_server)

    @classmethod
    def _normalize_model_for_provider(cls, provider: str, model: str | None) -> str:
        candidate = model.strip() if isinstance(model, str) else ""
        if provider == LOCAL_PROVIDER:
            return candidate or LOCAL_DEFAULT_MODEL
        if provider == CODEX_PROXY_PROVIDER:
            return OpenRouterClient._resolve_codex_proxy_model(candidate)
        if provider == OPENROUTER_PROVIDER:
            return OpenRouterClient._resolve_openrouter_model(candidate)
        return OpenRouterClient._resolve_openai_model(candidate)

    @staticmethod
    def _normalize_codex_proxy_url(provider: str, proxy_url: str | None) -> str:
        if provider != CODEX_PROXY_PROVIDER and not proxy_url:
            return ""
        return OpenRouterClient._resolve_codex_proxy_url(proxy_url)

    def runtime_config(self) -> dict[str, str]:
        runtime: dict[str, str] = {
            "provider": self.provider,
            "model": self.model,
        }
        if self.provider == CODEX_PROXY_PROVIDER:
            runtime["proxy_url"] = self.codex_proxy_url
        return runtime

    def local_model_status(self) -> dict[str, object]:
        return self.local_model_manager.status().to_payload()

    async def download_local_model(self, *, force: bool = False) -> dict[str, object]:
        return await self.local_model_manager.ensure_downloaded(force=force)

    def _effective_provider_and_model(self) -> tuple[str, str, bool]:
        if self.provider == LOCAL_PROVIDER:
            return LOCAL_PROVIDER, self.model or LOCAL_DEFAULT_MODEL, False

        remote_auth = self.client.auth_status(self.provider)
        if remote_auth.get("configured") is True:
            return self.provider, self.model, False

        local_status = self.local_model_manager.status().to_payload()
        if local_status.get("ready") is True:
            return LOCAL_PROVIDER, self.local_model_manager.model_id, True

        return self.provider, self.model, False

    def set_runtime_config(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        proxy_url: str | None = None,
    ) -> dict[str, str]:
        next_provider = self.provider
        if provider is not None:
            next_provider = self.client.normalize_provider(provider)

        next_model = self.model
        if model is not None or provider is not None:
            next_model = self._normalize_model_for_provider(next_provider, model)

        next_codex_proxy_url = self.codex_proxy_url
        if next_provider == CODEX_PROXY_PROVIDER:
            if proxy_url is not None or provider is not None:
                next_codex_proxy_url = self._normalize_codex_proxy_url(
                    next_provider,
                    proxy_url if proxy_url is not None else self.codex_proxy_url,
                )
        else:
            next_codex_proxy_url = ""

        self.provider = next_provider
        self.model = next_model
        self.codex_proxy_url = next_codex_proxy_url
        return self.runtime_config()

    async def _build_plan(
        self,
        *,
        message: str,
        intent: IntentName,
        case: CaseName,
        subagent: SubagentName,
        allowlist: list[str],
        provider: str,
        model: str,
    ) -> ExecutionPlan:
        planner_messages: list[dict[str, object]] = [
            {"role": "system", "content": _planner_system_prompt()},
            {
                "role": "user",
                "content": (
                    f"User request: {message}\n"
                    f"Detected intent: {intent}\n"
                    f"Detected case: {case}\n"
                    f"Selected subagent: {subagent}\n"
                    f"Available tools for later execution: {_format_allowlist(allowlist)}"
                ),
            },
        ]
        response = await self._chat_completions(
            model=model,
            provider=provider,
            messages=planner_messages,
            tools=None,
            tool_choice=None,
        )
        choice = _first_choice(response)
        assistant_message = choice.get("message")
        if not isinstance(assistant_message, dict):
            return _fallback_plan(
                message=message,
                intent=intent,
                subagent=subagent,
                allowlist=allowlist,
            )

        content = assistant_message.get("content")
        raw_text = content if isinstance(content, str) else ""
        return _parse_plan_response(
            raw_text=raw_text,
            message=message,
            intent=intent,
            subagent=subagent,
            allowlist=allowlist,
        )

    async def _chat_completions(
        self,
        *,
        model: str,
        provider: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None,
        tool_choice: str | None,
    ) -> dict[str, object]:
        if provider == LOCAL_PROVIDER:
            try:
                return await self.local_model_manager.chat_completions(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                )
            except LocalModelError as error:
                raise LocalModelNotReadyError(str(error)) from error

        return await self.client.chat_completions(
            model=model,
            provider=provider,
            proxy_url=self.codex_proxy_url,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )

    async def run(self, *, message: str, session_id: str = "") -> dict[str, object]:
        await self._gateway.refresh_registry()
        tool_names = {record.name for record in self._gateway.registry}

        intent = _parse_intent(message)
        case = _detect_case(message, tool_names)
        subagent = _route_subagent(intent, case)

        allowlist = _subagent_tool_allowlist(subagent, intent)
        records_by_name = {record.name: record for record in self._gateway.registry}
        tool_defs: list[dict[str, object]] = []
        for name in allowlist:
            record = records_by_name.get(name)
            if record is None:
                continue
            tool_defs.append(_tool_record_to_openai_tool(record))

        request_provider, request_model, used_local_fallback = (
            self._effective_provider_and_model()
        )

        plan = await self._build_plan(
            message=message,
            intent=intent,
            case=case,
            subagent=subagent,
            allowlist=allowlist,
            provider=request_provider,
            model=request_model,
        )

        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": _base_system_prompt()
                + "\n"
                + _subagent_system_prompt(subagent),
            },
            {
                "role": "assistant",
                "content": _render_plan_for_execution(plan),
            },
            {"role": "user", "content": message},
        ]

        tool_call_results: list[ToolCallResult] = []
        last_tool_name: str | None = None
        last_arguments: JsonObject = {}

        for _round in range(self.max_rounds):
            response = await self._chat_completions(
                model=request_model,
                provider=request_provider,
                messages=messages,
                tools=tool_defs if tool_defs else None,
                tool_choice="auto" if tool_defs else None,
            )
            choice = _first_choice(response)
            assistant_message = choice.get("message")
            if not isinstance(assistant_message, dict):
                return {
                    "success": False,
                    "case": case,
                    "intent": intent,
                    "subagent": subagent,
                    "plan": plan.to_payload(),
                    "reply": "모델 응답을 파싱하지 못했습니다.",
                    "error": "invalid_model_response",
                }

            finish_reason = choice.get("finish_reason")
            tool_calls = _extract_tool_calls(assistant_message)
            if finish_reason == "tool_calls" and tool_calls:
                messages.append(assistant_message)
                for call in tool_calls:
                    last_tool_name = call.name
                    last_arguments = call.arguments
                    result = await self._call_tool_by_name(call.name, call.arguments)
                    tool_call_results.append(
                        ToolCallResult(
                            tool_call_id=call.tool_call_id,
                            name=call.name,
                            arguments=call.arguments,
                            result=result,
                        )
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.tool_call_id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                continue

            content = assistant_message.get("content")
            reply = (
                content
                if isinstance(content, str) and content.strip()
                else "(no response)"
            )
            return {
                "success": True,
                "case": case,
                "intent": intent,
                "subagent": subagent,
                "plan": plan.to_payload(),
                "used_local_fallback": used_local_fallback,
                "selected_tool": last_tool_name,
                "arguments": last_arguments,
                "reply": reply,
                "result": [
                    {
                        "tool_call_id": item.tool_call_id,
                        "name": item.name,
                        "arguments": item.arguments,
                        "result": item.result,
                    }
                    for item in tool_call_results
                ],
                "error": None,
                "session_id": session_id,
            }

        return {
            "success": False,
            "case": case,
            "intent": intent,
            "subagent": subagent,
            "plan": plan.to_payload(),
            "used_local_fallback": used_local_fallback,
            "reply": "도구 호출 루프가 너무 오래 지속되었습니다.",
            "error": "max_rounds_exceeded",
        }

    def auth_status(self) -> dict[str, object]:
        remote_auth = self.client.auth_status(self.provider)
        local_status = self.local_model_status()

        if self.provider == LOCAL_PROVIDER:
            return {
                "configured": local_status.get("ready") is True,
                "mode": "local-transformers"
                if local_status.get("ready") is True
                else "none",
                "available_modes": ["local-transformers"]
                if local_status.get("ready") is True
                else [],
                "accepted_env": [],
                "local_fallback": local_status,
                "detail": local_status.get("detail", ""),
            }

        if remote_auth.get("configured") is True:
            return remote_auth

        if local_status.get("ready") is True:
            return {
                "configured": True,
                "mode": "local-transformers",
                "available_modes": ["local-transformers"],
                "accepted_env": remote_auth.get("accepted_env", []),
                "detail": remote_auth.get("detail", ""),
            }

        return remote_auth

    def set_runtime_auth(
        self,
        *,
        openai_api_key: str | None = None,
        openai_oauth_token: str | None = None,
        codex_oauth_token: str | None = None,
        openrouter_api_key: str | None = None,
        codex_proxy_access_token: str | None = None,
    ) -> None:
        self.client.set_runtime_auth(
            openai_api_key=openai_api_key,
            openai_oauth_token=openai_oauth_token,
            codex_oauth_token=codex_oauth_token,
            openrouter_api_key=openrouter_api_key,
            codex_proxy_access_token=codex_proxy_access_token,
        )

    async def _call_tool_by_name(self, name: str, arguments: JsonObject) -> object:
        for record in self._gateway.registry:
            if record.name == name:
                response = await self._gateway.tool_call(record.tool_id, arguments)
                if response.get("success") is True and "result" in response:
                    return response["result"]
                return response
        return {"success": False, "message": f"tool_not_found: {name}"}


def _first_choice(payload: dict[str, object]) -> dict[str, object]:
    raw_choices = payload.get("choices")
    if isinstance(raw_choices, list) and raw_choices:
        first = raw_choices[0]
        if isinstance(first, dict):
            return first
    return {}


def _extract_tool_calls(message: dict[str, object]) -> list[ToolCall]:
    raw = message.get("tool_calls")
    if not isinstance(raw, list):
        return []

    calls: list[ToolCall] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tool_call_id = item.get("id")
        function = item.get("function")
        if not isinstance(tool_call_id, str) or not isinstance(function, dict):
            continue
        name = function.get("name")
        raw_args = function.get("arguments")
        if not isinstance(name, str):
            continue

        arguments: JsonObject = {}
        if isinstance(raw_args, str) and raw_args.strip():
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, dict):
                    arguments = parsed
            except json.JSONDecodeError:
                arguments = {}
        elif isinstance(raw_args, dict):
            arguments = raw_args

        calls.append(
            ToolCall(
                tool_call_id=tool_call_id,
                name=name,
                arguments=arguments,
            )
        )
    return calls
