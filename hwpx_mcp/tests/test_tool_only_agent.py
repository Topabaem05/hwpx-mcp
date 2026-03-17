import pytest
from collections.abc import Callable

from hwpx_mcp.agentic.models import JsonValue
from hwpx_mcp.agentic.tool_only_agent import ToolOnlyAgent


class DummyTool:
    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable[..., dict[str, JsonValue]],
        input_schema: dict[str, JsonValue] | None = None,
        output_schema: dict[str, JsonValue] | None = None,
    ):
        self._name = name
        self._description = description
        self._input_schema = input_schema or {}
        self._output_schema = output_schema
        self.fn = fn

    def model_dump(self) -> dict[str, object]:
        dumped: dict[str, object] = {
            "name": self._name,
            "description": self._description,
            "inputSchema": self._input_schema,
        }
        if self._output_schema is not None:
            dumped["outputSchema"] = self._output_schema
        return dumped


class DummyBackend:
    def __init__(self, tools: list[DummyTool]):
        self._tools = tools
        self.calls: list[tuple[str, dict[str, JsonValue]]] = []
        self.call_tool_calls: list[tuple[str, dict[str, JsonValue]]] = []
        self._tool_manager = self._create_tool_manager()

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, JsonValue]):
        self.call_tool_calls.append((name, arguments))
        self.calls.append((name, arguments))
        if self.calls:
            return {
                "success": True,
                "tool": self.calls[-1][0],
                "arguments": self.calls[-1][1],
            }
        return {"success": True}

    def _create_tool_manager(self):
        tool_map: dict[str, object] = {}
        for tool in self._tools:
            tool_map[tool._name] = tool

        class _Manager:
            def __init__(self, tools: dict[str, object]):
                self._tools = tools

        return _Manager(tool_map)


def _recording_tool(
    name: str,
    calls: list[tuple[str, dict[str, JsonValue]]],
    result: dict[str, JsonValue],
) -> Callable[..., dict[str, JsonValue]]:
    def tool(**kwargs: JsonValue) -> dict[str, JsonValue]:
        calls.append((name, kwargs.copy()))
        return result

    return tool


@pytest.mark.asyncio
async def test_tool_only_agent_status_case_calls_ping_tool():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_ping",
                "Check server status",
                fn=_recording_tool(
                    "hwp_ping", calls, {"success": True, "message": "pong"}
                ),
            ),
            DummyTool(
                "hwp_capabilities",
                "List capabilities",
                fn=_recording_tool(
                    "hwp_capabilities",
                    calls,
                    {"success": True, "message": "capabilities"},
                ),
            ),
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("상태 확인해줘")

    assert result["success"] is True
    assert result["intent"] == "status"
    assert result["selected_tool"] == "hwp_ping"
    assert calls == [("hwp_ping", {})]
    assert backend.call_tool_calls == []


@pytest.mark.asyncio
async def test_tool_only_agent_template_case_calls_template_tool():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_list_templates",
                "List built-in templates",
                fn=_recording_tool(
                    "hwp_list_templates", calls, {"success": True, "templates": []}
                ),
            ),
            DummyTool(
                "hwp_ping",
                "Check status",
                fn=_recording_tool("hwp_ping", calls, {"success": True}),
            ),
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("템플릿 목록 보여줘")

    assert result["success"] is True
    assert result["case"] == "template_workflow"
    assert result["selected_tool"] == "hwp_list_templates"
    assert calls == [("hwp_list_templates", {})]
    assert backend.call_tool_calls == []


@pytest.mark.asyncio
async def test_tool_only_agent_create_case_uses_hwpx_tool_with_text():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_create_hwpx",
                "Create HWPX from text",
                fn=_recording_tool(
                    "hwp_create_hwpx",
                    calls,
                    {"success": True, "path": "/tmp/agent_output.hwpx"},
                ),
            )
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run('문서 생성 "분기 보고서"')

    assert result["success"] is True
    assert result["intent"] == "create"
    assert result["selected_tool"] == "hwp_create_hwpx"
    assert result["arguments"] == {
        "text": "분기 보고서",
        "filename": "agent_output.hwpx",
    }
    assert calls == [
        ("hwp_create_hwpx", {"text": "분기 보고서", "filename": "agent_output.hwpx"})
    ]


@pytest.mark.asyncio
async def test_tool_only_agent_search_without_keyword_requests_keyword():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_find",
                "Find text in current document",
                fn=_recording_tool("hwp_find", calls, {"success": True, "found": True}),
            )
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("문서에서 검색해줘")

    assert result["success"] is True
    assert result["intent"] == "search"
    assert result["selected_tool"] == "hwp_find"
    arguments = result["arguments"]
    assert isinstance(arguments, dict)
    assert isinstance(arguments.get("text"), str)
    assert calls[0][0] == "hwp_find"


@pytest.mark.asyncio
async def test_tool_only_agent_can_fallback_to_gateway_call_when_no_direct_callable_available():
    calls: list[tuple[str, dict[str, JsonValue]]] = []

    class NoCallableBackend:
        def __init__(self) -> None:
            self.call_tool_calls: list[tuple[str, dict[str, JsonValue]]] = []

        async def list_tools(self):
            return [
                DummyTool(
                    "hwp_platform_info",
                    "Platform information",
                    fn=_recording_tool(
                        "hwp_platform_info",
                        calls,
                        {"success": True, "platform": "test"},
                    ),
                )
            ]

        async def call_tool(self, name: str, arguments: dict[str, JsonValue]):
            self.call_tool_calls.append((name, arguments))
            return {"success": True, "tool": name, "arguments": arguments}

    backend = NoCallableBackend()
    agent = ToolOnlyAgent(backend)

    result = await agent.run("상태 확인해줘")

    assert result["success"] is True
    assert result["selected_tool"] == "hwp_platform_info"
    assert backend.call_tool_calls == [("hwp_platform_info", {})]
    assert not calls


