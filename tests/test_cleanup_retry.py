from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from yunyun_faithful_english_patch.patching import cleanup_temp_dir_with_retry


class CleanupTempDirWithRetryTests(unittest.TestCase):
    def test_cleanup_succeeds_immediately(self) -> None:
        with mock.patch("yunyun_faithful_english_patch.patching.shutil.rmtree") as rmtree:
            cleanup_temp_dir_with_retry(Path("tmp"), attempts=3, delay_seconds=0)

        rmtree.assert_called_once_with(Path("tmp"))

    def test_cleanup_retries_transient_permission_error(self) -> None:
        with (
            mock.patch(
                "yunyun_faithful_english_patch.patching.shutil.rmtree",
                side_effect=[PermissionError("locked"), None],
            ) as rmtree,
            mock.patch("yunyun_faithful_english_patch.patching.gc.collect") as collect,
            mock.patch("yunyun_faithful_english_patch.patching.time.sleep") as sleep,
        ):
            cleanup_temp_dir_with_retry(Path("tmp"), attempts=3, delay_seconds=0.25)

        self.assertEqual(rmtree.call_count, 2)
        collect.assert_called_once_with()
        sleep.assert_called_once_with(0.25)

    def test_cleanup_raises_after_retry_exhaustion(self) -> None:
        error = PermissionError("locked")
        with (
            mock.patch(
                "yunyun_faithful_english_patch.patching.shutil.rmtree",
                side_effect=error,
            ),
            mock.patch("yunyun_faithful_english_patch.patching.gc.collect"),
            mock.patch("yunyun_faithful_english_patch.patching.time.sleep") as sleep,
        ):
            with self.assertRaises(PermissionError) as raised:
                cleanup_temp_dir_with_retry(Path("tmp"), attempts=3, delay_seconds=0.25)

        self.assertIs(raised.exception, error)
        self.assertEqual(sleep.call_args_list, [mock.call(0.25), mock.call(0.5)])


if __name__ == "__main__":
    unittest.main()
