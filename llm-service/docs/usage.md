# LLM Service — Руководство по использованию

## Быстрый старт

### 1. Настройка окружения

```bash
cd llm-service
cp .env.example .env
```

Отредактируйте `.env`, указав реальные значения (Yandex как primary, DeepSeek как fallback):

```env
YANDEX_FOLDER_ID=b1g**********
YANDEX_API_KEY=AQVN**********
DEEPSEEK_API_KEY=sk-**********
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 2. Запуск через Docker (рекомендуется)

```bash
docker compose up -d --build
```

Проверка:

```bash
curl http://localhost:8000/api/v1/health
```

### 3. Локальный запуск (для разработки)

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API

### Базовый URL

```
http://localhost:8000/api/v1
```

Swagger-документация доступна по адресу: `http://localhost:8000/docs`

### Эндпоинты

#### `GET /health`

Состояние сервиса.

```bash
curl http://localhost:8000/api/v1/health
```

Ответ:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 123.4,
  "models_count": 3,
  "yandex_configured": true,
  "deepseek_configured": true
}
```

#### `GET /models`

Список моделей и их статус.

```bash
# Все модели
curl http://localhost:8000/api/v1/models

# Только доступные
curl http://localhost:8000/api/v1/models?status=available
```

Ответ:
```json
[
  {
    "model_id": "aliceai-llm",
    "display_name": "Alice AI LLM",
    "status": "available",
    "max_tokens": 1500,
    "supports_streaming": true,
    "last_checked_at": "2026-07-03T18:00:00+00:00"
  }
]
```

#### `GET /queue/status`

Текущее состояние очереди запросов.

```bash
curl http://localhost:8000/api/v1/queue/status
```

Ответ:
```json
{
  "queue_size": 2,
  "active_requests": 3,
  "max_concurrent": 10,
  "models_available": ["aliceai-llm"],
  "models_unavailable": ["yandexgpt-lite"]
}
```

#### `POST /chat`

Отправить запрос к LLM.

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "aliceai-llm",
    "messages": [
      {"role": "user", "content": "Придумай 3 необычные идеи для стартапа в сфере путешествий."}
    ],
    "temperature": 0.8,
    "max_tokens": 1500,
    "priority": 0
  }'
```

Ответ:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "model": "aliceai-llm",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "1. ...\n2. ...\n3. ..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 200,
    "total_tokens": 215
  },
  "created_at": "2026-07-03T18:00:00+00:00"
}
```

#### `POST /chat/stream`

Потоковый ответ (Server-Sent Events).

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Расскажи про флотацию руды."}
    ],
    "temperature": 0.5,
    "max_tokens": 2000
  }'
```

### Параметры запроса `/chat`

| Поле | Тип | По умолчанию | Описание |
|------|-----|-------------|----------|
| `model` | string | `aliceai-llm` | ID модели (из `.env`) |
| `messages` | array | — | История диалога: `[{"role": "system|user|assistant", "content": "..."}]` |
| `temperature` | float | `0.8` | Креативность (0.0 — детерминированно, 2.0 — максимально) |
| `max_tokens` | int | `1500` | Максимальное число токенов в ответе |
| `stream` | bool | `false` | Потоковый режим (только для `/chat/stream`) |
| `priority` | int | `0` | Приоритет в очереди (0–10, 10 — наивысший) |

### Коды ошибок

| HTTP | Код | Описание |
|------|-----|----------|
| 429 | `RATE_LIMITED` | Превышен лимит запросов к модели |
| 500 | `NOT_CONFIGURED` | Не заданы параметры ни одного провайдера (`YANDEX_*` или `DEEPSEEK_API_KEY`) |
| 502 | `CONNECTION_ERROR` | Ошибка соединения с LLM API |
| 503 | `MODEL_UNAVAILABLE` | Запрошенная модель недоступна |
| 503 | `QUEUE_TIMEOUT` | Истекло время ожидания в очереди |
| 504 | `TIMEOUT` | Истекло время ожидания ответа от LLM API |

## Тонкие моменты

### 1. Ограничение конкурентности

Yandex AI Studio разрешает **не более 10 одновременных синхронных генераций**. Сервис использует `asyncio.Semaphore(10)` для соблюдения этого лимита. Все запросы сверх лимита становятся в очередь и ждут освобождения слота (до `REQUEST_TIMEOUT_SECONDS`).

### 2. Provider fallback (Yandex -> DeepSeek)

Если запрос к Yandex завершился ошибкой соединения, таймаутом, rate-limit или серверной ошибкой, сервис автоматически повторяет запрос на DeepSeek (`DEEPSEEK_MODEL`, по умолчанию `deepseek-v4-flash`) при наличии `DEEPSEEK_API_KEY`.

Если запрошенная модель недоступна по статусу health-check, сервис также переключается на первую доступную модель. Это поведение логируется с тегами `requested` и `fallback`.

### 3. Health-check моделей

При старте сервис проверяет доступность каждой зарегистрированной модели (отправляя запрос с `max_output_tokens=1`). Далее проверка повторяется каждые `HEALTH_CHECK_INTERVAL` секунд.

### 4. Rate-limit recovery

При получении HTTP 429 модель помечается как `rate_limited` на 60 секунд. По истечении этого времени она снова становится доступной для запросов.

### 5. Логирование

По умолчанию — JSON-логи в stdout. Каждое событие содержит `timestamp`, `level`, `message`, а также контекстные поля (`request_id`, `model`, `duration_ms`, `tokens_used`).

Пример:
```json
{"timestamp": "2026-07-03T18:00:00.123456+00:00", "level": "INFO", "logger": "llm_service", "message": "llm_request_completed", "model": "aliceai-llm", "request_id": "550e8400-...", "duration_ms": 2340.5, "tokens_used": 215}
```

### 6. Мультиконтейнерность

Сервис спроектирован как stateless-шлюз: все потребители (другие контейнеры) обращаются к нему по HTTP. Ограничение конкурентности (`MAX_CONCURRENT_REQUESTS`) действует глобально на все входящие запросы, эффективно реализуя централизованный throttle для Yandex API.
