from __future__ import annotations

import json
from dataclasses import dataclass, field
from io import IOBase
from pathlib import Path
from typing import Any

from .errors import PatchError
from .game import atomic_write_with_writer

UNITY_PACKER = "original"


@dataclass
class PatchStats:
    target: str
    changed: int = 0
    matched: int = 0
    unchanged: int = 0
    tables_seen: set[str] = field(default_factory=set)
    missing_tables: set[str] = field(default_factory=set)
    missing_entries: list[str] = field(default_factory=list)

    def extend(self, other: PatchStats) -> None:
        self.changed += other.changed
        self.matched += other.matched
        self.unchanged += other.unchanged
        self.tables_seen.update(other.tables_seen)
        self.missing_tables.update(other.missing_tables)
        self.missing_entries.extend(other.missing_entries)

    @property
    def has_missing(self) -> bool:
        return bool(self.missing_tables or self.missing_entries)

    def summary(self) -> str:
        return (
            f"{self.target}: changed={self.changed}, matched={self.matched}, "
            f"unchanged={self.unchanged}, missing_tables={len(self.missing_tables)}, "
            f"missing_entries={len(self.missing_entries)}"
        )


def textasset_table_name(name: str) -> str | None:
    return name[:-5] if name.endswith(".lang") else None


def string_table_name(name: str) -> str | None:
    return name[:-3] if name.endswith("_en") else None


def object_name(obj: object) -> str:
    try:
        name = obj.peek_name()
    except Exception:
        return ""
    return str(name) if name else ""


def save_bundle_to_handle(bundle: object, handle: IOBase, packer: str | tuple[int, int]) -> None:
    from UnityPy.streams import EndianBinaryWriter

    writer = EndianBinaryWriter(handle)
    writer.write_string_to_null(bundle.signature)
    writer.write_u_int(bundle.version)
    writer.write_string_to_null(bundle.version_player)
    writer.write_string_to_null(bundle.version_engine)

    if bundle.signature == "UnityArchive":
        raise NotImplementedError("BundleFile - UnityArchive")
    if bundle.signature in ["UnityWeb", "UnityRaw"]:
        if bundle.version == 6:
            bundle.save_fs(writer, 64, 64)
        else:
            bundle.save_web_raw(writer)
        return
    if bundle.signature != "UnityFS":
        raise NotImplementedError(f"Unknown Bundle signature: {bundle.signature}")

    if not packer or packer == "none":
        bundle.save_fs(writer, 64, 64)
    elif packer == "original":
        bundle.save_fs(
            writer,
            data_flag=bundle.dataflags,
            block_info_flag=bundle._block_info_flags,
        )
    elif packer == "lz4":
        bundle.save_fs(writer, data_flag=194, block_info_flag=2)
    elif packer == "lzma":
        bundle.save_fs(writer, data_flag=65, block_info_flag=1)
    elif isinstance(packer, tuple):
        bundle.save_fs(writer, *packer)
    else:
        raise NotImplementedError("UnityFS - Packer:", packer)


def apply_story_payload(
    asset_name: str,
    script: str | bytes,
    story_translations: dict[str, dict[str, str]],
) -> tuple[str | bytes, PatchStats]:
    stats = PatchStats(target="story")
    table_name = textasset_table_name(asset_name)
    if not table_name or table_name not in story_translations:
        return script, stats

    was_bytes = isinstance(script, bytes)
    text = script.decode("utf-8-sig") if was_bytes else script
    payload = json.loads(text)
    keys = payload.get("Keys")
    language_rows = payload.get("List")
    if not isinstance(keys, list) or not isinstance(language_rows, list):
        raise PatchError(f"Story payload {asset_name} does not have Keys/List arrays")

    english_row = None
    for row in language_rows:
        if isinstance(row, dict) and row.get("Language") == "en":
            english_row = row
            break
    if english_row is None:
        raise PatchError(f"Story payload {asset_name} does not contain an English row")

    lines = english_row.get("Lines")
    if not isinstance(lines, list):
        raise PatchError(f"Story payload {asset_name} English row does not contain Lines")

    stats.tables_seen.add(table_name)
    key_to_index = {str(key): index for index, key in enumerate(keys)}
    for key, replacement in story_translations[table_name].items():
        index = key_to_index.get(key)
        if index is None or index >= len(lines):
            stats.missing_entries.append(f"{table_name}/{key}")
            continue
        stats.matched += 1
        if lines[index] == replacement:
            stats.unchanged += 1
        else:
            lines[index] = replacement
            stats.changed += 1

    new_text = json.dumps(payload, ensure_ascii=False, indent=4) + "\n"
    return (new_text.encode("utf-8") if was_bytes else new_text), stats


