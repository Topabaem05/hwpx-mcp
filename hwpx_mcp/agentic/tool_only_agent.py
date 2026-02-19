from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
import inspect
from collections.abc import Callable
import re
from typing import Any
from typing import Mapping
from typing import Literal
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from .gateway import AgenticGateway
from .gateway import BackendServer
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


class AgentState(TypedDict, total=False):
    message: str
    session_id: str
    tools_by_name: dict[str, str]
    case: CaseName
    intent: IntentName
    subagent: SubagentName
    selected_tool_name: str
    selected_tool_id: str
    arguments: dict[str, JsonValue]
    tool_result: object
    reply: str
    error: str


def _extract_quoted_text(message: str) -> str | None:
    match = re.search(r'"([^"]+)"', message)
    if match:
        return match.group(1).strip()
    match = re.search(r"'([^']+)'", message)
    if match:
        return match.group(1).strip()
    return None


def _parse_intent(message: str) -> IntentName:
    lowered = message.lower()
    if any(token in lowered for token in ("status", "ping", "상태", "헬스")):
        return "status"
    if any(
        token in lowered for token in ("capability", "capabilities", "지원", "가능")
    ):
        return "capabilities"
    if any(token in lowered for token in ("template", "템플릿", "양식")):
        return "template"
    if any(token in lowered for token in ("export pdf", "pdf", "내보내기")):
        return "export_pdf"
    if any(token in lowered for token in ("save", "저장")):
        return "save"
    if any(token in lowered for token in ("find", "search", "찾기", "검색")):
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
        any(token in lowered for token in ("template", "템플릿", "양식"))
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


