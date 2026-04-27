from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from io import IOBase
from pathlib import Path
from typing import Any

from .constants import (
    APP_INFO,
    BACKUP_DIR,
    CATALOG_BIN,
    DATA_UNITY3D,
    EXE_NAME,
    EXPECTED_APP_INFO,
    KNOWN_GAME_FILES,
    STATE_FILE,
    STRING_BUNDLE,
    STRING_BUNDLE_STOCK_CATALOG_CRC,
)
from .errors import HashMismatchError, ValidationError

STEAM_GAME_DIR = "Yunyun_Syndrome"


@dataclass(frozen=True)
class GamePaths:
    root: Path
    app_info: Path
    data_unity3d: Path
    string_bundle: Path
    catalog_bin: Path
    backup_dir: Path


def resolve_game_paths(game_root: Path | str) -> GamePaths:
    root = Path(game_root).expanduser().resolve()
    return GamePaths(
        root=root,
        app_info=root / APP_INFO,
        data_unity3d=root / DATA_UNITY3D,
        string_bundle=root / STRING_BUNDLE,
        catalog_bin=root / CATALOG_BIN,
        backup_dir=root / BACKUP_DIR,
    )


def resolve_auto_game_paths(game_root: Path | str | None) -> tuple[GamePaths, bool]:
    if game_root is not None:
        return resolve_game_paths(game_root), False

    cwd = Path.cwd()
    for candidate in iter_game_root_candidates(cwd=cwd):
        if has_game_root_markers(candidate):
            return resolve_game_paths(candidate), True

    return resolve_game_paths(cwd), False


def iter_game_root_candidates(
    *,
    cwd: Path | None = None,
    executable: Path | None = None,
    package_file: Path | None = None,
    home: Path | None = None,
    system: str | None = None,
) -> list[Path]:
    cwd = cwd or Path.cwd()
    executable = executable or Path(sys.executable)
    package_file = package_file or Path(__file__)
    home = home or Path.home()
    system = system or platform.system()

    anchors = [
        cwd,
        executable.expanduser().resolve().parent,
        package_file.expanduser().resolve().parent,
    ]
    candidates = [cwd]
    for anchor in anchors:
        candidates.extend(
            [
                anchor.parent / "Steam" / "steamapps" / "common" / STEAM_GAME_DIR,
                anchor.parent / "steamapps" / "common" / STEAM_GAME_DIR,
            ]
        )
    candidates.extend(default_steam_game_roots(home=home, system=system))
    return dedupe_paths(candidates)


def default_steam_game_roots(*, home: Path, system: str) -> list[Path]:
    if system == "Windows":
        return [
            Path("C:/Program Files (x86)/Steam/steamapps/common") / STEAM_GAME_DIR,
            Path("C:/Program Files/Steam/steamapps/common") / STEAM_GAME_DIR,
        ]
    if system == "Darwin":
        return [
            home
            / "Library"
            / "Application Support"
            / "Steam"
            / "steamapps"
            / "common"
            / STEAM_GAME_DIR
        ]
    return [
        home / ".steam" / "steam" / "steamapps" / "common" / STEAM_GAME_DIR,
        home / ".local" / "share" / "Steam" / "steamapps" / "common" / STEAM_GAME_DIR,
    ]


def dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    deduped: list[Path] = []
    for path in paths:
        normalized = path.expanduser().resolve(strict=False)
        key = os.path.normcase(str(normalized))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def has_game_root_markers(root: Path) -> bool:
    paths = resolve_game_paths(root)
    return all(
        path.exists()
        for path in (
            paths.root / EXE_NAME,
            paths.app_info,
            paths.data_unity3d,
            paths.string_bundle,
            paths.catalog_bin,
        )
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path: Path) -> dict[str, int | str]:
    return {
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def validate_game_root(
    paths: GamePaths,
    *,
    force: bool = False,
    require_hash_match: bool = True,
) -> list[str]:
    warnings: list[str] = []
    required = [
        paths.root / EXE_NAME,
        paths.app_info,
        paths.data_unity3d,
        paths.string_bundle,
        paths.catalog_bin,
    ]
    missing = [str(path.relative_to(paths.root)) for path in required if not path.exists()]
    if missing:
        raise ValidationError(
            "Not a recognized game root; missing: "
            + ", ".join(missing)
            + ". Run from the Yunyun_Syndrome game folder or pass "
            + "--game-root /path/to/Yunyun_Syndrome."
        )

    app_info = tuple(paths.app_info.read_text(encoding="utf-8", errors="replace").splitlines()[:2])
    if app_info != EXPECTED_APP_INFO:
        raise ValidationError(
            f"Unexpected app.info contents: {app_info!r}; expected {EXPECTED_APP_INFO!r}"
        )

    assert_unityfs(paths.data_unity3d)
    assert_unityfs(paths.string_bundle)
    assert_catalog_allows_local_bundle(paths.catalog_bin)

    if require_hash_match:
        state = read_patch_state(paths.backup_dir)
        check_known_hashes(paths, state=state, force=force, warnings=warnings)

    return warnings


def assert_unityfs(path: Path) -> None:
    with path.open("rb") as handle:
        if handle.read(8) != b"UnityFS\x00":
            raise ValidationError(f"{path.name} is not a UnityFS file")


def assert_catalog_allows_local_bundle(catalog_bin: Path) -> None:
    data = catalog_bin.read_bytes()
    if STRING_BUNDLE.name.encode("utf-8") not in data:
        raise ValidationError("Addressables catalog does not reference the English string bundle")


def patch_string_bundle_catalog_crc(catalog_bin: Path) -> bool:
    data = bytearray(catalog_bin.read_bytes())
    bundle_name = STRING_BUNDLE.name.encode("utf-8")
    bundle_pos = bytes(data).find(bundle_name)
    if bundle_pos < 0:
        raise ValidationError("Addressables catalog does not reference the English string bundle")

    old_crc = STRING_BUNDLE_STOCK_CATALOG_CRC.to_bytes(4, "little")
    matches: list[int] = []
    start = 0
    blob = bytes(data)
    while True:
        pos = blob.find(old_crc, start)
        if pos < 0:
            break
        matches.append(pos)
        start = pos + 1

    if not matches:
        return False

    nearby = [pos for pos in matches if abs(pos - bundle_pos) <= 4096]
    if len(nearby) != 1:
        raise ValidationError(
            "Could not safely locate the English string bundle CRC in catalog.bin; "
            f"found {len(matches)} possible stock-CRC matches"
        )

    data[nearby[0] : nearby[0] + 4] = b"\x00\x00\x00\x00"
    atomic_write_bytes(catalog_bin, bytes(data))
    return True


def check_known_hashes(
    paths: GamePaths,
    *,
    state: dict[str, Any] | None,
    force: bool,
    warnings: list[str],
) -> None:
    mismatches: list[str] = []
    targets = {
        "data.unity3d": paths.data_unity3d,
        STRING_BUNDLE.as_posix(): paths.string_bundle,
        CATALOG_BIN.as_posix(): paths.catalog_bin,
    }
    for manifest_key, path in targets.items():
        info = KNOWN_GAME_FILES.get(manifest_key)
        if not info:
            warnings.append(f"No known hash for {manifest_key}")
            continue
        identity = file_identity(path)
        original_match = identity == info
        patched_match = bool(
            state
            and state.get("patched_files", {}).get(manifest_key, {}) == identity
        )
        if original_match or patched_match:
            continue
        message = (
            f"{manifest_key} hash is not a known original or patch output "
            f"(size={identity['size']}, sha256={identity['sha256']})"
        )
        if force:
            warnings.append(message + " (--force accepted)")
        else:
            mismatches.append(message)

    if mismatches:
        raise HashMismatchError(mismatches)


def file_matches_patch_state(
    state: dict[str, Any] | None,
    manifest_key: str,
    path: Path,
) -> bool:
    return bool(
        state and state.get("patched_files", {}).get(manifest_key, {}) == file_identity(path)
    )


def read_patch_state(backup_dir: Path) -> dict[str, Any] | None:
    state_path = backup_dir / STATE_FILE
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid patch state file: {state_path}") from exc


def write_patch_state(backup_dir: Path, state: dict[str, Any]) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(
        backup_dir / STATE_FILE,
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n",
    )


def backup_path_for(backup_dir: Path, target: Path) -> Path:
    return backup_dir / f"{target.name}.orig"


def ensure_backup(backup_dir: Path, target: Path, *, refresh: bool = False) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_path_for(backup_dir, target)
    if refresh or not backup_path.exists():
        shutil.copy2(target, backup_path)
    return backup_path


def restore_backups(paths: GamePaths) -> list[Path]:
    restored: list[Path] = []
    for target in (paths.data_unity3d, paths.string_bundle, paths.catalog_bin):
        backup = backup_path_for(paths.backup_dir, target)
        if backup.exists():
            shutil.copy2(backup, target)
            restored.append(target)
    state_path = paths.backup_dir / STATE_FILE
    if state_path.exists():
        state_path.unlink()
    return restored


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        tmp = Path(tmp_name)
        if tmp.exists():
            tmp.unlink()


def atomic_write_with_writer(path: Path, write_func: Callable[[IOBase], None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            write_func(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        tmp = Path(tmp_name)
        if tmp.exists():
            tmp.unlink()
