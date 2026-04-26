from __future__ import annotations


class FaithfulPatchError(RuntimeError):
    """Base exception for user-facing CLI failures."""


class ValidationError(FaithfulPatchError):
    """The selected game root or input files are not safe to patch."""


class PatchError(FaithfulPatchError):
    """The patch could not be applied cleanly."""
