from __future__ import annotations

import argparse
import importlib.resources
from datetime import UTC, datetime
from pathlib import Path

import UnityPy

from . import __version__
from .constants import CATALOG_BIN, PROJECT_NAME, STRING_BUNDLE
from .errors import FaithfulPatchError
from .game import (
    ensure_backup,
    patch_string_bundle_catalog_crc,
    resolve_auto_game_paths,
    restore_backups,
    sha256_file,
    validate_game_root,
    write_patch_state,
)
from .patching import patch_story_file, patch_string_bundle
from .translations import load_translations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yunyun-faithful-english-patch",
        description="Apply or inspect the Yunyun Faithful English Patch.",
    )
    parser.add_argument("--game-root", type=Path, default=None, help="Game root folder")
    parser.add_argument(
        "--translations",
        type=Path,
        default=None,
        help="Directory containing story.en.json and strings.en.json",
    )
    parser.add_argument("--check", action="store_true", help="Validate inputs without patching")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report patch counts without writing",
    )
    parser.add_argument("--restore", action="store_true", help="Restore files from patch backups")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow unknown target file hashes after all other sanity checks pass",
    )
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            return run_self_test(args)
        return run(args)
    except FaithfulPatchError as exc:
        parser.exit(2, f"error: {exc}\n")


def run_self_test(args: argparse.Namespace) -> int:
    if UnityPy.__name__ != "UnityPy":
        raise AssertionError("Unexpected UnityPy import state")
    importlib.resources.files("UnityPy.resources")
    load_translations(args.translations)
    print("Self-test passed.")
    return 0


def run(args: argparse.Namespace) -> int:
    paths, auto_discovered = resolve_auto_game_paths(args.game_root)
    translations = load_translations(args.translations)
    if auto_discovered:
        print(f"Using game root: {paths.root}", flush=True)

    if args.restore:
        validate_game_root(
            paths,
            force=True,
            require_hash_match=False,
        )
        restored = restore_backups(paths)
        if restored:
            for path in restored:
                print(f"Restored {path.relative_to(paths.root)}")
        else:
            print("No backups found.")
        return 0

    warnings = validate_game_root(paths, force=args.force)
    for warning in warnings:
        print(f"warning: {warning}")

    if args.check:
        print("Game root sanity checks passed.")
        return 0

    if not args.dry_run:
        ensure_backup(paths.backup_dir, paths.data_unity3d)
        ensure_backup(paths.backup_dir, paths.string_bundle)
        ensure_backup(paths.backup_dir, paths.catalog_bin)

    story_stats = patch_story_file(
        paths.data_unity3d,
        translations.story,
        dry_run=args.dry_run,
    )
    string_stats = patch_string_bundle(
        paths.string_bundle,
        translations.strings,
        dry_run=args.dry_run,
    )

    catalog_crc_patched = False
    if not args.dry_run:
        catalog_crc_patched = patch_string_bundle_catalog_crc(paths.catalog_bin)

    print(story_stats.summary())
    print(string_stats.summary())
    if catalog_crc_patched:
        print("catalog: disabled stock CRC for English string-table bundle")
    if args.dry_run:
        print("Dry run complete; no files were changed.")
        return 0

    write_patch_state(
        paths.backup_dir,
        {
            "project": PROJECT_NAME,
            "version": __version__,
            "patched_at": datetime.now(UTC).isoformat(),
            "patched_files": {
                "data.unity3d": {
                    "size": paths.data_unity3d.stat().st_size,
                    "sha256": sha256_file(paths.data_unity3d),
                },
                STRING_BUNDLE.as_posix(): {
                    "size": paths.string_bundle.stat().st_size,
                    "sha256": sha256_file(paths.string_bundle),
                },
                CATALOG_BIN.as_posix(): {
                    "size": paths.catalog_bin.stat().st_size,
                    "sha256": sha256_file(paths.catalog_bin),
                },
            },
            "stats": {
                "story": stats_to_json(story_stats),
                "strings": stats_to_json(string_stats),
            },
        },
    )
    print("Patch applied.")
    return 0


def stats_to_json(stats: object) -> dict[str, object]:
    return {
        "changed": stats.changed,
        "matched": stats.matched,
        "missing_entries": list(stats.missing_entries),
        "missing_tables": sorted(stats.missing_tables),
        "target": stats.target,
        "tables_seen": sorted(stats.tables_seen),
        "unchanged": stats.unchanged,
    }


if __name__ == "__main__":
    raise SystemExit(main())
