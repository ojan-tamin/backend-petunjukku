"""Routes for local LLM inspection and chat inference."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_local_llm_service
from app.schemas.local_llm import (
    LocalLLMChatRequest,
    LocalLLMChatResponse,
    LocalLLMStatusResponse,
)
from app.services.local_llm_service import LocalLLMService

router = APIRouter(prefix="/local-llm", tags=["local-llm"])


@router.get("/status", response_model=LocalLLMStatusResponse)
def local_llm_status(
    service: LocalLLMService = Depends(get_local_llm_service),
) -> LocalLLMStatusResponse:
    return LocalLLMStatusResponse.model_validate(service.get_status())


@router.post("/chat", response_model=LocalLLMChatResponse)
def local_llm_chat(
    payload: LocalLLMChatRequest,
    service: LocalLLMService = Depends(get_local_llm_service),
) -> LocalLLMChatResponse:
    return LocalLLMChatResponse.model_validate(
        service.generate_response(
            message=payload.message,
            system_prompt=payload.system_prompt,
            history=[message.model_dump() for message in payload.history],
        )
    )
