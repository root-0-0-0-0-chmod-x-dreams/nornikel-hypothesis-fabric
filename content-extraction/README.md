# Content Extraction Service

FastAPI microservice that renders a page in Chromium, extracts the main article with Readability, converts it to Markdown, and returns structured JSON.

## Endpoints

- `POST /api/v1/extract`
- `GET /health/live`
- `GET /health/ready`

## Run

```bash
uvicorn main:app --reload
```

## Notes

- The browser layer uses Playwright.
- The extractor layer uses Readability for main-content extraction.
- Markdown conversion uses `markdownify` as a Turndown equivalent in Python.
