from __future__ import annotations

import sys
from pathlib import Path

BANNED_SUFFIXES = {
    ".asset",
    ".assets",
    ".bundle",
    ".dll",
    ".exe",
    ".jpeg",
    ".jpg",
    ".meta",
    ".mp3",
    ".mp4",
    ".msi",
    ".ogg",
    ".pdf",
    ".png",
    ".prefab",
    ".raw.jsonl",
    ".resS",
    ".resource",
    ".unity3d",
    ".wav",
}

BANNED_MAGIC = {
    b"UnityFS\x00": "UnityFS asset bundle",
    b"MZ": "Windows binary",
    b"%PDF": "PDF",
    b"\x89PNG": "PNG",
    b"OggS": "Ogg media",
}

SKIPPED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "extracted",
    "probe",
    "work",
}


def main() -> int:
    failures: list[str] = []
    root = Path.cwd()

    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)

        if path.is_dir() or any(part in SKIPPED_DIRS for part in rel.parts):
            continue

        lower_name = path.name.lower()
        if any(lower_name.endswith(suffix) for suffix in BANNED_SUFFIXES):
            failures.append(f"{rel}: banned file type")

        with path.open("rb") as handle:
            head = handle.read(16)

        for magic, label in BANNED_MAGIC.items():
            if head.startswith(magic):
                failures.append(f"{rel}: looks like {label}")

    if failures:
        print("Repository file check failed:", file=sys.stderr)
        print("\n".join(f"  - {failure}" for failure in failures), file=sys.stderr)
        return 1

    print("Repository file check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
