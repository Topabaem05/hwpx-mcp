import pytest

from hwpx_mcp.agentic.tool_only_agent import ToolOnlyAgent


class DummyTool:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
    ):
        self._name = name
        self._description = description
        self._input_schema = input_schema or {}
        self._output_schema = output_schema

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

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, object]):
        self.calls.append((name, arguments))
        return {
            "success": True,
            "tool": name,
            "arguments": arguments,
        }


@pytest.mark.asyncio
async def test_tool_only_agent_status_case_calls_ping_tool():
    backend = DummyBackend(
        [
            DummyTool("hwp_ping", "Check server status"),
            DummyTool("hwp_capabilities", "List capabilities"),
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("상태 확인해줘")

    assert result["success"] is True
    assert result["intent"] == "status"
    assert result["selected_tool"] == "hwp_ping"
    assert backend.calls[0][0] == "hwp_ping"


@pytest.mark.asyncio
async def test_tool_only_agent_template_case_calls_template_tool():
    backend = DummyBackend(
        [
            DummyTool("hwp_list_templates", "List built-in templates"),
            DummyTool("hwp_ping", "Check status"),
        ]
    )
    agent = ToolOnlyAgent(backend)

    result = await agent.run("템플릿 목록 보여줘")

    assert result["success"] is True
    assert result["case"] == "template_workflow"
    assert result["selected_tool"] == "hwp_list_templates"


@pytest.mark.asyncio
async def test_tool_only_agent_create_case_uses_hwpx_tool_with_text():
    backend = DummyBackend([DummyTool("hwp_create_hwpx", "Create HWPX from text")])
    agent = ToolOnlyAgent(backend)

    result = await agent.run('문서 생성 "분기 보고서"')

    assert result["success"] is True
    assert result["intent"] == "create"
    assert result["selected_tool"] == "hwp_create_hwpx"
    assert result["arguments"] == {
        "text": "분기 보고서",
        "filename": "agent_output.hwpx",
    }


@pytest.mark.asyncio
async def test_tool_only_agent_search_without_keyword_requests_keyword():
    backend = DummyBackend([DummyTool("hwp_find", "Find text in current document")])
    agent = ToolOnlyAgent(backend)

    result = await agent.run("문서에서 검색해줘")

    assert result["success"] is True
    assert result["intent"] == "search"
    assert result["selected_tool"] == "hwp_find"
    assert isinstance(result["arguments"].get("text"), str)
