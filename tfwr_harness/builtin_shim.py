"""Synthetic builtin shim registry for harness execution.

Registered builtin names should eventually mirror the game's callable surface
and return values. Registry helpers are harness-only scaffolding that let the
runtime assemble a synthetic namespace incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True, frozen=True)
class BuiltinSpec:
    """Metadata about a builtin exposed by the harness."""

    name: str
    mirror_in_game: bool = True
    implemented: bool = False
    notes: str = ""


class BuiltinShim:
    """Registry-backed synthetic builtin module contents."""

    def __init__(self) -> None:
        self.namespace: dict[str, Any] = {}
        self._specs: dict[str, BuiltinSpec] = {}

    def register(
        self,
        name: str,
        value: Callable[..., Any] | Any,
        *,
        mirror_in_game: bool = True,
        implemented: bool = False,
        notes: str = "",
    ) -> None:
        """Register a synthetic builtin name and its metadata."""
        self.namespace[name] = value
        self._specs[name] = BuiltinSpec(
            name=name,
            mirror_in_game=mirror_in_game,
            implemented=implemented,
            notes=notes,
        )

    def is_implemented(self, name: str) -> bool:
        """Return whether a registered builtin is backed by runtime behavior."""
        spec = self._specs.get(name)
        return False if spec is None else spec.implemented

    def snapshot_specs(self) -> list[BuiltinSpec]:
        """Return builtin metadata in stable name order."""
        return [self._specs[name] for name in sorted(self._specs)]
