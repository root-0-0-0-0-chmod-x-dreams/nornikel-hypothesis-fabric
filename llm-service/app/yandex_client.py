from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

import openai
from openai.types.responses import Response

from .config import get_config
from .logger import get_logger
from .model_manager import get_model_manager
from .queue import get_queue

logger = get_logger()


class YandexLLMError(Exception):
    def __init__(self, message: str, code: str = "LLM_ERROR", status: int = 500):
        self.code = code
        self.status = status
        super().__init__(message)


class ModelUnavailableError(YandexLLMError):
    def __init__(self, model_id: str):
        super().__init__(
            message=f"Model '{model_id}' is currently unavailable",
            code="MODEL_UNAVAILABLE",
            status=503,
        )


class RateLimitError(YandexLLMError):
    def __init__(self, model_id: str, retry_after: float = 60.0):
        super().__init__(
            message=f"Rate limit exceeded for model '{model_id}'. Retry after {retry_after:.0f}s",
            code="RATE_LIMITED",
            status=429,
        )


class ConfigurationError(YandexLLMError):
    def __init__(self):
        super().__init__(
            message="YANDEX_FOLDER_ID and YANDEX_API_KEY must be set in .env",
            code="NOT_CONFIGURED",
            status=500,
        )


class YandexClient:
    def __init__(self) -> None:
        self.config = get_config()
        if not self.config.is_configured:
            raise ConfigurationError()

        self._client = openai.OpenAI(
            api_key=self.config.yandex_api_key,
            project=self.config.yandex_folder_id,
            base_url=self.config.yandex_base_url,
            timeout=self.config.model_timeout,
            max_retries=0,
        )
        self._model_manager = get_model_manager()
        self._queue = get_queue()

    def _resolve_model(self, model_id: Optional[str] = None) -> str:
        resolved = model_id or self.config.default_model
        if not self._model_manager.is_available(resolved):
            available = self._model_manager.get_available_models()
            if available:
                resolved = available[0].model_id
                logger.info(
                    "fallback_model",
                    extra={"requested": model_id, "fallback": resolved},
                )
            else:
                raise ModelUnavailableError(resolved)
        return resolved

    async def chat(
        self,
        messages: list[dict],
        model_id: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 1500,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        model = self._resolve_model(model_id)
        full_model_id = self._model_manager.get_full_model_id(model_id=model)

        acquired = await self._queue.acquire(priority)
        if not acquired:
            raise YandexLLMError(
                message="Request queue timeout — too many pending requests",
                code="QUEUE_TIMEOUT",
                status=503,
            )

        try:
            logger.info(
                "llm_request_started",
                extra={"request_id": request_id, "model": model},
            )

            response: Response = await asyncio.to_thread(
                lambda: self._client.responses.create(
                    model=full_model_id,
                    input=messages,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            text = response.output[0].content[0].text
            usage_info = response.usage

            logger.info(
                "llm_request_completed",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "duration_ms": round(elapsed_ms, 1),
                    "tokens_used": usage_info.total_tokens if usage_info else 0,
                },
            )

            return {
                "request_id": request_id,
                "model": model,
                "text": text,
                "usage": {
                    "prompt_tokens": usage_info.prompt_tokens if usage_info else 0,
                    "completion_tokens": usage_info.completion_tokens if usage_info else 0,
                    "total_tokens": usage_info.total_tokens if usage_info else 0,
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        except openai.RateLimitError as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.warning(
                "llm_rate_limited",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "duration_ms": round(elapsed_ms, 1),
                },
            )
            await self._model_manager.mark_rate_limited(model)
            raise RateLimitError(model)

        except openai.APIConnectionError as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "llm_connection_error",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "duration_ms": round(elapsed_ms, 1),
                    "reason": str(e)[:200],
                },
            )
            await self._model_manager.mark_unavailable(model, reason="connection_error")
            raise YandexLLMError(
                message=f"Connection to Yandex API failed: {e}",
                code="CONNECTION_ERROR",
                status=502,
            )

        except openai.APITimeoutError as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "llm_timeout",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "duration_ms": round(elapsed_ms, 1),
                },
            )
            raise YandexLLMError(
                message=f"Yandex API request timed out after {self.config.model_timeout}s",
                code="TIMEOUT",
                status=504,
            )

        except openai.APIStatusError as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "llm_api_error",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "status_code": e.status_code,
                    "duration_ms": round(elapsed_ms, 1),
                    "reason": str(e)[:200],
                },
            )
            if e.status_code == 429:
                await self._model_manager.mark_rate_limited(model)
                raise RateLimitError(model)
            if e.status_code >= 500:
                await self._model_manager.mark_unavailable(
                    model, reason=f"api_error_{e.status_code}"
                )
            raise YandexLLMError(
                message=f"Yandex API error ({e.status_code}): {e}",
                code="API_ERROR",
                status=e.status_code,
            )

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.exception(
                "llm_unexpected_error",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "duration_ms": round(elapsed_ms, 1),
                },
            )
            raise YandexLLMError(
                message=f"Unexpected error: {e}",
                code="INTERNAL_ERROR",
                status=500,
            )

        finally:
            self._queue.release()

    async def chat_stream(
        self,
        messages: list[dict],
        model_id: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 1500,
        priority: int = 0,
    ) -> AsyncIterator[str]:
        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        model = self._resolve_model(model_id)
        full_model_id = self._model_manager.get_full_model_id(model_id=model)

        acquired = await self._queue.acquire(priority)
        if not acquired:
            raise YandexLLMError(
                message="Request queue timeout — too many pending requests",
                code="QUEUE_TIMEOUT",
                status=503,
            )

        try:
            logger.info(
                "llm_stream_started",
                extra={"request_id": request_id, "model": model},
            )

            stream = self._client.responses.create(
                model=full_model_id,
                input=messages,
                temperature=temperature,
                max_output_tokens=max_tokens,
                stream=True,
            )

            for event in stream:
                if hasattr(event, "delta") and event.delta:
                    yield event.delta

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "llm_stream_completed",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "duration_ms": round(elapsed_ms, 1),
                },
            )

        except openai.RateLimitError:
            await self._model_manager.mark_rate_limited(model)
            raise RateLimitError(model)

        except openai.APIConnectionError as e:
            await self._model_manager.mark_unavailable(model, reason="connection_error")
            raise YandexLLMError(
                message=f"Connection to Yandex API failed: {e}",
                code="CONNECTION_ERROR",
                status=502,
            )

        except openai.APIStatusError as e:
            if e.status_code == 429:
                await self._model_manager.mark_rate_limited(model)
                raise RateLimitError(model)
            if e.status_code >= 500:
                await self._model_manager.mark_unavailable(
                    model, reason=f"api_error_{e.status_code}"
                )
            raise YandexLLMError(
                message=f"Yandex API error ({e.status_code}): {e}",
                code="API_ERROR",
                status=e.status_code,
            )

        except Exception as e:
            logger.exception(
                "llm_stream_error",
                extra={"request_id": request_id, "model": model},
            )
            raise YandexLLMError(
                message=f"Unexpected streaming error: {e}",
                code="INTERNAL_ERROR",
                status=500,
            )

        finally:
            self._queue.release()

    async def probe_model(self, model_id: str) -> bool:
        """Проверяет доступность модели минимальным запросом (1 токен)."""
        full_model_id = self._model_manager.get_full_model_id(model_id=model_id)
        try:
            self._client.responses.create(
                model=full_model_id,
                input="ping",
                temperature=0.0,
                max_output_tokens=1,
            )
            return True
        except Exception:
            return False


_client: Optional[YandexClient] = None


def get_client() -> YandexClient:
    global _client
    if _client is None:
        _client = YandexClient()
    return _client
