"""Schemas for local LLM inspection and chat responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LocalLLMHistoryMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="Conversation role used to reconstruct chat prompts.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Plain-text content for a previous chat turn.",
    )


class LocalLLMChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Latest user message that should be answered by the local model.",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Optional system instruction injected ahead of the user message.",
    )
    history: list[LocalLLMHistoryMessage] = Field(
        default_factory=list,
        description="Optional prior messages used to rebuild a multi-turn prompt.",
    )


class LocalLLMChatResponse(BaseModel):
    answer: str = Field(
        ...,
        description="Generated answer from the local model, or an empty string when loading fails.",
    )
    backend: str = Field(..., description="Resolved runtime backend used for the request.")
    provider: str = Field(
        ...,
        description="Resolved execution provider, such as cpu or directml.",
    )
    model_path: str = Field(..., description="Resolved local model path inspected by the service.")
    device: str = Field(..., description="Resolved device target for the active backend.")
    gpu_path_active: bool = Field(
        ...,
        description="True only when the loaded runtime is actually using a GPU execution path.",
    )
    load_success: bool = Field(
        ...,
        description="Whether the model runtime was initialized successfully for this request.",
    )
    model_format: str = Field(..., description="Detected model artifact format.")
    fallback_required: bool = Field(
        ...,
        description="Whether the service had to use a fallback runtime path instead of DirectML-ready ORT GenAI.",
    )
    directml_viable: bool = Field(
        ...,
        description="Whether the inspected model folder is compatible with the preferred DirectML path.",
    )
    load_error: str | None = Field(
        default=None,
        description="Initialization or generation error when the model could not be used.",
    )


class LocalLLMStatusResponse(BaseModel):
    status: str = Field(..., description="High-level runtime state reported by the service.")
    enabled: bool = Field(..., description="Whether local inference is enabled by configuration.")
    backend: str = Field(..., description="Resolved backend for the inspected model.")
    provider: str = Field(..., description="Resolved execution provider for the backend.")
    model_path: str = Field(..., description="Resolved model path from configuration.")
    device: str = Field(..., description="Resolved device target from configuration and runtime.")
    gpu_path_active: bool = Field(
        ...,
        description="True only when the service has confirmed a real GPU execution path.",
    )
    load_attempted: bool = Field(
        ...,
        description="Whether lazy initialization has already been attempted in this process.",
    )
    load_success: bool = Field(
        ...,
        description="Whether the service has loaded the active runtime successfully.",
    )
    model_format: str = Field(..., description="Detected model artifact format.")
    has_genai_config: bool = Field(
        ...,
        description="Whether genai_config.json was found in the model folder.",
    )
    onnx_files: list[str] = Field(
        default_factory=list,
        description="Discovered ONNX artifacts under the configured model path.",
    )
    safetensors_files: list[str] = Field(
        default_factory=list,
        description="Discovered safetensors artifacts under the configured model path.",
    )
    gguf_files: list[str] = Field(
        default_factory=list,
        description="Discovered GGUF artifacts under the configured model path.",
    )
    directml_viable: bool = Field(
        ...,
        description="Whether the current model folder is compatible with the preferred DirectML path.",
    )
    fallback_required: bool = Field(
        ...,
        description="Whether the resolved runtime is a fallback path instead of DirectML-ready ORT GenAI.",
    )
    directml_blocker: str | None = Field(
        default=None,
        description="Why DirectML is not active or not viable for the current model artifacts.",
    )
    load_error: str | None = Field(
        default=None,
        description="Latest load or generation failure captured by the service.",
    )
    model_size_bytes: int = Field(
        default=0,
        description="Approximate total model size reported by checkpoint metadata or file sizes.",
    )
