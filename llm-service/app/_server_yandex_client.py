from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

import openai
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
            message=(
                "No LLM provider is configured. Set YANDEX_FOLDER_ID/YANDEX_API_KEY "
                "or DEEPSEEK_API_KEY in .env"
            ),
            code="NOT_CONFIGURED",
            status=500,
        )


class YandexClient:
    def __init__(self) -> None:
        self.config = get_config()
        if not self.config.has_any_provider:
            raise ConfigurationError()

        self._yandex_client: Optional[openai.OpenAI] = None
        if self.config.is_yandex_configured:
            self._yandex_client = openai.OpenAI(
                api_key=self.config.yandex_api_key,
                project=self.config.yandex_folder_id,
                base_url=self.config.yandex_base_url,
                timeout=self.config.model_timeout,
                max_retries=0,
            )

        self._deepseek_client: Optional[openai.OpenAI] = None
        if self.config.is_deepseek_configured:
            self._deepseek_client = openai.OpenAI(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url,
                timeout=self.config.model_timeout,
                max_retries=0,
            )

        self._model_manager = get_model_manager()
        self._queue = get_queue()

    def _is_deepseek_model(self, model_id: str) -> bool:
        return model_id == self.config.deepseek_model or model_id.startswith("deepseek-")

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

    def _provider_for_model(self, model_id: str) -> str:
        return "deepseek" if self._is_deepseek_model(model_id) else "yandex"

    def _client_for_model(self, model_id: str) -> tuple[openai.OpenAI, str, str]:
        provider = self._provider_for_model(model_id)
        if provider == "deepseek":
            if self._deepseek_client is None:
                raise ModelUnavailableError(model_id)
            return self._deepseek_client, provider, model_id

        if self._yandex_client is None:
            raise ModelUnavailableError(model_id)
        full_model_id = self._model_manager.get_full_model_id(model_id=model_id)
        return self._yandex_client, provider, full_model_id

    def _extract_text(self, response: Any) -> str:
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            if content:
                return str(content)

        raise YandexLLMError(
            message="LLM response does not contain text output",
            code="EMPTY_RESPONSE",
            status=502,
        )

    def _usage_value(self, usage: Any, *keys: str) -> int:
        if usage is None:
            return 0
        for key in keys:
            value = None
            if isinstance(usage, dict):
                value = usage.get(key)
            else:
                value = getattr(usage, key, None)
            if isinstance(value, (int, float)):
                return int(value)
        return 0

    def _extract_usage(self, response: Any) -> Dict[str, int]:
        usage = getattr(response, "usage", None)
        prompt_tokens = self._usage_value(usage, "prompt_tokens", "input_tokens")
        completion_tokens = self._usage_value(
            usage, "completion_tokens", "output_tokens"
        )
        total_tokens = self._usage_value(usage, "total_tokens")
        if total_tokens <= 0:
            total_tokens = prompt_tokens + completion_tokens

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    async def _mark_provider_degraded(self, provider: str, model: str, reason: str) -> None:
        if provider == "yandex":
            await self._model_manager.mark_unavailable(model, reason=reason)

    async def _mark_provider_rate_limited(self, provider: str, model: str) -> None:
        if provider == "yandex":
            await self._model_manager.mark_rate_limited(model)

    def _can_fallback_to_deepseek(self, provider: str, current_model: str) -> bool:
        return (
            provider == "yandex"
            and self._deepseek_client is not None
            and current_model != self.config.deepseek_model
        )

    async def _chat_once(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str, Any]:
        client, provider, api_model = self._client_for_model(model)
        response = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model=api_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )
        return model, provider, response

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

        acquired = await self._queue.acquire(priority)
        if not acquired:
            raise YandexLLMError(
                message="Request queue timeout - too many pending requests",
                code="QUEUE_TIMEOUT",
                status=503,
            )

        try:
            logger.info(
                "llm_request_started",
                extra={"request_id": request_id, "model": model, "metadata": metadata or {}},
            )
            primary_provider = self._provider_for_model(model)

            try:
                resolved_model, provider, response = await self._chat_once(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.APIStatusError) as e:
                if isinstance(e, openai.RateLimitError):
                    await self._mark_provider_rate_limited(primary_provider, model)
                elif isinstance(e, openai.APIStatusError) and e.status_code == 429:
                    await self._mark_provider_rate_limited(primary_provider, model)
                else:
                    await self._mark_provider_degraded(primary_provider, model, reason=type(e).__name__)

                if not self._can_fallback_to_deepseek(primary_provider, model):
                    raise

                logger.warning(
                    "provider_fallback_started",
                    extra={
                        "request_id": request_id,
                        "from_provider": "yandex",
                        "to_provider": "deepseek",
                        "reason": type(e).__name__,
                    },
                )
                resolved_model, provider, response = await self._chat_once(
                    messages=messages,
                    model=self.config.deepseek_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            text = self._extract_text(response)
            usage_info = self._extract_usage(response)

            logger.info(
                "llm_request_completed",
                extra={
                    "request_id": request_id,
                    "model": resolved_model,
                    "provider": provider,
                    "duration_ms": round(elapsed_ms, 1),
                    "tokens_used": usage_info["total_tokens"],
                },
            )

            return {
                "request_id": request_id,
                "model": resolved_model,
                "text": text,
                "usage": {
                    "prompt_tokens": usage_info["prompt_tokens"],
                    "completion_tokens": usage_info["completion_tokens"],
                    "total_tokens": usage_info["total_tokens"],
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        except openai.RateLimitError:
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
                message=f"Connection to LLM API failed: {e}",
                code="CONNECTION_ERROR",
                status=502,
            )

        except openai.APITimeoutError:
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
                message=f"LLM API request timed out after {self.config.model_timeout}s",
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
                message=f"LLM API error ({e.status_code}): {e}",
                code="API_ERROR",
                status=e.status_code,
            )

        except YandexLLMError:
            raise

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

        acquired = await self._queue.acquire(priority)
        if not acquired:
            raise YandexLLMError(
                message="Request queue timeout - too many pending requests",
                code="QUEUE_TIMEOUT",
                status=503,
            )

        try:
            logger.info(
                "llm_stream_started",
                extra={"request_id": request_id, "model": model},
            )
            primary_provider = self._provider_for_model(model)
            completed_model = model

            async def stream_from_model(selected_model: str) -> AsyncIterator[str]:
                client, provider, api_model = self._client_for_model(selected_model)
                stream = client.chat.completions.create(
                    model=api_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for event in stream:
                    if event.choices and event.choices[0].delta and event.choices[0].delta.content:
                        yield event.choices[0].delta.content
                logger.info(
                    "llm_stream_provider_completed",
                    extra={
                        "request_id": request_id,
                        "model": selected_model,
                        "provider": provider,
                    },
                )

            try:
                async for chunk in stream_from_model(model):
                    yield chunk
            except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.APIStatusError) as e:
                await self._mark_provider_degraded(primary_provider, model, reason=type(e).__name__)
                if not self._can_fallback_to_deepseek(primary_provider, model):
                    raise

                logger.warning(
                    "stream_provider_fallback_started",
                    extra={
                        "request_id": request_id,
                        "from_provider": "yandex",
                        "to_provider": "deepseek",
                        "reason": type(e).__name__,
                    },
                )
                async for chunk in stream_from_model(self.config.deepseek_model):
                    yield chunk
                completed_model = self.config.deepseek_model

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "llm_stream_completed",
                extra={
                    "request_id": request_id,
                    "model": completed_model,
                    "duration_ms": round(elapsed_ms, 1),
                },
            )

        except openai.RateLimitError:
            await self._model_manager.mark_rate_limited(model)
            raise RateLimitError(model)

        except openai.APIConnectionError as e:
            await self._model_manager.mark_unavailable(model, reason="connection_error")
            raise YandexLLMError(
                message=f"Connection to LLM API failed: {e}",
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
                message=f"LLM API error ({e.status_code}): {e}",
                code="API_ERROR",
                status=e.status_code,
            )

        except YandexLLMError:
            raise

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
        """Checks model availability with a minimal request."""
        client, _provider, api_model = self._client_for_model(model_id=model_id)
        try:
            await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model=api_model,
                    messages=[{"role": "user", "content": "ping"}],
                    temperature=0.0,
                    max_tokens=1,
                )
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
