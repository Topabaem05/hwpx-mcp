from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel

from .gateway import BackendServer
from .openrouter_agent import DEFAULT_MODEL
from .openrouter_agent import DEFAULT_PROVIDER
from .openrouter_agent import AgentAuthError
from .openrouter_agent import LlmRequestError
from .openrouter_agent import OpenRouterToolAgent


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class AgentHttpSurface:
    def __init__(
        self,
        backend_server: BackendServer,
        agent_factory: Callable[[BackendServer], OpenRouterToolAgent] | None = None,
    ):
        self._agent = (
            agent_factory(backend_server)
            if agent_factory is not None
            else OpenRouterToolAgent(backend_server)
        )

    async def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "surface": "agent-http",
            "defaults": {
                "provider": DEFAULT_PROVIDER,
                "model": DEFAULT_MODEL,
            },
        }

    async def chat(self, payload: ChatRequest) -> dict[str, object]:
        message = payload.message.strip()
        if not message:
            raise HTTPException(status_code=422, detail="message_required")

        session_id = payload.session_id.strip()
        try:
            result = await self._agent.run(message=message, session_id=session_id)
        except AgentAuthError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except LlmRequestError as error:
            status_code = 502
            if error.status_code in (400, 401, 403, 404, 429):
                status_code = 400
            raise HTTPException(status_code=status_code, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(
                status_code=500, detail=f"agent_runtime_error: {error}"
            ) from error
        return {
            **result,
            "runtime": {
                "provider": DEFAULT_PROVIDER,
                "model": DEFAULT_MODEL,
            },
        }


def build_agent_http_router(
    backend_server: BackendServer,
    *,
    agent_factory: Callable[[BackendServer], OpenRouterToolAgent] | None = None,
) -> APIRouter:
    surface = AgentHttpSurface(backend_server, agent_factory=agent_factory)
    router = APIRouter()

    @router.get("/agent/health")
    async def agent_health() -> dict[str, object]:
        return await surface.health()

    @router.post("/agent/chat")
    async def agent_chat(payload: ChatRequest) -> dict[str, object]:
        return await surface.chat(payload)

    return router
