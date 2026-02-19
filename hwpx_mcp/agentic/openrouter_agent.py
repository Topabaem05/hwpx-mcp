from __future__ import annotations

import json
import os
from dataclasses import dataclass
from dataclasses import field
from typing import Literal

import httpx

from .gateway import AgenticGateway
from .gateway import BackendServer
from .models import JsonValue
from .tool_only_agent import _detect_case
from .tool_only_agent import _parse_intent
from .tool_only_agent import CaseName
from .tool_only_agent import IntentName
from .tool_only_agent import SubagentName

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"

DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_PROVIDER = "cerebras/fp16"


JsonObject = dict[str, JsonValue]
MessageRole = Literal["system", "user", "assistant", "tool"]


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


def _route_subagent(intent: IntentName, case: CaseName) -> SubagentName:
    if intent in ("status", "capabilities"):
        return "status_agent"
    if intent == "template" or case == "template_workflow":
        return "template_agent"
    if intent == "export_pdf":
        return "export_agent"
    if intent == "search":
        return "search_agent"
    if intent in ("create", "insert_text", "save"):
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
        return ["hwp_list_templates", "hwp_search_template"]
    if subagent == "document_agent":
        return [
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
            "Focus: creating or editing documents. Use create/insert/save tools as needed.\n"
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


class OpenRouterClient:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    def _resolve_api_key(self) -> str:
        api_key = (self._api_key or os.getenv(OPENROUTER_API_KEY_ENV, "")).strip()
        if not api_key:
            raise RuntimeError(f"{OPENROUTER_API_KEY_ENV} is not set")
        return api_key

    async def chat_completions(
        self,
        *,
        model: str,
        provider: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None,
        tool_choice: str | None,
    ) -> dict[str, object]:
        api_key = self._resolve_api_key()

        body: dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "provider": {
                "order": [provider],
                "quantizations": [
                    provider.split("/", 1)[1] if "/" in provider else "fp16"
                ],
            },
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = tool_choice or "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/Topabaem05/hwpx-mcp",
            "X-Title": "HWPX MCP",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=body)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"openrouter_error: {response.status_code}: {response.text[:300]}"
                )
            return response.json()


@dataclass(slots=True)
class OpenRouterToolAgent:
    backend_server: BackendServer
    client: OpenRouterClient = field(default_factory=OpenRouterClient)
    model: str = DEFAULT_MODEL
    provider: str = DEFAULT_PROVIDER
    max_rounds: int = 8
    _gateway: AgenticGateway = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._gateway = AgenticGateway(self.backend_server)

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

        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": _base_system_prompt()
                + "\n"
                + _subagent_system_prompt(subagent),
            },
            {"role": "user", "content": message},
        ]

        tool_call_results: list[ToolCallResult] = []
        last_tool_name: str | None = None
        last_arguments: JsonObject = {}

        for _round in range(self.max_rounds):
            response = await self.client.chat_completions(
                model=self.model,
                provider=self.provider,
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
            "reply": "도구 호출 루프가 너무 오래 지속되었습니다.",
            "error": "max_rounds_exceeded",
        }

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
