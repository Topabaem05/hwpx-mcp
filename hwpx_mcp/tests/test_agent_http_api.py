from __future__ import annotations

import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hwpx_mcp.agentic.gateway import BackendServer
from hwpx_mcp.agentic.http_api import DEFAULT_MODEL
from hwpx_mcp.agentic.http_api import DEFAULT_PROVIDER
from hwpx_mcp.agentic.http_api import build_agent_http_router
from hwpx_mcp.agentic.openrouter_agent import AgentAuthError
from hwpx_mcp.agentic.openrouter_agent import JsonValue
from hwpx_mcp.agentic.openrouter_agent import LlmRequestError
from hwpx_mcp.agentic.openrouter_agent import OpenRouterClient
from hwpx_mcp.agentic.openrouter_agent import OpenRouterToolAgent


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
        self.call_tool_calls: list[tuple[str, dict[str, JsonValue]]] = []
        self._tool_manager = self._create_tool_manager()

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, JsonValue]):
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

    class FakeOpenRouterClient(OpenRouterClient):
        def __init__(self):
            super().__init__(api_key="sk-test")
            self._step = 0

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
            _ = (model, provider, messages, tools, tool_choice, proxy_url)
            self._step += 1

            if self._step == 1:
                return {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "hwp_ping",
                                            "arguments": "{}",
                                        },
                                    }
                                ],
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
                            "content": "pong",
                        },
                    }
                ]
            }

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
    app = FastAPI()

    def agent_factory(server: BackendServer) -> OpenRouterToolAgent:
        return OpenRouterToolAgent(server, client=FakeOpenRouterClient(), max_rounds=2)

    app.include_router(build_agent_http_router(backend, agent_factory=agent_factory))
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
    assert payload["runtime"] == {
        "provider": DEFAULT_PROVIDER,
        "model": DEFAULT_MODEL,
    }
    assert payload["auth"] == {
        "configured": True,
        "mode": "openai-api-key",
        "available_modes": ["openai-api-key"],
        "accepted_env": [
            "OPENAI_OAUTH_TOKEN",
            "CODEX_OAUTH_TOKEN",
            "OPENAI_API_KEY",
        ],
    }


