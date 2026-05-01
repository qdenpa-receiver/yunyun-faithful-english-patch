from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from yunyun_faithful_english_patch.errors import ValidationError
from yunyun_faithful_english_patch.game import (
    backup_path_for,
    ensure_backup,
    file_identity,
)


class EnsureBackupTests(unittest.TestCase):
    def test_existing_backup_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.bin"
            backup_dir = root / "backups"
            target.write_bytes(b"current")
            backup_dir.mkdir()
            backup = backup_path_for(backup_dir, target)
            backup.write_bytes(b"original")

            self.assertEqual(ensure_backup(backup_dir, target), backup)
            self.assertEqual(backup.read_bytes(), b"original")

    def test_missing_backup_is_created_from_known_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.bin"
            backup_dir = root / "backups"
            target.write_bytes(b"original")

            with mock.patch.dict(
                "yunyun_faithful_english_patch.game.KNOWN_GAME_FILES",
                {"manifest-target": file_identity(target)},
            ):
                backup = ensure_backup(
                    backup_dir,
                    target,
                    manifest_key="manifest-target",
                )

            self.assertEqual(backup.read_bytes(), b"original")

    def test_missing_backup_for_patched_state_target_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.bin"
            backup_dir = root / "backups"
            target.write_bytes(b"patched")
            state = {"patched_files": {"manifest-target": file_identity(target)}}

            with self.assertRaisesRegex(ValidationError, "already matches a previous patch"):
                ensure_backup(
                    backup_dir,
                    target,
                    manifest_key="manifest-target",
                    state=state,
                )


if __name__ == "__main__":
    unittest.main()
