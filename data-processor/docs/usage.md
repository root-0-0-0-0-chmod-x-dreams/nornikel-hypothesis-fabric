# Data Processor — Руководство по использованию

## Быстрый старт

### 1. Настройка

```bash
cd data-processor
cp .env.example .env      # конфигурация по умолчанию готова к работе
```

Отредактируй `.env` под свои нужды (см. [Конфигурация](#конфигурация-pdf-и-ocr)).

### 2. Запуск через Docker

```bash
docker compose up -d --build
```

Проверка:

```bash
curl http://localhost:8001/api/v1/health
```

### 3. Локальный запуск

```bash
python -m venv venv
venv\Scripts\activate              # Windows
# source venv/bin/activate         # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Для opendataloader** дополнительно нужна Java 21+. Установи с [Adoptium](https://adoptium.net/) или:

```powershell
# Windows: скачать и распаковать JDK 21 на диск D:
# Скрипт установки прилагается:
python install_jdk.py
```

**Для OCR** нужен EasyOCR и PyTorch (уже в `requirements.txt`). При первом запуске EasyOCR загрузит модели (~300 MB).

## API

Базовый URL: `http://localhost:8001/api/v1`  
Swagger: `http://localhost:8001/docs`

### `GET /health`

```bash
curl http://localhost:8001/api/v1/health
# {"status":"ok","version":"1.0.0","uptime_seconds":42.1}
```

### `POST /convert`

Конвертация одного файла. Тело — `multipart/form-data`, поле `file`.

```bash
curl -X POST http://localhost:8001/api/v1/convert -F "file=@report.pdf"
```

Ответ:

```json
{
  "success": true,
  "original_filename": "report.pdf",
  "file_type": "pdf",
  "markdown_content": "# Title\n\nParagraph text...\n\n![Figure 1](images/pdf_a1b2.jpeg)\n\n{OCR: Подпись к рисунку 1}\n",
  "images_extracted": 5,
  "errors": [],
  "warnings": [],
  "metadata": {}
}
```

### `POST /convert/batch`

Пакетная конвертация до **50 файлов** за раз.

```bash
curl -X POST http://localhost:8001/api/v1/convert/batch \
  -F "files=@report.pdf" \
  -F "files=@data.xlsx"
```

## Конфигурация PDF и OCR

Все настройки в `.env`:

```ini
# Выбор PDF-движка
PDF_LIBRARY=opendataloader      # opendataloader | pymupdf
PDF_IMAGE_OUTPUT=external       # off | external | embedded
PDF_IMAGE_FORMAT=jpeg           # jpeg | png

# OpenDataLoader Hybrid (опционально)
PDF_HYBRID_ENABLED=false        # нужен сервер opendataloader-pdf-hybrid
PDF_HYBRID_BACKEND=docling-fast
PDF_HYBRID_URL=http://localhost:5002
PDF_HYBRID_MODE=auto

# OCR картинок
OCR_ENABLED=false               # включить EasyOCR
OCR_LANGUAGES=ru,en             # языки через запятую
OCR_GPU_ENABLED=true            # GPU-ускорение (нужен CUDA)
```

### Режимы PDF_IMAGE_OUTPUT

| Режим | opendataloader | pymupdf | Результат |
|-------|---------------|---------|-----------|
| `off` | Только текст | Только текст | Нет картинок, максимальная скорость |
| `external` | Картинки в файлах | Картинки в файлах | Файлы в `images/`, ссылки в markdown |
| `embedded` | Base64 в markdown | не поддерживается | Тяжёлый markdown с base64-картинками |

### Выбор PDF-движка

| Критерий | opendataloader | pymupdf |
|----------|---------------|---------|
| Точность | #1 в бенчмарках (0.907) | Средняя |
| Скорость | 0.02 сек/стр | ~0.01 сек/стр |
| Таблицы | Отличное (0.928) | Базовое |
| Зависимости | Java 21+ | Только Python |
| Размер образа | ~2.5 GB | ~1 GB |
| Reading order | XY-Cut++ | Постраничный |

### OCR — как работает

При `OCR_ENABLED=true` после каждой картинки в markdown добавляется блок с распознанным текстом:

```markdown
![Схема флотации](images/pdf_a1b2c3.jpeg)

{OCR: Схема флотации руд цветных металлов с применением реагентов}
```

- **EasyOCR** запускается асинхронно для каждой картинки
- Модели загружаются при первом использовании (ленивая инициализация)
- **GPU**: при `OCR_GPU_ENABLED=true` использует CUDA/GPU (нужен PyTorch с CUDA)
- **CPU**: при `false` работает на CPU (медленнее, но без GPU)

### Установка EasyOCR вручную

```bash
pip install easyocr
```

Проверка:

```python
import easyocr
reader = easyocr.Reader(['ru', 'en'], gpu=True)
result = reader.readtext('test_image.png')
print(result)
```

При первом запуске EasyOCR загрузит модели (~300 MB для ru+en) в кэш `~/.EasyOCR/model/`.

## Hybrid-режим opendataloader (опционально)

Для максимального качества на сложных PDF (скан-копии, формулы, сложные таблицы):

```bash
# Терминал 1 — hybrid-сервер
pip install "opendataloader-pdf[hybrid]"
opendataloader-pdf-hybrid --port 5002 --force-ocr --ocr-lang "ru,en"

# Терминал 2 — в .env установить:
# PDF_HYBRID_ENABLED=true
# PDF_HYBRID_URL=http://localhost:5002
```

Или через Docker:

```bash
docker compose --profile hybrid up -d
```

## Установка Java 21 (для opendataloader)

### Windows (установка на диск D:)

```powershell
python install_jdk.py
```

Скрипт скачает JDK 21 с GitHub, распакует на `D:\java\jdk-21` и установит `JAVA_HOME`.

### Linux (Docker)

Java 21 уже встроена в Docker-образ. Для локального запуска:

```bash
apt-get install -y openjdk-21-jre-headless
```

## Поддерживаемые форматы

| Формат | Конвертер | Примечания |
|--------|-----------|------------|
| `.pdf` | opendataloader / pymupdf | Выбор через PDF_LIBRARY |
| `.docx` | docx2md | Таблицы, картинки из `word/media/` |
| `.xlsx` | openpyxl + pandas | Все листы |
| `.xls` | xls2xlsx → .xlsx | Автоконвертация |
| `.csv`, `.tsv` | pandas | Авто-разделитель |
| `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp` | Копия в images/ | UUID-имя |
| `.py`, `.js`, `.ts`, … | code block | Авто-язык |
| `.txt`, `.md`, `.yaml`, … | code block | ` ```text ``` ` |
| `.json` | pretty-print | `json.dumps(indent=2)` |
| `.html`, `.htm` | markdownify | ATX-headings |
| `.exe`, `.zip`, `.mp4`, … | **отказ** | Бинарные не поддерживаются |

## Работа с картинками

Все изображения сохраняются в `IMAGES_DIR` с UUID-именами. При OCR к ним добавляются текстовые описания.

## Коды ошибок

| HTTP | Описание |
|------|----------|
| 400 | Не указано имя файла, batch > 50 |
| 413 | Файл > MAX_FILE_SIZE_MB |
| 500 | Внутренняя ошибка конвертации |

## Логирование

JSON-логи в stdout:

```json
{
  "timestamp": "2026-07-04T18:00:00+00:00",
  "level": "INFO",
  "logger": "data_processor",
  "message": "converting_file",
  "original_filename": "report.pdf",
  "detected_type": "pdf"
}
```