def apply_string_typetree(
    tree: dict[str, Any],
    string_translations: dict[str, dict[str, dict[str, str]]],
) -> PatchStats:
    stats = PatchStats(target="strings")
    table_name = string_table_name(str(tree.get("m_Name") or ""))
    if not table_name or table_name not in string_translations:
        return stats

    table_data = tree.get("m_TableData")
    if not isinstance(table_data, list):
        raise PatchError(f"String table {table_name} does not contain m_TableData")

    stats.tables_seen.add(table_name)
    by_id = {
        str(row.get("m_Id")): row
        for row in table_data
        if isinstance(row, dict) and "m_Id" in row
    }
    for entry_id, replacement_row in string_translations[table_name].items():
        row = by_id.get(str(entry_id))
        if row is None:
            stats.missing_entries.append(f"{table_name}/{entry_id}")
            continue
        replacement = replacement_row["text"]
        stats.matched += 1
        if row.get("m_Localized") == replacement:
            stats.unchanged += 1
        else:
            row["m_Localized"] = replacement
            stats.changed += 1
    return stats


def patch_story_file(
    data_unity3d: Path,
    story_translations: dict[str, dict[str, str]],
    *,
    dry_run: bool = False,
) -> PatchStats:
    import UnityPy

    env = UnityPy.load(str(data_unity3d))
    stats = PatchStats(target="story")
    changed_objects = 0

    for obj in env.objects:
        if getattr(obj.type, "name", "") != "TextAsset":
            continue
        name = object_name(obj)
        if name and textasset_table_name(name) not in story_translations:
            continue
        try:
            data = obj.read()
        except Exception:
            continue
        if not name:
            name = str(getattr(data, "name", "") or getattr(data, "m_Name", ""))
        if textasset_table_name(name) not in story_translations:
            continue
        new_script, object_stats = apply_story_payload(name, data.m_Script, story_translations)
        stats.extend(object_stats)
        if object_stats.changed:
            if not dry_run:
                data.m_Script = new_script
                data.save()
                changed_objects += 1

    stats.missing_tables.update(set(story_translations) - stats.tables_seen)
    raise_if_missing(stats)

    if not dry_run and changed_objects:
        atomic_write_with_writer(
            data_unity3d,
            lambda handle: save_bundle_to_handle(env.file, handle, UNITY_PACKER),
        )
    return stats


def patch_string_bundle(
    string_bundle: Path,
    string_translations: dict[str, dict[str, dict[str, str]]],
    *,
    dry_run: bool = False,
) -> PatchStats:
    import UnityPy

    env = UnityPy.load(str(string_bundle))
    stats = PatchStats(target="strings")
    changed_objects = 0

    for obj in env.objects:
        if getattr(obj.type, "name", "") != "MonoBehaviour":
            continue
        name = object_name(obj)
        if name and string_table_name(name) not in string_translations:
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if string_table_name(str(tree.get("m_Name") or "")) not in string_translations:
            continue
        object_stats = apply_string_typetree(tree, string_translations)
        stats.extend(object_stats)
        if object_stats.changed:
            if not dry_run:
                obj.save_typetree(tree)
                changed_objects += 1

    stats.missing_tables.update(set(string_translations) - stats.tables_seen)
    raise_if_missing(stats)

    if not dry_run and changed_objects:
        atomic_write_with_writer(
            string_bundle,
            lambda handle: save_bundle_to_handle(env.file, handle, UNITY_PACKER),
        )
    return stats


def raise_if_missing(stats: PatchStats) -> None:
    if not stats.has_missing:
        return
    details = []
    if stats.missing_tables:
        details.append("missing tables: " + ", ".join(sorted(stats.missing_tables)[:20]))
    if stats.missing_entries:
        details.append("missing entries: " + ", ".join(stats.missing_entries[:20]))
    message = f"{stats.target} translations do not match target assets; "
    raise PatchError(message + "; ".join(details))
