from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ValidationError


@dataclass(frozen=True)
class TranslationSet:
    story: dict[str, dict[str, str]]
    strings: dict[str, dict[str, dict[str, str]]]


def default_translations_dir() -> Path:
    """Find bundled translations for source runs and PyInstaller builds."""
    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base:
        return Path(frozen_base) / "translations"

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "translations"
        if candidate.is_dir():
            return candidate
    return Path.cwd() / "translations"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"Missing translation file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def load_translations(translations_dir: Path | None = None) -> TranslationSet:
    root = translations_dir or default_translations_dir()
    story = load_json(root / "story.en.json")
    strings = load_json(root / "strings.en.json")
    validate_translation_shape(story, strings)
    return TranslationSet(story=story, strings=strings)


def validate_translation_shape(story: Any, strings: Any) -> None:
    if not isinstance(story, dict):
        raise ValidationError("story.en.json must be an object keyed by table name")
    for table, entries in story.items():
        if not isinstance(table, str) or not isinstance(entries, dict):
            raise ValidationError("story.en.json must map table names to entry objects")
        for key, text in entries.items():
            if not isinstance(key, str) or not isinstance(text, str):
                raise ValidationError(f"Invalid story entry under {table!r}")

    if not isinstance(strings, dict):
        raise ValidationError("strings.en.json must be an object keyed by table name")
    for table, entries in strings.items():
        if not isinstance(table, str) or not isinstance(entries, dict):
            raise ValidationError("strings.en.json must map table names to entry objects")
        for entry_id, row in entries.items():
            if not isinstance(entry_id, str) or not isinstance(row, dict):
                raise ValidationError(f"Invalid string entry under {table!r}")
            if not isinstance(row.get("text"), str):
                raise ValidationError(f"String entry {table}/{entry_id} is missing text")
            if "key" in row and not isinstance(row["key"], str):
                raise ValidationError(f"String entry {table}/{entry_id} has a non-string key")

def normalize_story_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, str]], int]:
    """Convert story JSONL-style rows into the committed JSON shape."""
    out: dict[str, dict[str, str]] = {}
    duplicates = 0
    for row in rows:
        table = str(row["table_name"])
        key = str(row["key"])
        text = str(row["en"])
        bucket = out.setdefault(table, {})
        if key in bucket:
            if bucket[key] != text:
                raise ValidationError(f"Conflicting story duplicate for {table}/{key}")
            duplicates += 1
            continue
        bucket[key] = text
    return out, duplicates


def normalize_string_rows(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, dict[str, str]]], int, int]:
    """Convert string JSONL-style rows into the committed JSON shape."""
    out: dict[str, dict[str, dict[str, str]]] = {}
    skipped_blank = 0
    duplicates = 0
    seen: set[tuple[str, str]] = set()
    for row in rows:
        table = str(row["table_name"])
        entry_id = str(row["entry_id"])
        ident = (table, entry_id)
        if ident in seen:
            duplicates += 1
            continue
        seen.add(ident)
        text = str(row.get("en") or "")
        if not text.strip():
            skipped_blank += 1
            continue
        out.setdefault(table, {})[entry_id] = {
            "key": str(row.get("key") or ""),
            "text": text,
        }
    return out, skipped_blank, duplicates
