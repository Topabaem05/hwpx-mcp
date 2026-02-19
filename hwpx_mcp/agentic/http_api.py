from __future__ import annotations

import os
from dataclasses import dataclass

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .gateway import BackendServer
from .tool_only_agent import ToolOnlyAgent

DEFAULT_PROVIDER = os.getenv("HWPX_AGENT_PROVIDER", "cerebras/fp16")
DEFAULT_MODEL = os.getenv("HWPX_AGENT_MODEL", "openai/gpt-oss-120b")


@dataclass(slots=True)
class AgentRuntimeConfig:
    provider: str
    model: str
    api_key_present: bool


class AgentHttpSurface:
    def __init__(self, backend_server: BackendServer):
        self._agent = ToolOnlyAgent(backend_server)

    async def health(self, request: Request) -> JSONResponse:
        _ = request
        return JSONResponse(
            {
                "status": "ok",
                "surface": "agent-http",
                "defaults": {
                    "provider": DEFAULT_PROVIDER,
                    "model": DEFAULT_MODEL,
                },
            }
        )

    async def chat(self, request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                {"success": False, "error": "invalid_json"}, status_code=400
            )

        if not isinstance(payload, dict):
            return JSONResponse(
                {"success": False, "error": "invalid_payload"},
                status_code=400,
            )

        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return JSONResponse(
                {"success": False, "error": "message_required"},
                status_code=422,
            )

        raw_session_id = payload.get("session_id", "")
        session_id = raw_session_id if isinstance(raw_session_id, str) else ""
        runtime = _extract_runtime_config(payload)

        result = await self._agent.run(message=message, session_id=session_id)
        return JSONResponse(
            {
                **result,
                "runtime": {
                    "provider": runtime.provider,
                    "model": runtime.model,
                    "api_key_present": runtime.api_key_present,
                },
            }
        )


def _extract_runtime_config(payload: dict[object, object]) -> AgentRuntimeConfig:
    raw_runtime = payload.get("runtime")
    runtime = raw_runtime if isinstance(raw_runtime, dict) else {}

    raw_provider = runtime.get("provider")
    provider = raw_provider.strip() if isinstance(raw_provider, str) else ""

    raw_model = runtime.get("model")
    model = raw_model.strip() if isinstance(raw_model, str) else ""

    raw_api_key = runtime.get("api_key")
    api_key = raw_api_key.strip() if isinstance(raw_api_key, str) else ""

    return AgentRuntimeConfig(
        provider=provider or DEFAULT_PROVIDER,
        model=model or DEFAULT_MODEL,
        api_key_present=bool(api_key),
    )


def build_agent_http_routes(backend_server: BackendServer) -> list[Route]:
    surface = AgentHttpSurface(backend_server)
    return [
        Route("/agent/health", surface.health, methods=["GET"]),
        Route("/agent/chat", surface.chat, methods=["POST"]),
    ]
