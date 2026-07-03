# Архитектура LLM Service

## Обзор

`llm-service` — это FastAPI-шлюз к моделям Yandex AI Studio (Alice AI LLM, YandexGPT, YandexGPT Lite), использующий OpenAI-совместимый протокол. Сервис предназначен для работы в составе более крупной системы (Фабрика гипотез), обслуживая множество контейнеров-потребителей.

## Схема компонентов

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              llm-service (FastAPI)                │   │
│  │                                                   │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────┐  │   │
│  │  │ Router   │  │  Middleware   │  │  Models   │  │   │
│  │  │ /api/v1  │──│  ErrorHandler │──│  Pydantic │  │   │
│  │  └────┬─────┘  └──────────────┘  └───────────┘  │   │
│  │       │                                           │   │
│  │  ┌────▼──────────────────────────────────────┐   │   │
│  │  │          YandexClient                      │   │   │
│  │  │  ┌──────────────┐  ┌───────────────────┐  │   │   │
│  │  │  │ openai sdk   │  │  RequestQueue     │  │   │   │
│  │  │  │ (compat)     │  │  (asyncio.Sem)    │  │   │   │
│  │  │  └──────┬───────┘  └───────────────────┘  │   │   │
│  │  │         │                                  │   │   │
│  │  │  ┌──────▼──────────────────────────────┐  │   │   │
│  │  │  │       ModelManager                   │  │   │   │
│  │  │  │  - model registry                    │  │   │   │
│  │  │  │  - status tracking                   │  │   │   │
│  │  │  │  - periodic health checks            │  │   │   │
│  │  │  │  - rate-limit detection              │  │   │   │
│  │  │  └──────────────────────────────────────┘  │   │   │
│  │  └────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
│              Yandex AI Studio API                        │
│         (ai.api.cloud.yandex.net/v1)                     │
└─────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Router (`router.py`)
Точки входа REST API:
- `GET  /api/v1/health` — состояние сервиса
- `GET  /api/v1/models` — список моделей с фильтрацией по статусу
- `GET  /api/v1/queue/status` — статус очереди и активных запросов
- `POST /api/v1/chat` — синхронный chat completion
- `POST /api/v1/chat/stream` — streaming chat completion (SSE)

### 2. YandexClient (`yandex_client.py`)
Обёртка над `openai.OpenAI`, сконфигурированная на эндпоинт Yandex AI Studio.

Особенности:
- Формат model_id: `gpt://{FOLDER_ID}/{model_name}`
- Использует `client.responses.create()` (Yandex-совместимый метод)
- Все вызовы обёрнуты в `asyncio.to_thread` для неблокирующего I/O
- Категоризация ошибок: `RateLimitError` (429), `APIConnectionError` (502), `APITimeoutError` (504), `APIStatusError`, прочие

### 3. RequestQueue (`queue.py`)
Ограничение конкурентности на основе `asyncio.Semaphore`.

- **MAX_CONCURRENT_REQUESTS** = 10 (соответствует квоте Yandex на синхронную генерацию)
- Ожидание в очереди: до `REQUEST_TIMEOUT_SECONDS` (по умолчанию 300 с)
- Приоритеты: `0` (обычный) — `10` (наивысший), реализованы через FIFO + semaphore

### 4. ModelManager (`model_manager.py`)
Реестр моделей с отслеживанием состояния.

Состояния модели:
| Статус | Описание |
|--------|----------|
| `available` | Модель подтверждена рабочей |
| `unavailable` | Модель недоступна (ошибка соединения, 5xx) |
| `rate_limited` | Превышен лимит запросов (временная блокировка) |
| `unknown` | Начальное состояние, проверка не проводилась |

- Автоматическое восстановление из `rate_limited` по истечении таймаута (60 с)
- Периодический health-check всех моделей (интервал: `HEALTH_CHECK_INTERVAL`)
- Fallback: если запрошенная модель недоступна — автоматический выбор первой доступной

### 5. Middleware (`middleware.py`)
Централизованный перехват ошибок:
- `YandexLLMError` → соответствующий HTTP-статус + JSON с кодом
- Неизвестные исключения → 500 + generic message
- Логирование каждого запроса: метод, путь, статус, длительность

### 6. Config (`config.py`)
Загрузка параметров из `.env` через `python-dotenv`. Паттерн singleton.

### 7. Logger (`logger.py`)
Структурированное логирование в JSON (по умолчанию) или plain-text.
Дополнительные поля в логах: `model`, `request_id`, `duration_ms`, `tokens_used`.

## Поток запроса

```
1. POST /api/v1/chat
2. Router.validate(ChatRequest)
3. YandexClient.chat()
   ├── resolve_model() — проверка доступности, fallback
   ├── queue.acquire() — захват слота (semaphore)
   ├── client.responses.create() — вызов Yandex API
   │   ├── Успех → mark_available(), возврат результата
   │   ├── 429  → mark_rate_limited(), raise RateLimitError
   │   ├── 5xx  → mark_unavailable(), raise YandexLLMError
   │   └── ...  → логирование и raise
   └── queue.release() — освобождение слота (finally)
4. Middleware → перехват ошибок, логирование
5. JSON-ответ клиенту
```

## Квоты Yandex AI Studio (учтённые ограничения)

| Параметр | Квота | Переменная |
|----------|-------|------------|
| Одновременных синхронных генераций | 10 | `MAX_CONCURRENT_REQUESTS=10` |
| Асинхронных запросов/сек | 10 | Не используется (только sync) |
| Асинхронных запросов/час | 5 000 | Не используется (только sync) |
| Токенизация/сек | 50 | Не регламентируется на уровне клиента |

## Запуск

```bash
# Локально
cd llm-service
cp .env.example .env  # заполнить YANDEX_FOLDER_ID и YANDEX_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker
docker compose up -d --build
```

## Расширяемость

- **Новые модели**: добавить в `DEFAULT_MODELS` в `main.py` или вызвать `model_manager.register_model()` динамически.
- **Поддержка async API Yandex**: добавить отдельный метод в `YandexClient` с использованием `client.responses.create(stream=False, ...)` и polling статуса.
- **Несколько проектов (FOLDER_ID)**: создать несколько экземпляров `YandexClient` с разными `config`.
- **Метрики Prometheus**: добавить эндпоинт `/metrics` с метриками очереди, латентности, ошибок.
