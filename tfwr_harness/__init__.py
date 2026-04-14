"""Local TFWR harness scaffold.

This package runs TFWR-like scripts under CPython with a synthetic builtin shim.
It is intentionally not a full reimplementation of the game's language.

Modules that should aim to mirror in-game behavior over time:
- ``models``
- ``runtime``
- ``builtin_shim``
- ``traces``

Harness-only helper modules:
- ``cli``
- ``loader``
- ``parity``
- ``scenarios``
- ``validator``
"""

from .cli import main

__all__ = ["main"]
