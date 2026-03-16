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
    return _contains_any(
        lowered, (".hwp", ".hwpx", "기존 문서", "문서 수정", "공식문서")
    )


def _looks_like_search_request(lowered: str) -> bool:
    return _contains_any(lowered, ("find", "search", "찾기", "검색"))


def _extract_document_path(message: str) -> str | None:
    quoted = _extract_quoted_text(message)
    if isinstance(quoted, str) and quoted.lower().endswith((".hwp", ".hwpx")):
        return quoted
    match = re.search(r"([^\s]+\.(?:hwp|hwpx))", message, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _extract_table_dimensions(message: str) -> tuple[int, int] | None:
    patterns = [
        r"(\d+)\s*행\s*(\d+)\s*열",
        r"(\d+)\s*열\s*(\d+)\s*행",
        r"(\d+)\s*[xX]\s*(\d+)",
        r"(\d+)\s*by\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            first = int(match.group(1))
            second = int(match.group(2))
            if pattern == r"(\d+)\s*열\s*(\d+)\s*행":
                return second, first
            return first, second
    return None


def _extract_field_name(message: str) -> str | None:
    match = re.search(r"필드\s+([\w가-힣]+)", message)
    if match:
        return match.group(1).rstrip("에")
    match = re.search(r"([\w가-힣]+?)에\s*[\"']", message)
    if match:
        return match.group(1)
    return None


def _extract_insert_text(message: str) -> str | None:
    quoted_values = re.findall(r'"([^"]+)"', message)
    if len(quoted_values) >= 2:
        return quoted_values[-1].strip()
    if len(quoted_values) == 1 and not quoted_values[0].lower().endswith(
        (".hwp", ".hwpx")
    ):
        return quoted_values[0].strip()
    return None


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
        self,
        message: str,
        session_id: str | None = None,
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
        if intent in (
            "create",
            "insert_text",
            "save",
            "open_document",
            "table",
            "field_form",
        ):
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

        if intent == "open_document":
            return await self._handle_existing_document_edit(state, message)

        if intent == "table":
            return await self._handle_table_request(state, message)

        if intent == "field_form":
            return await self._handle_field_request(state, message)

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

    async def _handle_existing_document_edit(
        self,
        state: AgentState,
        message: str,
    ) -> AgentState:
        platform_state = await self._call_first_available(
            state, ["hwp_platform_info"], {}
        )
        platform_result = platform_state.get("tool_result")
        has_document = False
        if isinstance(platform_result, dict):
            has_document = platform_result.get("has_document") is True

        path = _extract_document_path(message)
        if not has_document and not path:
            return {
                "intent": "open_document",
                "reply": "기존 문서를 수정하려면 열 문서 경로를 알려주세요.",
                "error": "document_path_required",
                "selected_tool_name": platform_state.get(
                    "selected_tool_name", "hwp_platform_info"
                ),
                "selected_tool_id": platform_state.get("selected_tool_id", ""),
                "arguments": platform_state.get("arguments", {}),
                "tool_result": platform_result,
            }

        final_state = platform_state
        if path:
            open_state = await self._call_first_available(
                state, ["hwp_open"], {"path": path}
            )
            if open_state.get("error"):
                return open_state
            final_state = open_state

        insert_text = _extract_insert_text(message)
        if not insert_text:
            return final_state

        insert_state = await self._call_first_available(
            state,
            ["hwp_insert_text", "hwp_windows_insert_text"],
            {"text": insert_text},
        )
        insert_state["intent"] = "open_document"
        return insert_state

    async def _handle_table_request(
        self,
        state: AgentState,
        message: str,
    ) -> AgentState:
        dims = _extract_table_dimensions(message)
        if dims is None:
            return {
                "reply": "표를 만들려면 행과 열 수를 함께 알려주세요. 예: 2행 3열 표",
                "error": "missing_table_dimensions",
            }

        rows, cols = dims
        table_state = await self._call_first_available(
            state,
            ["hwp_create_table"],
            {"rows": rows, "cols": cols},
        )
        table_state["intent"] = "table"
        return table_state

    async def _handle_field_request(
        self,
        state: AgentState,
        message: str,
    ) -> AgentState:
        field_name = _extract_field_name(message)
        if not field_name:
            return {
                "reply": "양식 필드 이름을 알려주세요.",
                "error": "missing_field_name",
            }

        text = _extract_insert_text(message)
        if text:
            field_state = await self._call_first_available(
                state,
                ["hwp_put_field_text"],
                {"name": field_name, "text": text},
            )
        else:
            field_state = await self._call_first_available(
                state,
                ["hwp_create_field"],
                {"name": field_name},
            )
        field_state["intent"] = "field_form"
        return field_state

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

        if name == "hwp_open":
            path = args.get("path")
            return {"path": path} if isinstance(path, str) else {}

        if name == "hwp_create_table":
            rows = args.get("rows")
            cols = args.get("cols")
            if isinstance(rows, int) and isinstance(cols, int):
                return {"rows": rows, "cols": cols}
            return {}

        if name in ("hwp_create_field", "hwp_put_field_text"):
            field_name = args.get("name")
            if not isinstance(field_name, str):
                return {}
            payload = {"name": field_name}
            text = args.get("text")
            if name == "hwp_put_field_text":
                if not isinstance(text, str):
                    return {}
                payload["text"] = text
            return payload

        return {
            key: value
            for key, value in args.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }
