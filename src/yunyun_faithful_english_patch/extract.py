from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .errors import FaithfulPatchError
from .game import resolve_game_paths, validate_game_root
from .patching import string_table_name, textasset_table_name
from .translations import load_translations

STRING_BUNDLE_BY_LOCALE = {
    "en": Path(
        "Yunyun_Syndrome_Data/StreamingAssets/aa/StandaloneWindows64/"
        "localization-string-tables-english(en)_assets_all.bundle"
    ),
    "ja": Path(
        "Yunyun_Syndrome_Data/StreamingAssets/aa/StandaloneWindows64/"
        "localization-string-tables-japanese(ja)_assets_all.bundle"
    ),
}
SHARED_ASSETS_BUNDLE = Path(
    "Yunyun_Syndrome_Data/StreamingAssets/aa/StandaloneWindows64/"
    "localization-assets-shared_assets_all.bundle"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m yunyun_faithful_english_patch.extract",
        description="Extract local string tables for translation maintenance.",
    )
    parser.add_argument("--game-root", type=Path, required=True, help="Game root folder")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument(
        "--locale",
        default="en,ja",
        help="Comma-separated locale codes to extract; supported values: en, ja",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow unknown target file hashes after all other sanity checks pass",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except FaithfulPatchError as exc:
        parser.exit(2, f"error: {exc}\n")


def run(args: argparse.Namespace) -> int:
    paths = resolve_game_paths(args.game_root)
    validate_game_root(paths, force=args.force)
    locales = parse_locales(args.locale)
    shared_bundle = shared_assets_bundle(paths.root)
    string_key_maps = extract_string_key_maps(shared_bundle)

    args.out.mkdir(parents=True, exist_ok=True)
    story_rows_by_locale: dict[str, list[dict[str, Any]]] = {}
    string_rows_by_locale: dict[str, list[dict[str, Any]]] = {}

    for locale in locales:
        story_path = args.out / f"story.{locale}.raw.jsonl"
        strings_path = args.out / f"strings.{locale}.raw.jsonl"
        string_bundle = locale_string_bundle(paths.root, locale)

        story_rows = list(extract_story_rows(paths.data_unity3d, locale))
        string_rows = list(extract_string_rows(string_bundle, string_key_maps, locale))
        story_rows_by_locale[locale] = story_rows
        string_rows_by_locale[locale] = string_rows

        story_count = write_jsonl(story_path, story_rows)
        string_count = write_jsonl(strings_path, string_rows)
        print(f"Wrote {story_count} story rows to {story_path}")
        print(f"Wrote {string_count} string rows to {strings_path}")

    if "ja" in locales:
        translations = load_translations()
        story_comparison_path = args.out / "story.ja_vs_translation.en.jsonl"
        strings_comparison_path = args.out / "strings.ja_vs_translation.en.jsonl"
        story_count = write_jsonl(
            story_comparison_path,
            compare_story_rows(story_rows_by_locale["ja"], translations.story),
        )
        string_count = write_jsonl(
            strings_comparison_path,
            compare_string_rows(
                string_rows_by_locale["ja"],
                translations.strings,
                target_en_rows=string_rows_by_locale.get("en"),
            ),
        )
        print(f"Wrote {story_count} story comparison rows to {story_comparison_path}")
        print(f"Wrote {string_count} string comparison rows to {strings_comparison_path}")

    print("Extraction complete. Review output before sharing; it may include game text.")
    return 0


def parse_locales(value: str) -> list[str]:
    locales: list[str] = []
    for raw_locale in value.split(","):
        locale = raw_locale.strip()
        if not locale:
            continue
        if locale not in STRING_BUNDLE_BY_LOCALE:
            supported = ", ".join(sorted(STRING_BUNDLE_BY_LOCALE))
            message = f"Unsupported locale {locale!r}; supported values: {supported}"
            raise FaithfulPatchError(message)
        if locale not in locales:
            locales.append(locale)
    if not locales:
        raise FaithfulPatchError("At least one locale must be requested")
    return locales


def locale_string_bundle(game_root: Path, locale: str) -> Path:
    try:
        relative_path = STRING_BUNDLE_BY_LOCALE[locale]
    except KeyError as exc:
        supported = ", ".join(sorted(STRING_BUNDLE_BY_LOCALE))
        message = f"Unsupported locale {locale!r}; supported values: {supported}"
        raise FaithfulPatchError(message) from exc

    path = game_root / relative_path
    if not path.exists():
        raise FaithfulPatchError(f"Missing {locale!r} string bundle: {relative_path}")
    return path


def shared_assets_bundle(game_root: Path) -> Path:
    path = game_root / SHARED_ASSETS_BUNDLE
    if not path.exists():
        raise FaithfulPatchError(f"Missing shared localization bundle: {SHARED_ASSETS_BUNDLE}")
    return path


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def extract_story_rows(data_unity3d: Path, locale: str) -> Iterable[dict[str, Any]]:
    import UnityPy

    env = UnityPy.load(str(data_unity3d))
    for obj in env.objects:
        if getattr(obj.type, "name", "") != "TextAsset":
            continue
        try:
            data = obj.read()
        except Exception:
            continue
        name = str(getattr(data, "name", "") or getattr(data, "m_Name", ""))
        table_name = textasset_table_name(name)
        if not table_name:
            continue
        script = (
            data.m_Script.decode("utf-8-sig")
            if isinstance(data.m_Script, bytes)
            else data.m_Script
        )
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue
        keys = payload.get("Keys")
        rows = payload.get("List")
        if not isinstance(keys, list) or not isinstance(rows, list):
            continue
        for language_row in rows:
            if not isinstance(language_row, dict) or language_row.get("Language") != locale:
                continue
            lines = language_row.get("Lines")
            if not isinstance(lines, list):
                continue
            for index, key in enumerate(keys):
                if index < len(lines):
                    yield {
                        "domain": "story",
                        "table_name": table_name,
                        "key": str(key),
                        "locale": locale,
                        "text": lines[index],
                    }


def extract_string_rows(
    string_bundle: Path,
    string_keys: dict[str, dict[str, str]],
    locale: str,
) -> Iterable[dict[str, Any]]:
    import UnityPy

    env = UnityPy.load(str(string_bundle))
    suffix = f"_{locale}"
    for obj in env.objects:
        if getattr(obj.type, "name", "") != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        name = str(tree.get("m_Name") or "")
        if not name.endswith(suffix):
            continue
        table_name = string_table_name(name) if locale == "en" else name[: -len(suffix)]
        if not table_name:
            continue
        table_data = tree.get("m_TableData")
        if not isinstance(table_data, list):
            continue
        key_by_entry_id = string_keys.get(table_name, {})
        for row in table_data:
            if isinstance(row, dict) and "m_Id" in row:
                entry_id = str(row["m_Id"])
                yield {
                    "domain": "strings",
                    "table_name": table_name,
                    "entry_id": entry_id,
                    "key": key_by_entry_id.get(entry_id),
                    "locale": locale,
                    "text": row.get("m_Localized", ""),
                }


def extract_string_key_maps(shared_bundle: Path) -> dict[str, dict[str, str]]:
    import UnityPy

    env = UnityPy.load(str(shared_bundle))
    table_keys: dict[str, dict[str, str]] = {}
    for obj in env.objects:
        if getattr(obj.type, "name", "") != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        table_name = str(tree.get("m_TableCollectionName") or "")
        if not table_name:
            name = str(tree.get("m_Name") or "")
            suffix = " Shared Data"
            if name.endswith(suffix):
                table_name = name[: -len(suffix)]
        entries = tree.get("m_Entries")
        if not table_name or not isinstance(entries, list):
            continue

        key_by_entry_id: dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict) or "m_Id" not in entry or "m_Key" not in entry:
                continue
            key_by_entry_id[str(entry["m_Id"])] = str(entry["m_Key"])
        if key_by_entry_id:
            table_keys[table_name] = key_by_entry_id
    return table_keys