def test_agent_health_endpoint_reports_missing_auth_for_default_client(monkeypatch):
    monkeypatch.delenv("OPENAI_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    backend = DummyBackend([])
    app = FastAPI()
    app.include_router(build_agent_http_router(backend))
    client = TestClient(app)

    with client:
        response = client.get("/agent/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["auth"] == {
        "configured": False,
        "mode": "none",
        "detail": "OPENAI_OAUTH_TOKEN or CODEX_OAUTH_TOKEN or OPENAI_API_KEY is not set",
        "available_modes": [],
        "accepted_env": [
            "OPENAI_OAUTH_TOKEN",
            "CODEX_OAUTH_TOKEN",
            "OPENAI_API_KEY",
        ],
    }
    assert payload["runtime"] == {
        "provider": DEFAULT_PROVIDER,
        "model": DEFAULT_MODEL,
    }


def test_agent_auth_endpoint_sets_runtime_oauth_token(monkeypatch):
    monkeypatch.delenv("OPENAI_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    backend = DummyBackend([])
    app = FastAPI()
    app.include_router(build_agent_http_router(backend))
    client = TestClient(app)

    with client:
        health_before = client.get("/agent/health")
        assert health_before.status_code == 200
        assert health_before.json()["auth"]["configured"] is False

        auth_set = client.post(
            "/agent/auth",
            json={
                "openai_oauth_token": "Bearer runtime-oauth-token",
                "openai_api_key": "",
                "codex_oauth_token": "",
            },
        )
        assert auth_set.status_code == 200
        auth_payload = auth_set.json()
        assert auth_payload["success"] is True
        assert auth_payload["auth"]["configured"] is True
        assert auth_payload["auth"]["mode"] == "openai-oauth"
        assert auth_payload["auth"]["available_modes"] == ["openai-oauth"]

        auth_noop = client.post("/agent/auth", json={})
        assert auth_noop.status_code == 200
        noop_payload = auth_noop.json()
        assert noop_payload["auth"]["configured"] is True
        assert noop_payload["auth"]["mode"] == "openai-oauth"

        health_after = client.get("/agent/health")
        assert health_after.status_code == 200
        assert health_after.json()["auth"]["configured"] is True
        assert health_after.json()["auth"]["mode"] == "openai-oauth"


def test_agent_config_endpoint_switches_runtime_to_openrouter(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    backend = DummyBackend([])
    app = FastAPI()
    app.include_router(build_agent_http_router(backend))
    client = TestClient(app)

    with client:
        config_set = client.post(
            "/agent/config",
            json={
                "provider": "openrouter",
                "model": "openai/gpt-oss-120b",
            },
        )
        assert config_set.status_code == 200
        config_payload = config_set.json()
        assert config_payload["success"] is True
        assert config_payload["runtime"] == {
            "provider": "openrouter",
            "model": "openai/gpt-oss-120b",
        }
        assert config_payload["auth"] == {
            "configured": False,
            "mode": "none",
            "detail": "OPENROUTER_API_KEY is not set",
            "available_modes": [],
            "accepted_env": ["OPENROUTER_API_KEY"],
        }

        health_after = client.get("/agent/health")
        assert health_after.status_code == 200
        health_payload = health_after.json()
        assert health_payload["runtime"] == {
            "provider": "openrouter",
            "model": "openai/gpt-oss-120b",
        }
        assert health_payload["auth"]["accepted_env"] == ["OPENROUTER_API_KEY"]


def test_agent_auth_endpoint_sets_runtime_openrouter_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    backend = DummyBackend([])
    app = FastAPI()
    app.include_router(build_agent_http_router(backend))
    client = TestClient(app)

    with client:
        config_set = client.post(
            "/agent/config",
            json={
                "provider": "openrouter",
                "model": "openai/gpt-oss-120b",
            },
        )
        assert config_set.status_code == 200

        auth_set = client.post(
            "/agent/auth",
            json={
                "openrouter_api_key": "or-key",
            },
        )
        assert auth_set.status_code == 200
        auth_payload = auth_set.json()
        assert auth_payload["success"] is True
        assert auth_payload["runtime"] == {
            "provider": "openrouter",
            "model": "openai/gpt-oss-120b",
        }
        assert auth_payload["auth"] == {
            "configured": True,
            "mode": "openrouter-api-key",
            "available_modes": ["openrouter-api-key"],
            "accepted_env": ["OPENROUTER_API_KEY"],
        }


def test_agent_config_endpoint_switches_runtime_to_codex_proxy(monkeypatch):
    monkeypatch.delenv("HWPX_CODEX_PROXY_ACCESS_TOKEN", raising=False)

    backend = DummyBackend([])
    app = FastAPI()
    app.include_router(build_agent_http_router(backend))
    client = TestClient(app)

    with client:
        config_set = client.post(
            "/agent/config",
            json={
                "provider": "codex-proxy",
                "model": "gpt-5",
                "proxy_url": "http://127.0.0.1:5011",
            },
        )
        assert config_set.status_code == 200
        config_payload = config_set.json()
        assert config_payload["runtime"] == {
            "provider": "codex-proxy",
            "model": "gpt-5",
            "proxy_url": "http://127.0.0.1:5011/chat/completions",
        }
        assert config_payload["auth"] == {
            "configured": False,
            "mode": "none",
            "detail": "HWPX_CODEX_PROXY_ACCESS_TOKEN is not set",
            "available_modes": [],
            "accepted_env": ["HWPX_CODEX_PROXY_ACCESS_TOKEN"],
        }


def test_agent_auth_endpoint_sets_runtime_codex_proxy_access_token(monkeypatch):
    monkeypatch.delenv("HWPX_CODEX_PROXY_ACCESS_TOKEN", raising=False)

    backend = DummyBackend([])
    app = FastAPI()
    app.include_router(build_agent_http_router(backend))
    client = TestClient(app)

    with client:
        config_set = client.post(
            "/agent/config",
            json={
                "provider": "codex-proxy",
                "model": "gpt-5",
                "proxy_url": "http://127.0.0.1:2455/v1",
            },
        )
        assert config_set.status_code == 200

        auth_set = client.post(
            "/agent/auth",
            json={
                "codex_proxy_access_token": "Bearer proxy-token",
            },
        )
        assert auth_set.status_code == 200
        auth_payload = auth_set.json()
        assert auth_payload["runtime"] == {
            "provider": "codex-proxy",
            "model": "gpt-5",
            "proxy_url": "http://127.0.0.1:2455/v1/chat/completions",
        }
        assert auth_payload["auth"] == {
            "configured": True,
            "mode": "codex-proxy-token",
            "available_modes": ["codex-proxy-token"],
            "accepted_env": ["HWPX_CODEX_PROXY_ACCESS_TOKEN"],
        }


def test_openrouter_agent_uses_openrouter_default_model_when_only_provider_env_is_set(
    monkeypatch,
):
    monkeypatch.setenv("HWPX_AGENT_PROVIDER", "openrouter")
    monkeypatch.delenv("HWPX_AGENT_MODEL", raising=False)

    agent = OpenRouterToolAgent(DummyBackend([]))

    assert agent.runtime_config() == {
        "provider": "openrouter",
        "model": "openai/gpt-oss-120b",
    }


def test_openrouter_agent_uses_codex_proxy_defaults_when_provider_env_is_set(
    monkeypatch,
):
    monkeypatch.setenv("HWPX_AGENT_PROVIDER", "codex-proxy")
    monkeypatch.delenv("HWPX_AGENT_MODEL", raising=False)
    monkeypatch.delenv("HWPX_CODEX_PROXY_URL", raising=False)

    agent = OpenRouterToolAgent(DummyBackend([]))

    assert agent.runtime_config() == {
        "provider": "codex-proxy",
        "model": "gpt-5",
        "proxy_url": "http://127.0.0.1:2455/v1/chat/completions",
    }


def test_agent_config_normalizes_openai_provider_style_model_id():
    agent = OpenRouterToolAgent(DummyBackend([]))

    runtime = agent.set_runtime_config(
        provider="openai",
        model="openai/gpt-4o-mini",
    )

    assert runtime == {
        "provider": "openai",
        "model": "gpt-4o-mini",
    }


def test_agent_chat_endpoint_runs_tool_only_agent_directly():
    client, backend, calls = _create_client()

    with client:
        response = client.post(
            "/agent/chat",
            json={
                "message": "상태 확인해줘",
                "session_id": "session-1",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["selected_tool"] == "hwp_ping"
    assert payload["runtime"] == {
        "provider": DEFAULT_PROVIDER,
        "model": DEFAULT_MODEL,
    }
    assert payload["reply"] == "pong"
    assert calls == []
    assert backend.call_tool_calls == [("hwp_ping", {})]


def test_agent_chat_endpoint_requires_non_empty_message():
    client, _, _ = _create_client()

    with client:
        response = client.post("/agent/chat", json={"message": ""})

    assert response.status_code == 422
    assert response.json()["detail"] == "message_required"


def test_agent_chat_returns_400_for_auth_error():
    backend = DummyBackend([])
    app = FastAPI()

    class ErrorAgent(OpenRouterToolAgent):
        def __init__(self, backend_server: BackendServer, error: Exception):
            super().__init__(backend_server=backend_server)
            self._error = error

        async def run(self, *, message: str, session_id: str = "") -> dict[str, object]:
            _ = (message, session_id)
            raise self._error

    def agent_factory(server: BackendServer) -> OpenRouterToolAgent:
        return ErrorAgent(
            backend_server=server,
            error=AgentAuthError(
                "OPENAI_OAUTH_TOKEN or CODEX_OAUTH_TOKEN or OPENAI_API_KEY is not set"
            ),
        )

    app.include_router(build_agent_http_router(backend, agent_factory=agent_factory))
    client = TestClient(app)

    with client:
        response = client.post("/agent/chat", json={"message": "hello"})

    assert response.status_code == 400
    assert (
        "OPENAI_OAUTH_TOKEN or CODEX_OAUTH_TOKEN or OPENAI_API_KEY is not set"
        in response.json()["detail"]
    )


def test_agent_chat_maps_upstream_llm_500_to_502():
    backend = DummyBackend([])
    app = FastAPI()

    class ErrorAgent(OpenRouterToolAgent):
        def __init__(self, backend_server: BackendServer, error: Exception):
            super().__init__(backend_server=backend_server)
            self._error = error

        async def run(self, *, message: str, session_id: str = "") -> dict[str, object]:
            _ = (message, session_id)
            raise self._error

    def agent_factory(server: BackendServer) -> OpenRouterToolAgent:
        return ErrorAgent(
            backend_server=server,
            error=LlmRequestError(
                status_code=500,
                message="llm_error[openai-api-key]: 500: upstream",
            ),
        )

    app.include_router(build_agent_http_router(backend, agent_factory=agent_factory))
    client = TestClient(app)

    with client:
        response = client.post("/agent/chat", json={"message": "hello"})

    assert response.status_code == 502
    assert "llm_error[openai-api-key]" in response.json()["detail"]


def test_openrouter_client_resolves_codex_oauth_token(monkeypatch):
    monkeypatch.delenv("OPENAI_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("CODEX_OAUTH_TOKEN", "codex-token-value")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = OpenRouterClient()
    mode, token = client._resolve_auth("openai")

    assert mode == "codex-oauth"
    assert token == "codex-token-value"


def test_openrouter_client_trims_bearer_prefix(monkeypatch):
    monkeypatch.setenv("OPENAI_OAUTH_TOKEN", "Bearer oauth-token-value")
    monkeypatch.delenv("CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = OpenRouterClient()
    mode, token = client._resolve_auth("openai")

    assert mode == "openai-oauth"
    assert token == "oauth-token-value"


@pytest.mark.asyncio
async def test_openrouter_client_falls_back_to_api_key_on_oauth_insufficient_quota(
    monkeypatch,
):
    class SequenceClient(OpenRouterClient):
        def __init__(self, responses: list[httpx.Response]):
            super().__init__(api_key="api-token")
            self._responses = responses
            self.auth_headers: list[str] = []
            self.target_urls: list[str] = []

        async def _post_chat_completion(
            self,
            *,
            target_url: str,
            headers: dict[str, str],
            body: dict[str, object],
        ) -> httpx.Response:
            _ = body
            self.auth_headers.append(headers.get("Authorization", ""))
            self.target_urls.append(target_url)
            return self._responses.pop(0)

    monkeypatch.setenv("OPENAI_OAUTH_TOKEN", "oauth-token")
    monkeypatch.delenv("CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    first = httpx.Response(
        status_code=429,
        request=request,
        json={"error": {"type": "insufficient_quota", "message": "quota exhausted"}},
    )
    second = httpx.Response(
        status_code=200,
        request=request,
        json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
    )

    client = SequenceClient([first, second])
    payload = await client.chat_completions(
        model=DEFAULT_MODEL,
        provider="openai",
        messages=[{"role": "user", "content": "hello"}],
        tools=None,
        tool_choice=None,
        proxy_url=None,
    )

    choices = payload.get("choices") if isinstance(payload, dict) else None
    assert isinstance(choices, list) and choices
    first_choice = choices[0]
    assert isinstance(first_choice, dict)
    message = first_choice.get("message")
    assert isinstance(message, dict)
    assert message.get("content") == "ok"
    assert client.auth_headers == ["Bearer oauth-token", "Bearer api-token"]
    assert client.target_urls == [
        "https://api.openai.com/v1/chat/completions",
        "https://api.openai.com/v1/chat/completions",
    ]


@pytest.mark.asyncio
async def test_openrouter_client_uses_openrouter_url_and_model(monkeypatch):
    class RecordingClient(OpenRouterClient):
        def __init__(self):
            super().__init__()
            self.target_url = ""
            self.body: dict[str, object] = {}
            self.headers: dict[str, str] = {}

        async def _post_chat_completion(
            self,
            *,
            target_url: str,
            headers: dict[str, str],
            body: dict[str, object],
        ) -> httpx.Response:
            self.target_url = target_url
            self.headers = headers
            self.body = body
            request = httpx.Request("POST", target_url)
            return httpx.Response(
                status_code=200,
                request=request,
                json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
            )

    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-token")

    client = RecordingClient()
    payload = await client.chat_completions(
        model="openai/gpt-oss-120b",
        provider="openrouter",
        messages=[{"role": "user", "content": "hello"}],
        tools=None,
        tool_choice=None,
        proxy_url=None,
    )

    assert isinstance(payload, dict)
    choices = payload.get("choices")
    assert isinstance(choices, list) and choices
    first_choice = choices[0]
    assert isinstance(first_choice, dict)
    message = first_choice.get("message")
    assert isinstance(message, dict)
    assert message.get("content") == "ok"
    assert client.target_url == "https://openrouter.ai/api/v1/chat/completions"
    assert client.headers["Authorization"] == "Bearer openrouter-token"
    assert client.headers["X-Title"] == "HWPX MCP"
    assert client.body["model"] == "openai/gpt-oss-120b"


@pytest.mark.asyncio
async def test_openrouter_client_uses_codex_proxy_url_and_token(monkeypatch):
    class RecordingClient(OpenRouterClient):
        def __init__(self):
            super().__init__()
            self.target_url = ""
            self.body: dict[str, object] = {}
            self.headers: dict[str, str] = {}

        async def _post_chat_completion(
            self,
            *,
            target_url: str,
            headers: dict[str, str],
            body: dict[str, object],
        ) -> httpx.Response:
            self.target_url = target_url
            self.headers = headers
            self.body = body
            request = httpx.Request("POST", target_url)
            return httpx.Response(
                status_code=200,
                request=request,
                json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
            )

    monkeypatch.setenv("HWPX_CODEX_PROXY_ACCESS_TOKEN", "proxy-token")

    client = RecordingClient()
    payload = await client.chat_completions(
        model="gpt-5",
        provider="codex-proxy",
        proxy_url="http://127.0.0.1:5011",
        messages=[{"role": "user", "content": "hello"}],
        tools=None,
        tool_choice=None,
    )

    assert isinstance(payload, dict)
    choices = payload.get("choices")
    assert isinstance(choices, list) and choices
    first_choice = choices[0]
    assert isinstance(first_choice, dict)
    message = first_choice.get("message")
    assert isinstance(message, dict)
    assert message.get("content") == "ok"
    assert client.target_url == "http://127.0.0.1:5011/chat/completions"
    assert client.headers["Authorization"] == "Bearer proxy-token"
    assert client.body["model"] == "gpt-5"


@pytest.mark.asyncio
async def test_openrouter_client_adds_quota_hint_when_no_fallback_available(
    monkeypatch,
):
    class SequenceClient(OpenRouterClient):
        def __init__(self, responses: list[httpx.Response]):
            super().__init__()
            self._responses = responses

        async def _post_chat_completion(
            self,
            *,
            target_url: str,
            headers: dict[str, str],
            body: dict[str, object],
        ) -> httpx.Response:
            _ = (target_url, headers, body)
            return self._responses.pop(0)

    monkeypatch.setenv("OPENAI_OAUTH_TOKEN", "oauth-only-token")
    monkeypatch.delenv("CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(
        status_code=429,
        request=request,
        text=json.dumps(
            {"error": {"type": "insufficient_quota", "message": "quota exhausted"}}
        ),
    )

    client = SequenceClient([response])

    with pytest.raises(LlmRequestError) as exc_info:
        await client.chat_completions(
            model=DEFAULT_MODEL,
            provider="openai",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            tool_choice=None,
            proxy_url=None,
        )

    error = exc_info.value
    assert error.status_code == 429
    assert "quota_hint" in str(error)
    assert "attempted_auth=openai-oauth" in str(error)


@pytest.mark.asyncio
async def test_openrouter_client_does_not_fallback_on_rate_limit_429(monkeypatch):
    class SequenceClient(OpenRouterClient):
        def __init__(self, responses: list[httpx.Response]):
            super().__init__(api_key="api-token")
            self._responses = responses
            self.calls = 0

        async def _post_chat_completion(
            self,
            *,
            target_url: str,
            headers: dict[str, str],
            body: dict[str, object],
        ) -> httpx.Response:
            _ = (target_url, headers, body)
            self.calls += 1
            return self._responses.pop(0)

    monkeypatch.setenv("OPENAI_OAUTH_TOKEN", "oauth-token")
    monkeypatch.delenv("CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(
        status_code=429,
        request=request,
        json={"error": {"type": "rate_limit_reached", "message": "too many requests"}},
    )

    client = SequenceClient([response])

    with pytest.raises(LlmRequestError) as exc_info:
        await client.chat_completions(
            model=DEFAULT_MODEL,
            provider="openai",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            tool_choice=None,
            proxy_url=None,
        )

    error = exc_info.value
    assert error.status_code == 429
    assert "quota_hint" not in str(error)
    assert "attempted_auth=openai-oauth" in str(error)
    assert client.calls == 1


@pytest.mark.asyncio
async def test_openrouter_client_does_not_fallback_on_policy_403(monkeypatch):
    class SequenceClient(OpenRouterClient):
        def __init__(self, responses: list[httpx.Response]):
            super().__init__(api_key="api-token")
            self._responses = responses
            self.calls = 0

        async def _post_chat_completion(
            self,
            *,
            target_url: str,
            headers: dict[str, str],
            body: dict[str, object],
        ) -> httpx.Response:
            _ = (target_url, headers, body)
            self.calls += 1
            return self._responses.pop(0)

    monkeypatch.setenv("OPENAI_OAUTH_TOKEN", "oauth-token")
    monkeypatch.delenv("CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(
        status_code=403,
        request=request,
        json={"error": {"type": "policy_violation", "message": "blocked"}},
    )

    client = SequenceClient([response])

    with pytest.raises(LlmRequestError) as exc_info:
        await client.chat_completions(
            model=DEFAULT_MODEL,
            provider="openai",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            tool_choice=None,
            proxy_url=None,
        )

    error = exc_info.value
    assert error.status_code == 403
    assert "attempted_auth=openai-oauth" in str(error)
    assert client.calls == 1
