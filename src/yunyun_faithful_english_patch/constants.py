from __future__ import annotations

from pathlib import Path

PROJECT_NAME = "Yunyun Faithful English Patch"
GAME_TITLE = "Yunyun Syndrome!? Rhythm Psychosis"
TARGET_LOCALE = "en"

DATA_DIR = Path("Yunyun_Syndrome_Data")
APP_INFO = DATA_DIR / "app.info"
EXE_NAME = "Yunyun_Syndrome.exe"
DATA_UNITY3D = DATA_DIR / "data.unity3d"
CATALOG_BIN = DATA_DIR / "StreamingAssets" / "aa" / "catalog.bin"
STRING_BUNDLE = (
    DATA_DIR
    / "StreamingAssets"
    / "aa"
    / "StandaloneWindows64"
    / "localization-string-tables-english(en)_assets_all.bundle"
)
KNOWN_GAME_FILES = {
    "data.unity3d": {
        "sha256": "e7a27107dc53abff221b59d3cb31f719cb1457bd14991810f361137f4ca63f52",
        "size": 549650621,
    },
    STRING_BUNDLE.as_posix(): {
        "sha256": "119f3e9180aa94aa4392c8c57a6e34ad98afc0463c953fd8c5b4660e1be93ba0",
        "size": 151129,
    },
}
BACKUP_DIR = DATA_DIR / ".yunyun_faithful_english_patch_backups"
STATE_FILE = "patch_state.json"

EXPECTED_APP_INFO = ("AllianceArts", "Yunyun_Syndrome")
