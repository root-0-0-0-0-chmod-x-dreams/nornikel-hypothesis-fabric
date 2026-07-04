# Архитектура Data Processor

## Обзор

`data-processor` — FastAPI-микросервис, преобразующий файлы различных форматов в Markdown. Используется как компонент предобработки данных в системе «Фабрика гипотез»: любые входные документы (отчёты, статьи, таблицы, изображения) унифицируются в единый текстовый формат, пригодный для дальнейшей обработки LLM и RAG-пайплайнами.

## Гибкая система распознавания PDF

Главная особенность — **выбор библиотеки** для распознавания PDF через переменную `PDF_LIBRARY` в `.env`:

| Значение | Библиотека | Требования | Особенности |
|----------|------------|------------|-------------|
| `opendataloader` | OpenDataLoader PDF | Java 21+ | #1 в бенчмарках (0.907), таблицы, bounding boxes, быстрый (0.02s/стр) |
| `pymupdf` | PyMuPDF (fitz) | Только Python | Лёгкий, без Java, встроенный в образ |

Переключение между библиотеками не требует пересборки Docker-образа — достаточно изменить `.env` и перезапустить контейнер.

## Схема компонентов

```
┌──────────────────────────────────────────────────────────────────┐
│                      Docker Host                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  data-processor (FastAPI)                   │  │
│  │                                                              │  │
│  │  ┌──────────┐   ┌─────────────────┐   ┌──────────────────┐ │  │
│  │  │ Router   │──▶│ Converter       │──▶│ ImageManager     │ │  │
│  │  │ /api/v1  │   │ Registry        │   │    + OCR         │ │  │
│  │  └──────────┘   │ ┌─────────────┐ │   │ ┌──────────────┐ │ │  │
│  │                 │ │ pdf (flex)  │ │   │ │ images/      │ │ │  │
│  │  ┌──────────┐   │ │ docx        │ │   │ │  pdf_xxx.jpg │ │ │  │
│  │  │ utils.py │   │ │ xlsx/xls    │ │   │ │  img_xxx.png │ │ │  │
│  │  │ detect   │──▶│ │ csv         │ │   │ └──────────────┘ │ │  │
│  │  │ filetype │   │ │ image/*     │ │   │                  │ │  │
│  │  └──────────┘   │ │ code/text   │ │   │ OCR-блоки {OCR}  │ │  │
│  │                 │ │ html        │ │   │ после картинок   │ │  │
│  │                 │ │ binary      │ │   └──────────────────┘ │  │
│  │                 │ └─────────────┘                         │  │
│  │                 └─────────────────┘                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│       │                                                           │
│       ▼                                                           │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐                          │
│  │ images/ │  │uploads/ │  │ output/  │   ← Docker volumes       │
│  │ (vol)   │  │  (tmp)  │  │  (vol)   │                          │
│  └─────────┘  └─────────┘  └──────────┘                          │
└──────────────────────────────────────────────────────────────────┘
```

## Конвейер конвертации

```
1. POST /api/v1/convert  (файл + filename)
2. Сохранение во временную uploads/
3. utils.detect_file_type()  →  FileType enum
   ├── .pdf  → проверить .env PDF_LIBRARY → opendataloader или pymupdf
   ├── .docx → FileType.DOCX
   ├── .xlsx → FileType.XLSX
   ├── .xls  → FileType.XLS  (→ конвертация в .xlsx через xls2xlsx)
   ├── .csv  → FileType.CSV
   ├── .png/.jpg/… → IMAGE_*
   ├── .py/.js/… → CODE
   ├── .txt/.md/… → TEXT
   ├── .html → HTML
   └── бинарные → BINARY (отказ)
4. registry.get_converter(file_type)
5. asyncio.to_thread(converter_func, file_path, filename)
6. (если OCR_ENABLED=true) → EasyOCR на каждую картинку → вставка {OCR: ...}
7. ConvertResult → JSON-ответ
```

## Компоненты

### 1. Config — гибкая конфигурация (`config.py`)

Все параметры управляются через `.env`. Ключевые настройки PDF:

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `PDF_LIBRARY` | `opendataloader` | `opendataloader` или `pymupdf` |
| `PDF_IMAGE_OUTPUT` | `external` | `off`, `external` или `embedded` |
| `PDF_IMAGE_FORMAT` | `jpeg` | `jpeg` или `png` |
| `OCR_ENABLED` | `false` | Включить EasyOCR для картинок |
| `OCR_LANGUAGES` | `ru,en` | Языки OCR |
| `OCR_GPU_ENABLED` | `true` | GPU-ускорение EasyOCR |
| `PDF_HYBRID_ENABLED` | `false` | Гибридный режим opendataloader |

### 2. PDF Converter — два движка (`pdf_converter.py`)

#### OpenDataLoader PDF (`pdf_library=opendataloader`)
- Вызывает Java-CLI через `opendataloader_pdf.convert()`
- Markdown + папка с картинками
- ImageManager переписывает ссылки на UUID
- Поддержка hybrid-режима (AI-бэкенд для сложных страниц)
- Скорость: 0.02 сек/стр (локальный), 0.46 сек/стр (hybrid)
- Требует Java 21+

#### PyMuPDF (`pdf_library=pymupdf`)
- `fitz.open()` + постраничное извлечение текста и картинок
- `page.get_text("text")` для извлечения текста
- `page.get_images()` + `doc.extract_image()` для картинок
- Без внешних зависимостей (только Python)
- Легче и проще, но ниже качество таблиц и reading order

### 3. ImageManager + OCR (`image_manager.py`)

Централизованное хранилище изображений с встроенным OCR.

- Все картинки → `IMAGES_DIR` с UUID-именами
- `rewrite_markdown_images()`: парсит `![alt](path)`, копирует, переписывает ссылки
- `apply_ocr_to_markdown()`: находит все `![...](...)`, запускает EasyOCR, вставляет блоки:
  ```
  ![image 1](images/pdf_abc.jpeg)

  {OCR: Распознанный текст на изображении}
  ```
- EasyOCR инициализируется лениво (при первом вызове), поддерживает GPU через PyTorch CUDA

## Docker

- **Java 21** встроен в образ для opendataloader
- **EasyOCR** + **PyTorch** (CPU по умолчанию в контейнере)
- Для GPU: `docker compose --profile hybrid` для hybrid-сервера
- Объём образа: ~4 GB (Python + Java + PyTorch + модели OCR)

## Поддерживаемые форматы

| Формат | Конвертер | Примечания |
|--------|-----------|------------|
| `.pdf` | opendataloader / PyMuPDF | Выбор в `.env`, извлечение текста и картинок |
| `.docx` | docx2md | Таблицы, картинки из `word/media/` |
| `.xlsx` | openpyxl + pandas | Все листы, таблицы markdown |
| `.xls` | xls2xlsx → как .xlsx | Автоконвертация в .xlsx |
| `.csv`, `.tsv` | pandas | Автоопределение разделителя |
| `.png`, `.jpg`, … (7 форматов) | Копирование в images/ | Markdown: `![name](images/img_{uuid}.ext)` |
| `.py`, `.js`, … (25 языков) | code block | Автоопределение языка |
| `.txt`, `.md`, `.yaml`, … | code block | ` ```text ``` ` |
| `.json` | pretty-print | `json.dumps(indent=2)` |
| `.html`, `.htm` | markdownify | heading_style=ATX |
| Бинарные (30+ типов) | **отказ** | Ошибка: тип не поддерживается |

## Расширяемость

- **Смена PDF-движка**: изменить `PDF_LIBRARY` в `.env`, перезапустить
- **Новый формат**: добавить функцию в `converters/`, зарегистрировать в `CONVERTER_REGISTRY`
- **Кастомная папка картинок**: `IMAGES_DIR` в `.env`
- **S3/MinIO вместо локальной папки**: заменить `ImageManager.add_image` на загрузку в S3
