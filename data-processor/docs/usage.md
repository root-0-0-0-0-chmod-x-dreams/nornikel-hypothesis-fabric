# Data Processor — Руководство по использованию

## Быстрый старт

### 1. Настройка

```bash
cd data-processor
cp .env.example .env      # конфигурация по умолчанию готова к работе
```

### 2. Запуск через Docker (рекомендуется)

```bash
docker compose up -d --build
```

Проверка:

```bash
curl http://localhost:8001/api/v1/health
```

### 3. Локальный запуск (для разработки)

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## API

Базовый URL: `http://localhost:8001/api/v1`

Swagger: `http://localhost:8001/docs`

### `GET /health`

```bash
curl http://localhost:8001/api/v1/health
```

```json
{"status": "ok", "version": "1.0.0", "uptime_seconds": 42.1}
```

### `POST /convert`

Конвертация одного файла. Тело — `multipart/form-data`, поле `file`.

```bash
curl -X POST http://localhost:8001/api/v1/convert \
  -F "file=@docs/report.pdf"
```

Ответ:

```json
{
  "success": true,
  "original_filename": "report.pdf",
  "file_type": "pdf",
  "markdown_content": "# Report Title\n\n## Section 1\n...",
  "images_extracted": 5,
  "errors": [],
  "warnings": [],
  "metadata": {"pages": 12}
}
```

### `POST /convert/batch`

Пакетная конвертация до **50 файлов** за раз. Тело — `multipart/form-data`, поле `files` (множественное).

```bash
curl -X POST http://localhost:8001/api/v1/convert/batch \
  -F "files=@report.pdf" \
  -F "files=@data.xlsx" \
  -F "files=@diagram.png" \
  -F "files=@notes.docx"
```

Ответ:

```json
{
  "total": 4,
  "succeeded": 3,
  "failed": 1,
  "results": [
    {
      "success": true,
      "original_filename": "report.pdf",
      "file_type": "pdf",
      "markdown_content": "...",
      "images_extracted": 5,
      "errors": [],
      "warnings": [],
      "metadata": {"pages": 12}
    }
  ]
}
```

### `GET /convert/{filename}/raw`

Получить ранее сконвертированный результат в виде сырого markdown.

```bash
curl http://localhost:8001/api/v1/convert/report/raw
```

## Поддерживаемые форматы

| Формат | Конвертер | Примечания |
|--------|-----------|------------|
| `.pdf` | docling → PyMuPDF (fallback) | Извлекаются текст и картинки |
| `.docx` | docx2md | Таблицы, картинки из `word/media/` |
| `.xlsx` | openpyxl + pandas | Все листы, таблицы markdown |
| `.xls` | xls2xlsx → как .xlsx | Автоконвертация в .xlsx |
| `.csv`, `.tsv` | pandas | Автоопределение разделителя |
| `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp` | Копирование в images/ | Markdown: `![](images/img_{uuid}.ext)` |
| `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, … | code block | Автоопределение языка (25+ языков) |
| `.txt`, `.md`, `.yaml`, `.log`, `.cfg`, … | code block | Обёртка в ` ```text ``` ` |
| `.json` | code block (pretty-print) | `json.dumps(indent=2)` |
| `.html`, `.htm` | markdownify | heading_style=ATX |
| `.exe`, `.dll`, `.zip`, `.mp4`, `.db`, … | **отказ** | Ошибка: тип не поддерживается |

## Работа с картинками

Все изображения (из PDF, DOCX, загруженные напрямую) сохраняются в общую папку `images/` с уникальными UUID-именами:

```
images/
├── img_a1b2c3d4e5f6.png     # из image_converter
├── pdf_f7e8d9c0b1a2.jpg     # из PDF (docling)
├── docx_1234abcd5678.png    # из DOCX
└── img_90998877aabb.png     # ещё одна картинка
```

- **При конвертации PDF**: docling создаёт временную папку с картинками (например, `uploads/report/`). `ImageManager` переносит их в общую `images/` с UUID-именами и переписывает все ссылки в markdown.
- **При конвертации DOCX**: `ImageManager` извлекает картинки из `word/media/` внутри docx-архива.
- **При конвертации изображений напрямую**: картинка копируется в `images/`, создаётся markdown-файл из одной ссылки.

## Коды ошибок

| HTTP | Описание |
|------|----------|
| 400 | Не указано имя файла, batch > 50 файлов |
| 413 | Файл превышает `MAX_FILE_SIZE_MB` (100 MB) |
| 500 | Внутренняя ошибка конвертации |

Поле `success: false` в ответе не вызывает HTTP-ошибку — оно позволяет обрабатывать частичные сбои в batch-режиме.

## Тонкие моменты

### 1. docling и память

docling загружает модели машинного обучения для парсинга PDF. Первый запуск может занять время на загрузку моделей (~500 MB). В Docker-образе зарезервировано `1G` памяти.

### 2. CSV-разделители

Сервис автоматически определяет разделитель по первой строке:
- Если есть `\t` и нет `,` → табуляция
- Если есть `;` и нет `,` → точка с запятой
- Иначе → запятая

### 3. Картинки из PDF

Два пути извлечения:
- **docling** (основной): качественное извлечение, создаёт папку с картинками
- **PyMuPDF** (fallback): постраничное извлечение, если docling не установлен

### 4. Логирование

JSON-логи в stdout. Пример:

```json
{
  "timestamp": "2026-07-03T21:00:00.123456+00:00",
  "level": "INFO",
  "logger": "data_processor",
  "message": "converting_file",
  "filename": "report.pdf",
  "file_type": "pdf"
}
```

### 5. Очистка временных файлов

Все загруженные файлы удаляются сразу после конвертации. Промежуточные папки (созданные docling для картинок) также удаляются.