def compare_story_rows(
    source_ja_rows: Iterable[dict[str, Any]],
    story_translations: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    source = {
        (str(row["table_name"]), str(row["key"])): row
        for row in source_ja_rows
        if "table_name" in row and "key" in row
    }
    translation_keys = {
        (table_name, key)
        for table_name, entries in story_translations.items()
        for key in entries
    }
    rows: list[dict[str, Any]] = []
    for table_name, key in sorted(source.keys() | translation_keys):
        source_row = source.get((table_name, key))
        translation_en = story_translations.get(table_name, {}).get(key)
        rows.append(
            {
                "domain": "story",
                "table_name": table_name,
                "key": key,
                "source_ja": source_row.get("text") if source_row else None,
                "translation_en": translation_en,
                "status": comparison_status(source_row is not None, translation_en is not None),
            }
        )
    return rows


def compare_string_rows(
    source_ja_rows: Iterable[dict[str, Any]],
    string_translations: dict[str, dict[str, dict[str, str]]],
    *,
    target_en_rows: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    source = {
        (str(row["table_name"]), str(row["entry_id"])): row
        for row in source_ja_rows
        if "table_name" in row and "entry_id" in row
    }
    target = {
        (str(row["table_name"]), str(row["entry_id"])): row
        for row in (target_en_rows or [])
        if "table_name" in row and "entry_id" in row
    }
    translation_keys = {
        (table_name, entry_id)
        for table_name, entries in string_translations.items()
        for entry_id in entries
    }
    rows: list[dict[str, Any]] = []
    for table_name, entry_id in sorted(source.keys() | target.keys() | translation_keys):
        source_row = source.get((table_name, entry_id))
        target_row = target.get((table_name, entry_id))
        translation_row = string_translations.get(table_name, {}).get(entry_id)
        has_source = source_row is not None
        has_translation = translation_row is not None
        status = comparison_status(has_source, has_translation)
        if target_row is not None and not has_translation:
            status = "extra_target"
        key = None
        for row in (translation_row, source_row, target_row):
            if row is not None and row.get("key"):
                key = row.get("key")
                break
        rows.append(
            {
                "domain": "strings",
                "table_name": table_name,
                "entry_id": entry_id,
                "key": key,
                "source_ja": source_row.get("text") if source_row else None,
                "translation_en": translation_row.get("text") if translation_row else None,
                "target_en": target_row.get("text") if target_row else None,
                "status": status,
            }
        )
    return rows


def comparison_status(has_source: bool, has_translation: bool) -> str:
    if has_source and has_translation:
        return "matched"
    if has_source:
        return "missing_translation"
    return "missing_source"


if __name__ == "__main__":
    raise SystemExit(main())
