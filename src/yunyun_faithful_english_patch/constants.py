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
STRING_BUNDLE_STOCK_CATALOG_CRC = 0x871A01E0
KNOWN_GAME_FILES = {
    "data.unity3d": {
        "sha256": "d241c55d8658aa5d0031ee1cf783cb4bef3871945251dc54c45f132e4abe8516",
        "size": 552455802,
    },
    STRING_BUNDLE.as_posix(): {
        "sha256": "59b6d64ca32d22be09ef3c9f65c882afad00fb3a38ac2434a1d2382709c74011",
        "size": 151438,
    },
    CATALOG_BIN.as_posix(): {
        "sha256": "abd675d4315a93119e4f16aa48290b5fde4e3fd77b8126fd7fce1a1095c69023",
        "size": 90183,
    },
}
BACKUP_DIR = DATA_DIR / ".yunyun_faithful_english_patch_backups"
STATE_FILE = "patch_state.json"

EXPECTED_APP_INFO = ("AllianceArts", "Yunyun_Syndrome")
