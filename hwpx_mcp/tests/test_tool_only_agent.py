import pytest

from hwpx_mcp.agentic.tool_only_agent import ToolOnlyAgent


class DummyTool:
    def __init__(
        self,
        name: str,
        description: str,
        fn,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
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
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.call_tool_calls: list[tuple[str, dict[str, object]]] = []
        self._tool_manager = self._create_tool_manager()

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, object]):
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
    name: str, calls: list[tuple[str, dict[str, object]]], result: dict
):
    def tool(**kwargs):
        calls.append((name, kwargs.copy()))
        return result

    return tool


@pytest.mark.asyncio
async def test_tool_only_agent_status_case_calls_ping_tool():
    calls: list[tuple[str, dict[str, object]]] = []
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
    calls: list[tuple[str, dict[str, object]]] = []
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
    calls: list[tuple[str, dict[str, object]]] = []
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
    calls: list[tuple[str, dict[str, object]]] = []
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
    assert isinstance(result["arguments"].get("text"), str)
    assert calls[0][0] == "hwp_find"


@pytest.mark.asyncio
async def test_tool_only_agent_can_fallback_to_gateway_call_when_no_direct_callable_available():
    calls: list[tuple[str, dict[str, object]]] = []

    class NoCallableBackend:
        def __init__(self) -> None:
            self.call_tool_calls: list[tuple[str, dict[str, object]]] = []

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

        async def call_tool(self, name: str, arguments: dict[str, object]):
            self.call_tool_calls.append((name, arguments))
            return {"success": True, "tool": name, "arguments": arguments}

    backend = NoCallableBackend()
    agent = ToolOnlyAgent(backend)

    result = await agent.run("상태 확인해줘")

    assert result["success"] is True
    assert result["selected_tool"] == "hwp_platform_info"
    assert backend.call_tool_calls == [("hwp_platform_info", {})]
    assert not calls
