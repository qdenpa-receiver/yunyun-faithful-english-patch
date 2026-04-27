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
STRING_BUNDLE_STOCK_CATALOG_CRC = 0x23F45A9C
KNOWN_GAME_FILES = {
    "data.unity3d": {
        "sha256": "e7a27107dc53abff221b59d3cb31f719cb1457bd14991810f361137f4ca63f52",
        "size": 549650621,
    },
    STRING_BUNDLE.as_posix(): {
        "sha256": "119f3e9180aa94aa4392c8c57a6e34ad98afc0463c953fd8c5b4660e1be93ba0",
        "size": 151129,
    },
    CATALOG_BIN.as_posix(): {
        "sha256": "94a1bd2f69532cae24981df0189929223e2ddd100e702b402d9bcb685737ad69",
        "size": 90183,
    },
}
BACKUP_DIR = DATA_DIR / ".yunyun_faithful_english_patch_backups"
STATE_FILE = "patch_state.json"

EXPECTED_APP_INFO = ("AllianceArts", "Yunyun_Syndrome")
