"""Harness-specific error types.

Errors in this module are harness-only. They provide clearer failure modes than
the game itself so scaffolded tooling and tests can distinguish unsupported
features from invalid manifests and parity regressions.
"""


class HarnessError(Exception):
    """Base exception for harness failures."""


class UnsupportedFeatureError(HarnessError):
    """Raised when a requested TFWR feature is not implemented by the harness."""


class InvalidScenarioError(HarnessError):
    """Raised when a scenario manifest is missing required fields or is malformed."""


class ParityMismatchError(HarnessError):
    """Raised when harness behavior diverges from a declared golden expectation."""


class StrictModeInvalidActionError(HarnessError):
    """Raised when strict mode rejects an in-game action that would normally fail softly."""


class StaticValidationError(HarnessError):
    """Raised when static TFWR validation finds blocking issues before execution."""
