"""Core runtime and scenario models for the TFWR harness.

The data structures in this module should be kept close to the game concepts
they represent. A few fields, such as ``metadata`` and scenario assertions, are
harness-only helpers that make debugging and fixture authoring practical under
CPython.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
import random
from typing import Any

from .traces import TraceEvent


class RunStatus(StrEnum):
    """Normalized run outcome states used by the harness."""

    COMPLETED = "completed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class ScenarioMode(StrEnum):
    """Execution modes supported by Phase 7 scenario manifests."""

    NORMAL = "normal"
    SIMULATE = "simulate"
    LEADERBOARD = "leaderboard"


@dataclass(slots=True)
class EntityState:
    """State for the entity currently occupying a tile.

    ``entity_type`` should eventually mirror the TFWR enum names exposed to
    scripts. ``metadata`` is a harness-only escape hatch for entity mechanics
    that need extra bookkeeping without destabilizing the base model.
    """

    entity_type: str | None = None
    growth: float = 0.0
    required_growth: float | None = None
    planted_tick: int | None = None
    planted_seconds: float | None = None
    mature: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TileState:
    """Mutable state for a single farm tile."""

    ground_type: str = "Grounds.Grassland"
    entity: EntityState | None = None
    water: float = 0.0
    last_updated_tick: int = 0
    last_updated_seconds: float = 0.0
    next_water_decay_seconds: float | None = None
    water_decay_steps: int = 0
    flags: set[str] = field(default_factory=set)


@dataclass(slots=True)
class GameState:
    """Top-level runtime state for a single-drone harness run.

    This model is intended to mirror the board, inventory, unlocks, timing, and
    current drone location as closely as practical. ``notes`` is harness-only
    debug context and should not be treated as part of game parity.
    """

    world_size: int = 1
    drone_x: int = 0
    drone_y: int = 0
    tiles: list[list[TileState]] = field(default_factory=list)
    inventory: dict[str, float] = field(default_factory=dict)
    unlocks: dict[str, int] = field(default_factory=dict)
    tick_count: int = 0
    elapsed_seconds: float = 0.0
    speed_level: int = 0
    execution_speed: float = 0.0
    active_power: float = 0.0
    current_hat: str | None = None
    scenario_limits: dict[str, Any] = field(default_factory=dict)
    rng_seed: int | None = None
    rng_state: object | None = None
    random_calls: int = 0
    strict_mode: bool = False
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Ensure the tile grid matches the configured world size."""
        if self.world_size <= 0:
            raise ValueError("world_size must be positive")
        if self.speed_level < 0:
            raise ValueError("speed_level must be non-negative")

        if not self.tiles:
            self.tiles = self._build_square_tiles(self.world_size)
        elif len(self.tiles) != self.world_size:
            raise ValueError("tile row count must match world_size")
        else:
            for row in self.tiles:
                if len(row) != self.world_size:
                    raise ValueError("tile column count must match world_size")

        self.drone_x %= self.world_size
        self.drone_y %= self.world_size

        if self.rng_seed is None:
            self.rng_seed = 0
        if self.rng_state is None:
            self.rng_state = random.Random(self.rng_seed).getstate()

    @staticmethod
    def _build_square_tiles(world_size: int) -> list[list[TileState]]:
        return [
            [TileState() for _column in range(world_size)]
            for _row in range(world_size)
        ]


@dataclass(slots=True)
class ScenarioAssertion:
    """A declarative assertion loaded from a scenario manifest."""

    path: str
    expected: Any
    operator: str = "equals"


@dataclass(slots=True)
class Scenario:
    """Declarative input for a harness run.

    The manifest fields should stay stable and reusable across scenarios. The
    ``metadata`` and ``notes`` fields are harness-only authoring aids.
    """

    name: str
    script_path: Path
    description: str = ""
    manifest_path: Path | None = None
    manifest_version: int = 1
    mode: ScenarioMode = ScenarioMode.NORMAL
    mode_source: str = "manifest"
    entrypoint: str | None = None
    preset: str | None = None
    seed: int | None = None
    speedup: float = 0.0
    strict_mode: bool = False
    args: list[str] = field(default_factory=list)
    globals: dict[str, Any] = field(default_factory=dict)
    initial_state: GameState = field(default_factory=GameState)
    assertions: list[ScenarioAssertion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RunResult:
    """Normalized result returned by the harness after a run attempt."""

    scenario_name: str
    status: RunStatus
    success: bool = False
    tick_count: int = 0
    elapsed_seconds: float = 0.0
    return_value: Any = None
    events: list[TraceEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    final_state: GameState | None = None
    script_path: Path | None = None
