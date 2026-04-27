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
STRING_BUNDLE_STOCK_CATALOG_CRC = 0x2395DCDE
KNOWN_GAME_FILES = {
    "data.unity3d": {
        "sha256": "2a0937f78d3264f62ec2233c0844d32dd064e07192c68d37c47e9601131c5988",
        "size": 551642177,
    },
    STRING_BUNDLE.as_posix(): {
        "sha256": "80dd16595e13e0c0fc134c38292320f0503f27ae2235c128917e0e43e2c64726",
        "size": 151321,
    },
    CATALOG_BIN.as_posix(): {
        "sha256": "acdf34549f8f5b96b4a5399a7991d15fd73db6780b3122f661d08f0207e193f0",
        "size": 90183,
    },
}
BACKUP_DIR = DATA_DIR / ".yunyun_faithful_english_patch_backups"
STATE_FILE = "patch_state.json"

EXPECTED_APP_INFO = ("AllianceArts", "Yunyun_Syndrome")