@dataclass(slots=True)
class ToolOnlyAgent:
    backend_server: BackendServer
    _gateway: AgenticGateway = field(init=False, repr=False)
    _graph: Any = field(init=False, repr=False)
    _tool_callables: dict[str, Callable[..., object]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self._gateway = AgenticGateway(self.backend_server)
        self._graph = self._build_graph()

    async def run(
        self, message: str, session_id: str | None = None
    ) -> dict[str, object]:
        final_state = await self._graph.ainvoke(
            {
                "message": message.strip(),
                "session_id": (session_id or "").strip(),
            }
        )
        return {
            "success": "error" not in final_state,
            "case": final_state.get("case", "degraded_recovery"),
            "intent": final_state.get("intent", "unknown"),
            "subagent": final_state.get("subagent", "recovery_agent"),
            "selected_tool": final_state.get("selected_tool_name"),
            "arguments": final_state.get("arguments", {}),
            "reply": final_state.get("reply", "요청을 처리하지 못했습니다."),
            "result": final_state.get("tool_result"),
            "error": final_state.get("error"),
        }

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("prepare", self._node_prepare)
        graph.add_node("classify", self._node_classify)
        graph.add_node("route", self._node_route)
        graph.add_node("status_agent", self._status_agent)
        graph.add_node("template_agent", self._template_agent)
        graph.add_node("document_agent", self._document_agent)
        graph.add_node("export_agent", self._export_agent)
        graph.add_node("search_agent", self._search_agent)
        graph.add_node("recovery_agent", self._recovery_agent)
        graph.add_node("finalize", self._node_finalize)

        graph.add_edge(START, "prepare")
        graph.add_edge("prepare", "classify")
        graph.add_edge("classify", "route")
        graph.add_conditional_edges(
            "route",
            lambda state: state.get("subagent", "recovery_agent"),
            {
                "status_agent": "status_agent",
                "template_agent": "template_agent",
                "document_agent": "document_agent",
                "export_agent": "export_agent",
                "search_agent": "search_agent",
                "recovery_agent": "recovery_agent",
            },
        )
        graph.add_edge("status_agent", "finalize")
        graph.add_edge("template_agent", "finalize")
        graph.add_edge("document_agent", "finalize")
        graph.add_edge("export_agent", "finalize")
        graph.add_edge("search_agent", "finalize")
        graph.add_edge("recovery_agent", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _node_prepare(self, state: AgentState) -> AgentState:
        await self._gateway.refresh_registry()
        self._tool_callables = self._collect_tool_callables()
        tools_by_name = {
            record.name: record.tool_id for record in self._gateway.registry
        }
        return {"tools_by_name": tools_by_name}

    async def _node_classify(self, state: AgentState) -> AgentState:
        tools_by_name = state.get("tools_by_name", {})
        message = state.get("message", "")
        case = _detect_case(message, set(tools_by_name.keys()))
        intent = _parse_intent(message)
        return {"case": case, "intent": intent}

    async def _node_route(self, state: AgentState) -> AgentState:
        intent = state.get("intent", "unknown")
        case = state.get("case", "degraded_recovery")

        if intent in ("status", "capabilities"):
            return {"subagent": "status_agent"}
        if intent == "template" or case == "template_workflow":
            return {"subagent": "template_agent"}
        if intent == "export_pdf":
            return {"subagent": "export_agent"}
        if intent == "search":
            return {"subagent": "search_agent"}
        if intent in ("create", "insert_text", "save"):
            return {"subagent": "document_agent"}
        return {"subagent": "recovery_agent"}

    async def _status_agent(self, state: AgentState) -> AgentState:
        intent = state.get("intent", "status")
        if intent == "capabilities":
            preferred = [
                "hwp_capabilities",
                "hwp_get_capabilities",
                "hwp_platform_info",
            ]
        else:
            preferred = ["hwp_ping", "hwp_platform_info", "hwp_capabilities"]
        return await self._call_first_available(state, preferred, {})

    async def _template_agent(self, state: AgentState) -> AgentState:
        return await self._call_first_available(
            state,
            ["hwp_list_templates", "hwp_search_template"],
            {},
        )

    async def _document_agent(self, state: AgentState) -> AgentState:
        intent = state.get("intent", "unknown")
        message = state.get("message", "")
        text_payload = _extract_quoted_text(message)

        if intent == "create":
            if text_payload:
                args: dict[str, JsonValue] = {
                    "text": text_payload,
                    "filename": "agent_output.hwpx",
                }
                return await self._call_first_available(
                    state, ["hwp_create_hwpx"], args
                )
            return await self._call_first_available(state, ["hwp_create"], {})

        if intent == "save":
            output_path = str(Path.cwd() / "agent_output.hwpx")
            args = {"path": output_path}
            return await self._call_first_available(
                state, ["hwp_save", "hwp_save_document"], args
            )

        insert_text = text_payload or message
        return await self._call_first_available(
            state,
            ["hwp_insert_text", "hwp_windows_insert_text"],
            {"text": insert_text},
        )

    async def _export_agent(self, state: AgentState) -> AgentState:
        output_path = str(Path.cwd() / "agent_output.pdf")
        return await self._call_first_available(
            state,
            ["hwp_export_pdf", "hwp_save_as"],
            {"output_path": output_path, "format": "pdf", "path": output_path},
        )

    async def _search_agent(self, state: AgentState) -> AgentState:
        message = state.get("message", "")
        keyword = _extract_quoted_text(message)
        if not keyword:
            tokens = [
                token for token in re.findall(r"[\w가-힣]+", message) if len(token) > 1
            ]
            keyword = tokens[-1] if tokens else ""

        if not keyword:
            return {
                "reply": '검색어를 따옴표로 감싸 입력해 주세요. 예: "매출" 찾아줘',
                "error": "missing_search_keyword",
            }

        return await self._call_first_available(
            state,
            ["hwp_find", "hwp_search_text"],
            {"text": keyword, "query": keyword},
        )

    async def _recovery_agent(self, state: AgentState) -> AgentState:
        tool_names = sorted(state.get("tools_by_name", {}).keys())
        sample = ", ".join(tool_names[:10]) if tool_names else "none"
        return {
            "reply": (
                "요청을 직접 실행할 케이스를 찾지 못했습니다. "
                "현재 사용 가능한 툴 예시: "
                f"{sample}"
            ),
            "error": "no_matching_subagent",
        }

    async def _node_finalize(self, state: AgentState) -> AgentState:
        if state.get("reply"):
            return state

        selected_tool = state.get("selected_tool_name")
        if not selected_tool:
            return {
                "reply": "적절한 툴을 찾지 못했습니다.",
                "error": "tool_not_selected",
            }

        result = state.get("tool_result")
        return {
            "reply": f"[{selected_tool}] 실행 완료\n{result}",
        }

    async def _call_first_available(
        self,
        state: AgentState,
        candidates: list[str],
        candidate_args: dict[str, JsonValue],
    ) -> AgentState:
        tools_by_name = state.get("tools_by_name", {})
        for name in candidates:
            tool_id = tools_by_name.get(name)
            if not tool_id:
                continue

            normalized_args = self._normalize_arguments(name, candidate_args)
            direct_callable = self._tool_callables.get(name)
            if direct_callable is not None:
                try:
                    result = direct_callable(**normalized_args)
                    if inspect.isawaitable(result):
                        result = await result
                    return self._build_tool_state(
                        name=name,
                        tool_id=tool_id,
                        arguments=normalized_args,
                        result=result,
                    )
                except Exception as exc:
                    return {
                        "selected_tool_name": name,
                        "selected_tool_id": tool_id,
                        "arguments": normalized_args,
                        "tool_result": {
                            "success": False,
                            "message": f"tool_call_failed: {exc}",
                        },
                        "error": f"tool_call_failed: {exc}",
                    }

            called = await self._gateway.tool_call(tool_id, normalized_args)
            return self._build_tool_state(
                name=name,
                tool_id=tool_id,
                arguments=normalized_args,
                result=called,
                use_gateway_result=True,
            )

        return {
            "error": "no_available_tool",
            "reply": "현재 케이스에서 실행 가능한 툴이 없습니다.",
        }

    def _collect_tool_callables(self) -> dict[str, Callable[..., object]]:
        tool_manager = getattr(self.backend_server, "_tool_manager", None)
        if not tool_manager:
            return {}

        raw_tools = getattr(tool_manager, "_tools", None)
        if not isinstance(raw_tools, Mapping):
            return {}

        callables: dict[str, Callable[..., object]] = {}
        for name, entry in raw_tools.items():
            function = getattr(entry, "fn", None)
            if callable(function):
                callables[name] = function
        return callables

    @staticmethod
    def _build_tool_state(
        *,
        name: str,
        tool_id: str,
        arguments: dict[str, JsonValue],
        result: object,
        use_gateway_result: bool = False,
    ) -> AgentState:
        if use_gateway_result:
            if not isinstance(result, dict):
                return {
                    "selected_tool_name": name,
                    "selected_tool_id": tool_id,
                    "arguments": arguments,
                    "tool_result": result,
                    "error": "invalid_gateway_response",
                }

            if result.get("success") is False:
                message = result.get("message", "tool_call_failed")
                return {
                    "selected_tool_name": name,
                    "selected_tool_id": tool_id,
                    "arguments": arguments,
                    "tool_result": result,
                    "error": str(message),
                }

            tool_result = result.get("result")
            if tool_result is None and "result" not in result:
                return {
                    "selected_tool_name": name,
                    "selected_tool_id": tool_id,
                    "arguments": arguments,
                    "tool_result": result,
                    "error": "invalid_gateway_response",
                }

            return {
                "selected_tool_name": name,
                "selected_tool_id": tool_id,
                "arguments": arguments,
                "tool_result": tool_result,
            }

        if isinstance(result, dict) and result.get("success") is False:
            message = result.get("message", "tool_call_failed")
            return {
                "selected_tool_name": name,
                "selected_tool_id": tool_id,
                "arguments": arguments,
                "tool_result": result,
                "error": str(message),
            }

        return {
            "selected_tool_name": name,
            "selected_tool_id": tool_id,
            "arguments": arguments,
            "tool_result": result,
        }

    @staticmethod
    def _normalize_arguments(
        name: str, args: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        if name == "hwp_save":
            path = args.get("path")
            if isinstance(path, str):
                return {"path": path}
            return {}

        if name == "hwp_export_pdf":
            output_path = args.get("output_path")
            if isinstance(output_path, str):
                return {"output_path": output_path}
            return {}

        if name == "hwp_save_as":
            path = args.get("path")
            fmt = args.get("format", "pdf")
            if isinstance(path, str) and isinstance(fmt, str):
                return {"path": path, "format": fmt}
            return {}

        if name in ("hwp_insert_text", "hwp_windows_insert_text", "hwp_create_hwpx"):
            text = args.get("text")
            if not isinstance(text, str):
                return {}
            payload: dict[str, JsonValue] = {"text": text}
            filename = args.get("filename")
            if isinstance(filename, str):
                payload["filename"] = filename
            return payload

        if name in ("hwp_find", "hwp_search_text"):
            if name == "hwp_find":
                text = args.get("text")
                return {"text": text} if isinstance(text, str) else {}
            query = args.get("query")
            return {"query": query} if isinstance(query, str) else {}

        return {
            key: value
            for key, value in args.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }
