# Архитектура Data Processor

## Обзор

`data-processor` — FastAPI-микросервис, преобразующий файлы различных форматов в Markdown. Используется как компонент предобработки данных в системе «Фабрика гипотез»: любые входные документы (отчёты, статьи, таблицы, изображения) унифицируются в единый текстовый формат, пригодный для дальнейшей обработки LLM и RAG-пайплайнами.

## Схема компонентов

```
┌──────────────────────────────────────────────────────────────────┐
│                     Docker Host                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  data-processor (FastAPI)                   │  │
│  │                                                              │  │
│  │  ┌──────────┐   ┌─────────────────┐   ┌──────────────────┐ │  │
│  │  │ Router   │──▶│ Converter       │──▶│ ImageManager     │ │  │
│  │  │ /api/v1  │   │ Registry        │   │                  │ │  │
│  │  └──────────┘   │ ┌─────────────┐ │   │ ┌──────────────┐ │ │  │
│  │                 │ │ pdf         │ │   │ │ images/      │ │ │  │
│  │  ┌──────────┐   │ │ docx        │ │   │ │  img_a1b2.png│ │ │  │
│  │  │ utils.py │   │ │ xlsx/xls    │ │   │ │  pdf_c3d4.jpg│ │ │  │
│  │  │ detect   │──▶│ │ csv         │ │   │ │  docx_e5f6..│ │ │  │
│  │  │ filetype │   │ │ image/*     │ │   │ └──────────────┘ │ │  │
│  │  └──────────┘   │ │ code/text   │ │   │                  │ │  │
│  │                 │ │ html        │ │   │ UUID-имена       │ │  │
│  │                 │ │ binary      │ │   │ перезапись ссылок│ │  │
│  │                 │ └─────────────┘ │   └──────────────────┘ │  │
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
   ├── .pdf  → FileType.PDF
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
6. ConvertResult → JSON-ответ
```

## Компоненты

### 1. Utils — детекция типов (`utils.py`)

Определяет `FileType` по расширению + эвристике содержимого:

| Категория | Расширения | FileType |
|-----------|------------|----------|
| PDF | `.pdf` | `PDF` |
| Word | `.docx` | `DOCX` |
| Excel | `.xlsx`, `.xls` | `XLSX`, `XLS` |
| CSV | `.csv`, `.tsv` | `CSV` |
| Изображения | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp` | `IMAGE_*` |
| Код | `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, … (25 языков) | `CODE` |
| Текст | `.txt`, `.md`, `.yaml`, `.cfg`, `.log`, … | `TEXT` |
| JSON | `.json` | `JSON` |
| HTML | `.html`, `.htm` | `HTML` |
| Бинарные | `.exe`, `.dll`, `.zip`, `.mp3`, `.mp4`, `.db`, `.pt`, … | `BINARY` |

Если расширение неопознано — проверка на текстовое содержимое (эвристика: < 10% не-text байт в первых 1024 байтах).

### 2. ImageManager (`image_manager.py`)

Централизованное хранилище изображений.

- Все картинки сохраняются в единую директорию (`IMAGES_DIR`)
- Имена: `{prefix}_{uuid12}.{ext}` (например: `pdf_a1b2c3d4e5f6.png`)
- Дедупликация: если файл с таким именем уже существует — не перезаписывается
- `rewrite_markdown_images(md_content, source_images_dir, prefix)`:
  - Парсит `![alt](path)` в markdown
  - Для каждой локальной ссылки: ищет файл в `source_images_dir`
  - Копирует в общую папку с новым UUID-именем
  - Заменяет ссылку в markdown на `images/{uuid_name}`
  - Возвращает обновлённый markdown и количество извлечённых картинок

Это критично для PDF (docling создаёт папку `filename/` с картинками рядом с md — ссылки вида `filename/img_001.png` заменяются на `images/pdf_a1b2....png`).

### 3. Конвертеры (`converters/`)

#### PDF (`pdf_converter.py`)
- **Основной путь**: `docling.DocumentConverter().convert()` → markdown с папкой картинок
- **ImageManager**: rewrite ссылок из папки docling в общую `images/`
- **Fallback** (если docling не установлен): `PyMuPDF` (fitz) — постраничное извлечение текста и картинок

#### DOCX (`docx_converter.py`)
- `docx2md.do_convert(use_md_table=True)`
- Извлечение картинок из `word/media/` через `zipfile`
- ImageManager: rewrite ссылок

#### Excel (`excel_converter.py`)
- `.xlsx`: `openpyxl.load_workbook(data_only=True)` → для каждого листа `pandas.DataFrame.to_markdown()`
- `.xls`: `xls2xlsx.XLS2XLSX(...).to_xlsx(...)` → затем как `.xlsx`
- Обработка пустых ячеек, NaN, float→int нормализация

#### CSV (`text_converter.py`)
- Автоопределение разделителя: `,` → `;` → `\t` (по первой строке)
- `pandas.read_csv(dtype=str)` → `to_markdown()`

#### Изображения (`image_converter.py`)
- `ImageManager.add_image()` — копия в `images/`
- Markdown-вывод: `![filename](images/img_{uuid}.ext)`

#### Текст/Код (`text_converter.py`)
- Чтение UTF-8, заворачивание в code block
- Для кода: автоопределение языка по расширению (подсветка синтаксиса)
- JSON: pretty-print (2 пробела)

#### HTML (`text_converter.py`)
- `markdownify.markdownify(heading_style="ATX")`

#### Бинарные (`text_converter.py`)
- Возвращает ошибку: «тип не поддерживается»

### 4. Registry (`converters/registry.py`)

- Словарь `CONVERTER_REGISTRY: Dict[FileType, Callable]`
- `convert_file()`: detect → lookup → `asyncio.to_thread(converter, ...)`
- Все конвертеры — синхронные функции, вызываются в отдельном потоке

### 5. Router (`router.py`)

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/v1/health` | GET | Состояние сервиса |
| `/api/v1/convert` | POST | Конвертация одного файла (multipart) |
| `/api/v1/convert/batch` | POST | Пакетная конвертация (до 50 файлов) |
| `/api/v1/convert/{filename}/raw` | GET | Получить ранее сконвертированный markdown |

### 6. Модели ответа (`models.py`)

```python
ConvertResult:
    success: bool
    original_filename: str
    file_type: str            # pdf, docx, xlsx, ...
    markdown_content: str     # итоговый markdown
    images_extracted: int     # сколько картинок перенесено в images/
    errors: list[str]
    warnings: list[str]
    metadata: dict            # pages, sheets, rows, language, delimiter...
```

## Docker и volume mounts

```yaml
volumes:
  - images_data:/app/images    # постоянное хранилище картинок
  - output_data:/app/output    # постоянное хранилище markdown-результатов
```

`uploads/` — временная директория (внутри контейнера, очищается после каждого запроса).

## Поток данных при конвертации PDF с картинками

```
1. PDF загружается во временный uploads/
2. docling.DocumentConverter().convert("uploads/doc.pdf")
   → создаёт uploads/doc/*.png  (картинки рядом с документом)
   → возвращает markdown со ссылками вида ![img](doc/img_001.png)
3. ImageManager.rewrite_markdown_images():
   a. Парсит все ![...](doc/*.png)
   b. Копирует каждый doc/*.png → images/pdf_{uuid}.png
   c. Заменяет ссылки: ![img](images/pdf_{uuid}.png)
4. Удаляет временную папку uploads/doc/
5. Удаляет временный uploads/doc.pdf
6. Возвращает ConvertResult с обновлённым markdown
```

## Расширяемость

- **Новый формат**: добавить функцию-конвертер в `converters/`, зарегистрировать в `CONVERTER_REGISTRY`
- **Кастомная папка картинок**: изменить `IMAGES_DIR` в `.env`
- **Несколько экземпляров**: `docker compose up --scale data-processor=3` (stateless, images на общем volume)
- **S3/MinIO вместо локальной папки**: заменить `ImageManager.add_image` на загрузку в S3 с возвратом URL

## Ограничения

- Максимальный размер одного файла: `MAX_FILE_SIZE_MB` (100 MB по умолчанию)
- Максимум файлов в batch: 50
- Бинарные файлы (`.exe`, `.zip`, `.mp4`, `.db`, `.pt`, …) — отказ с ошибкой
- Картинки в PDF извлекаются docling или PyMuPDF (могут быть пропущены при сложной вёрстке)
