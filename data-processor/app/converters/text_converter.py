from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from app.models import ConvertResult
from app.utils import FileType, get_language_for_code

logger = logging.getLogger("data_processor")


def convert_text(file_path: Path, original_filename: str) -> ConvertResult:
    try:
        content = file_path.read_text(encoding="utf-8")
        suffix = file_path.suffix.lower()
        content_type = "text"

        if suffix == ".json":
            content_type = "json"
            try:
                parsed = json.loads(content)
                content = json.dumps(parsed, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass

        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.TEXT.value,
            markdown_content=f"```{content_type}\n{content}\n```\n",
            metadata={"encoding": "utf-8"},
        )

    except UnicodeDecodeError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.TEXT.value,
            errors=["File is not valid UTF-8 text"],
        )
    except Exception as e:
        logger.exception("text_conversion_failed")
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.TEXT.value,
            errors=[str(e)],
        )


def convert_code(file_path: Path, original_filename: str) -> ConvertResult:
    try:
        content = file_path.read_text(encoding="utf-8")
        language = get_language_for_code(original_filename)
        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.CODE.value,
            markdown_content=f"```{language}\n{content}\n```\n",
            metadata={"language": language, "encoding": "utf-8"},
        )
    except UnicodeDecodeError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.CODE.value,
            errors=["File is not valid UTF-8 text"],
        )
    except Exception as e:
        logger.exception("code_conversion_failed")
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.CODE.value,
            errors=[str(e)],
        )


def convert_csv(file_path: Path, original_filename: str) -> ConvertResult:
    try:
        import pandas as pd

        delimiter = ","
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
            if "\t" in first_line and "," not in first_line:
                delimiter = "\t"
            elif ";" in first_line and "," not in first_line:
                delimiter = ";"

        df = pd.read_csv(
            str(file_path),
            sep=delimiter,
            encoding="utf-8",
            on_bad_lines="skip",
            dtype=str,
        )

        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.CSV.value,
            markdown_content=df.to_markdown(index=False),
            metadata={
                "rows": len(df),
                "columns": list(df.columns),
                "delimiter": delimiter,
            },
        )

    except ImportError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.CSV.value,
            errors=["pandas not installed. Install: pip install pandas tabulate"],
        )
    except Exception as e:
        logger.exception("csv_conversion_failed")
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.CSV.value,
            errors=[str(e)],
        )


def convert_html(file_path: Path, original_filename: str) -> ConvertResult:
    try:
        from markdownify import markdownify as md_convert

        content = file_path.read_text(encoding="utf-8", errors="replace")
        md_text = md_convert(content, heading_style="ATX")
        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.HTML.value,
            markdown_content=md_text,
        )
    except ImportError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.HTML.value,
            errors=["markdownify not installed. Install: pip install markdownify"],
        )
    except Exception as e:
        logger.exception("html_conversion_failed")
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.HTML.value,
            errors=[str(e)],
        )


def convert_binary(file_path: Path, original_filename: str) -> ConvertResult:
    return ConvertResult(
        success=False,
        original_filename=original_filename,
        file_type=FileType.BINARY.value,
        errors=[f"Binary file type not supported: {file_path.suffix}. Cannot convert to machine-readable format."],
    )
