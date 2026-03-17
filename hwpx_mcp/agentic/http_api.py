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
from .openrouter_agent import LocalModelError
from .openrouter_agent import LocalModelNotReadyError
from .openrouter_agent import OpenRouterToolAgent


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class AuthRequest(BaseModel):
    openai_api_key: str | None = None
    openai_oauth_token: str | None = None
    codex_oauth_token: str | None = None
    openrouter_api_key: str | None = None
    codex_proxy_access_token: str | None = None


class ConfigRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    proxy_url: str | None = None


class LocalModelDownloadRequest(BaseModel):
    force: bool = False


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
        auth = self._agent.auth_status()
        return {
            "status": "ok",
            "surface": "agent-http",
            "defaults": {
                "provider": DEFAULT_PROVIDER,
                "model": DEFAULT_MODEL,
            },
            "runtime": self._agent.runtime_config(),
            "auth": auth,
            "local_model": self._agent.local_model_status(),
        }

    async def set_auth(self, payload: AuthRequest) -> dict[str, object]:
        self._agent.set_runtime_auth(
            openai_api_key=payload.openai_api_key,
            openai_oauth_token=payload.openai_oauth_token,
            codex_oauth_token=payload.codex_oauth_token,
            openrouter_api_key=payload.openrouter_api_key,
            codex_proxy_access_token=payload.codex_proxy_access_token,
        )
        return {
            "success": True,
            "runtime": self._agent.runtime_config(),
            "auth": self._agent.auth_status(),
        }

    async def set_config(self, payload: ConfigRequest) -> dict[str, object]:
        runtime = self._agent.set_runtime_config(
            provider=payload.provider,
            model=payload.model,
            proxy_url=payload.proxy_url,
        )
        return {
            "success": True,
            "runtime": runtime,
            "auth": self._agent.auth_status(),
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
        except LocalModelNotReadyError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(
                status_code=500, detail=f"agent_runtime_error: {error}"
            ) from error
        return {
            **result,
            "runtime": self._agent.runtime_config(),
        }

    async def local_model_status(self) -> dict[str, object]:
        return self._agent.local_model_status()

    async def download_local_model(
        self, payload: LocalModelDownloadRequest
    ) -> dict[str, object]:
        try:
            return await self._agent.download_local_model(force=payload.force)
        except LocalModelError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error


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

    @router.post("/agent/auth")
    async def agent_auth(payload: AuthRequest) -> dict[str, object]:
        return await surface.set_auth(payload)

    @router.post("/agent/config")
    async def agent_config(payload: ConfigRequest) -> dict[str, object]:
        return await surface.set_config(payload)

    @router.post("/agent/chat")
    async def agent_chat(payload: ChatRequest) -> dict[str, object]:
        return await surface.chat(payload)

    @router.get("/agent/local-model/status")
    async def agent_local_model_status() -> dict[str, object]:
        return await surface.local_model_status()

    @router.post("/agent/local-model/download")
    async def agent_local_model_download(
        payload: LocalModelDownloadRequest,
    ) -> dict[str, object]:
        return await surface.download_local_model(payload)

    return router