@pytest.mark.asyncio
async def test_tool_only_agent_uses_table_tool_for_table_request():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_create_table",
                "Create a table",
                fn=_recording_tool(
                    "hwp_create_table",
                    calls,
                    {"success": True, "message": "Created 2x2 table"},
                ),
            )
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("2행 2열 표를 만들어줘")

    assert result["success"] is True
    assert result["intent"] == "table"
    assert result["selected_tool"] == "hwp_create_table"
    assert result["arguments"] == {"rows": 2, "cols": 2}
    assert calls == [("hwp_create_table", {"rows": 2, "cols": 2})]


@pytest.mark.asyncio
async def test_tool_only_agent_supports_reverse_korean_table_dimensions():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_create_table",
                "Create a table",
                fn=_recording_tool(
                    "hwp_create_table",
                    calls,
                    {"success": True, "message": "Created 2x3 table"},
                ),
            )
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("3열 2행 표를 만들어줘")

    assert result["success"] is True
    assert result["arguments"] == {"rows": 2, "cols": 3}
    assert calls == [("hwp_create_table", {"rows": 2, "cols": 3})]


@pytest.mark.asyncio
async def test_tool_only_agent_uses_field_tool_for_form_field_request():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_put_field_text",
                "Set field text",
                fn=_recording_tool(
                    "hwp_put_field_text",
                    calls,
                    {"success": True, "message": "field updated"},
                ),
            )
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run('양식 필드 이름에 "홍길동" 넣어줘')

    assert result["success"] is True
    assert result["intent"] == "field_form"
    assert result["selected_tool"] == "hwp_put_field_text"
    assert result["arguments"] == {"name": "이름", "text": "홍길동"}
    assert calls == [("hwp_put_field_text", {"name": "이름", "text": "홍길동"})]


@pytest.mark.asyncio
async def test_tool_only_agent_opens_document_before_editing_existing_path():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_platform_info",
                "Platform information",
                fn=_recording_tool(
                    "hwp_platform_info",
                    calls,
                    {"success": True, "has_document": False, "platform": "windows"},
                ),
            ),
            DummyTool(
                "hwp_open",
                "Open document",
                fn=_recording_tool(
                    "hwp_open",
                    calls,
                    {"success": True, "message": "Opened"},
                ),
            ),
            DummyTool(
                "hwp_insert_text",
                "Insert text",
                fn=_recording_tool(
                    "hwp_insert_text",
                    calls,
                    {"success": True, "message": "Inserted"},
                ),
            ),
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run('"official.hwpx" 문서를 수정해서 "승인 완료" 추가해줘')

    assert result["success"] is True
    assert result["intent"] == "open_document"
    assert calls == [
        ("hwp_platform_info", {}),
        ("hwp_open", {"path": "official.hwpx"}),
        ("hwp_insert_text", {"text": "승인 완료"}),
    ]


@pytest.mark.asyncio
async def test_tool_only_agent_reopens_requested_path_even_when_other_document_is_open():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_platform_info",
                "Platform information",
                fn=_recording_tool(
                    "hwp_platform_info",
                    calls,
                    {"success": True, "has_document": True, "platform": "windows"},
                ),
            ),
            DummyTool(
                "hwp_open",
                "Open document",
                fn=_recording_tool(
                    "hwp_open",
                    calls,
                    {"success": True, "message": "Opened"},
                ),
            ),
            DummyTool(
                "hwp_insert_text",
                "Insert text",
                fn=_recording_tool(
                    "hwp_insert_text",
                    calls,
                    {"success": True, "message": "Inserted"},
                ),
            ),
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run('"official.hwpx"에 "승인 완료" 추가해줘')

    assert result["success"] is True
    assert result["intent"] == "open_document"
    assert calls == [
        ("hwp_platform_info", {}),
        ("hwp_open", {"path": "official.hwpx"}),
        ("hwp_insert_text", {"text": "승인 완료"}),
    ]


@pytest.mark.asyncio
async def test_tool_only_agent_keeps_literal_form_search_as_search():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_find",
                "Find text in current document",
                fn=_recording_tool(
                    "hwp_find",
                    calls,
                    {"success": True, "found": True},
                ),
            )
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run('"양식" 검색해줘')

    assert result["success"] is True
    assert result["intent"] == "search"
    assert result["selected_tool"] == "hwp_find"
    assert calls == [("hwp_find", {"text": "양식"})]


@pytest.mark.asyncio
async def test_tool_only_agent_refuses_existing_document_edit_without_path_or_open_doc():
    calls: list[tuple[str, dict[str, JsonValue]]] = []
    backend = DummyBackend(
        [
            DummyTool(
                "hwp_platform_info",
                "Platform information",
                fn=_recording_tool(
                    "hwp_platform_info",
                    calls,
                    {"success": True, "has_document": False, "platform": "linux"},
                ),
            ),
            DummyTool(
                "hwp_insert_text",
                "Insert text",
                fn=_recording_tool(
                    "hwp_insert_text",
                    calls,
                    {"success": True, "message": "Inserted"},
                ),
            ),
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("공식문서를 수정해줘")

    assert result["success"] is False
    assert result["intent"] == "open_document"
    assert result["error"] == "document_path_required"
    assert calls == [("hwp_platform_info", {})]
