from __future__ import annotations


class FaithfulPatchError(RuntimeError):
    """Base exception for user-facing CLI failures."""


class ValidationError(FaithfulPatchError):
    """The selected game root or input files are not safe to patch."""


class HashMismatchError(ValidationError):
    """One or more target files did not match known safe hashes."""

    def __init__(self, mismatches: list[str]) -> None:
        self.mismatches = mismatches
        super().__init__(
            "target file hashes are not recognized; use --force only if this "
            "game version is expected"
        )


class PatchError(FaithfulPatchError):
    """The patch could not be applied cleanly."""
