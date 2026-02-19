from __future__ import annotations

from starlette.applications import Starlette
from starlette.testclient import TestClient

from hwpx_mcp.agentic.http_api import DEFAULT_MODEL
from hwpx_mcp.agentic.http_api import DEFAULT_PROVIDER
from hwpx_mcp.agentic.http_api import build_agent_http_routes


class DummyTool:
    def __init__(self, name: str, description: str, fn):
        self._name = name
        self._description = description
        self.fn = fn

    def model_dump(self) -> dict[str, object]:
        return {
            "name": self._name,
            "description": self._description,
            "inputSchema": {},
        }


class DummyBackend:
    def __init__(self, tools: list[DummyTool]):
        self._tools = tools
        self.call_tool_calls: list[tuple[str, dict[str, object]]] = []
        self._tool_manager = self._create_tool_manager()

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, object]):
        self.call_tool_calls.append((name, arguments))
        return {"success": True, "name": name, "arguments": arguments}

    def _create_tool_manager(self):
        tool_map: dict[str, object] = {}
        for tool in self._tools:
            tool_map[tool._name] = tool

        class _Manager:
            def __init__(self, tools: dict[str, object]):
                self._tools = tools

        return _Manager(tool_map)


def _create_client():
    calls: list[tuple[str, dict[str, object]]] = []

    def ping_tool(**kwargs):
        calls.append(("hwp_ping", kwargs.copy()))
        return {"success": True, "message": "pong"}

    backend = DummyBackend(
        [
            DummyTool(
                name="hwp_ping",
                description="Check backend status",
                fn=ping_tool,
            )
        ]
    )
    app = Starlette(routes=build_agent_http_routes(backend))
    return TestClient(app), backend, calls


def test_agent_health_endpoint_uses_expected_defaults():
    client, _, _ = _create_client()
    with client:
        response = client.get("/agent/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["defaults"]["provider"] == DEFAULT_PROVIDER
    assert payload["defaults"]["model"] == DEFAULT_MODEL


def test_agent_chat_endpoint_runs_tool_only_agent_directly():
    client, backend, calls = _create_client()

    with client:
        response = client.post(
            "/agent/chat",
            json={
                "message": "상태 확인해줘",
                "session_id": "session-1",
                "runtime": {
                    "provider": "cerebras/fp16",
                    "model": "openai/gpt-oss-120b",
                    "api_key": "sk-test",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["selected_tool"] == "hwp_ping"
    assert payload["runtime"] == {
        "provider": "cerebras/fp16",
        "model": "openai/gpt-oss-120b",
        "api_key_present": True,
    }
    assert calls == [("hwp_ping", {})]
    assert backend.call_tool_calls == []


def test_agent_chat_endpoint_requires_non_empty_message():
    client, _, _ = _create_client()

    with client:
        response = client.post("/agent/chat", json={"message": ""})

    assert response.status_code == 422
    assert response.json()["error"] == "message_required"
