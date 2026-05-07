from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    status_code = 503
    public_detail = "AI service is unavailable"


class LLMConfigurationError(LLMError):
    public_detail = "LLM configuration is incomplete"


class LLMUpstreamError(LLMError):
    public_detail = "LLM provider request failed"


class LLMResponseError(LLMError):
    public_detail = "LLM provider returned an invalid response"


class LLMClient:
    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.provider = str(provider or settings.llm_provider or "openrouter").strip().lower()
        self.model = str(model or settings.llm_model or "").strip()
        self.api_key = str(api_key or settings.llm_api_key or "").strip()
        self.base_url = str(base_url or settings.llm_base_url or "").strip().rstrip("/")
        self.timeout_seconds = float(timeout_seconds or settings.llm_timeout_seconds or 60.0)
        self.max_retries = int(max_retries if max_retries is not None else settings.llm_max_retries)

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        if self.provider != "openrouter":
            raise LLMConfigurationError(f"Unsupported LLM provider: {self.provider}")
        if not self.api_key:
            raise LLMConfigurationError("LLM_API_KEY or OPENROUTER_API_KEY is not set")
        if not self.model:
            raise LLMConfigurationError("LLM_MODEL is not set")
        if not self.base_url:
            raise LLMConfigurationError("LLM_BASE_URL is not set")

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": float(temperature if temperature is not None else settings.llm_temperature),
        }
        token_limit = int(max_tokens if max_tokens is not None else settings.llm_max_tokens)
        if token_limit > 0:
            body["max_tokens"] = token_limit
        if response_format == "json_object" and "gemini" not in self.model.lower():
            body["response_format"] = {"type": "json_object"}
        if extra_body:
            body.update(extra_body)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": str(settings.llm_http_referer or "https://petunjukku.id"),
            "X-Title": str(settings.app_name or "Petunjukku Backend")[:120],
        }

        last_error: Exception | None = None
        for attempt in range(max(0, self.max_retries) + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=body)
                if response.status_code == 200:
                    return self._extract_content(response.json())
                if self._should_retry(response.status_code) and attempt < self.max_retries:
                    delay = 0.35 * (2**attempt) + random.uniform(0, 0.25)
                    logger.warning(
                        "Retrying LLM request status=%s attempt=%s/%s delay=%.2fs",
                        response.status_code,
                        attempt + 1,
                        self.max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                logger.warning("LLM upstream error status=%s body=%s", response.status_code, response.text[:300])
                raise LLMUpstreamError(f"LLM upstream error: {response.status_code}")
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2**attempt))
                    continue
                raise LLMUpstreamError("LLM request timed out") from exc
            except httpx.RequestError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(0.35 * (2**attempt))
                    continue
                raise LLMUpstreamError("LLM request failed") from exc

        raise LLMUpstreamError("LLM request failed") from last_error

    @staticmethod
    def _should_retry(status_code: int) -> bool:
        return status_code == 429 or status_code >= 500

    @staticmethod
    def _extract_content(data: Any) -> str:
        if not isinstance(data, dict):
            raise LLMResponseError("LLM response is not a JSON object")
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseError("LLM response has no choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise LLMResponseError("LLM response choice is invalid")
        message = first.get("message")
        if not isinstance(message, dict):
            raise LLMResponseError("LLM response has no message")
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts).strip()
        raise LLMResponseError("LLM response content is invalid")
