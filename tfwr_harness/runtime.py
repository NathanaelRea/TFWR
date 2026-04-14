"""Runtime orchestration scaffolding for the TFWR harness.

The runtime coordinates game-like state, builtin shims, and normalized tracing.
This module should evolve toward game-parity behavior, while convenience
configuration such as print capture remains harness-only.
"""

from __future__ import annotations

import builtins as pybuiltins
import copy
from dataclasses import dataclass, field
import math
from pathlib import Path
import random
import traceback
from types import ModuleType
from typing import Any

from .builtin_shim import BuiltinShim
from .errors import StaticValidationError, StrictModeInvalidActionError, UnsupportedFeatureError
from .game_data import (
    ALWAYS_UNLOCKED_THINGS,
    DEFAULT_HAT,
    DIRECTION_DELTAS,
    ENTITY_SPECS,
    EXPAND_WORLD_SIZES,
    Grounds,
    Hats,
    Items,
    Leaderboards,
    MOVEMENT_BLOCKING_ENTITIES,
    North,
    East,
    South,
    UNLOCK_COSTS,
    West,
    THING_UNLOCK_REQUIREMENTS,
    Unlocks,
    Entities,
)
from .loader import LoadedScriptSource, WorkspaceModuleSet, discover_workspace_modules, load_script_source
from .models import EntityState, GameState, RunResult, RunStatus, Scenario, ScenarioMode, TileState
from .scenarios import build_preset_scenario
from .traces import TraceRecorder
from .validator import format_issues, has_blocking_issues, validate_source

BASE_TICKS_PER_SECOND = 400.0
SPEED_UPGRADE_FACTOR = 1.5
POWER_SPEED_MULTIPLIER = 2.0
SUCCESSFUL_ACTION_TICKS = 200
FAILED_ACTION_TICKS = 1
FIXED_DURATION_SECONDS = 1.0
WATER_DECAY_MIN_SECONDS = 0.8
WATER_DECAY_MAX_SECONDS = 1.2
WATER_DECAY_FACTOR = 0.99
POWER_SECONDS_PER_UNIT = 15.0
SUNFLOWER_MIN_PETALS = 7
SUNFLOWER_MAX_PETALS = 15
SUNFLOWER_MAX_BONUS_MULTIPLIER = 5.0
TREE_ADJACENCY_GROWTH_PENALTY = 0.25
DINO_BASE_MOVE_TICKS = 400
DINO_MOVE_DISCOUNT_PER_APPLE = 0.97
DINOSAUR_STATE_KEY = "_dinosaur"
SWAPPABLE_ENTITIES = {
    None,
    Entities.Grass,
    Entities.Bush,
    Entities.Tree,
    Entities.Carrot,
    Entities.Pumpkin,
    Entities.Dead_Pumpkin,
    Entities.Sunflower,
    Entities.Cactus,
    Entities.Apple,
}

SAFE_PYTHON_BUILTINS = {
    "__build_class__": pybuiltins.__build_class__,
    "AssertionError": pybuiltins.AssertionError,
    "Exception": pybuiltins.Exception,
    "False": False,
    "ImportError": pybuiltins.ImportError,
    "None": None,
    "RuntimeError": pybuiltins.RuntimeError,
    "True": True,
    "TypeError": pybuiltins.TypeError,
    "ValueError": pybuiltins.ValueError,
    "bool": pybuiltins.bool,
    "dict": pybuiltins.dict,
    "enumerate": pybuiltins.enumerate,
    "float": pybuiltins.float,
    "int": pybuiltins.int,
    "isinstance": pybuiltins.isinstance,
    "list": pybuiltins.list,
    "object": pybuiltins.object,
    "set": pybuiltins.set,
    "tuple": pybuiltins.tuple,
}


@dataclass(slots=True)
class RuntimeOptions:
    """Harness-only runtime configuration."""

    strict_mode: bool = False
    strict_validation: bool = False
    capture_prints: bool = True
    base_ticks_per_second: float = BASE_TICKS_PER_SECOND


@dataclass(slots=True)
class _ExecutionSession:
    """Isolated module loader and import environment for one harness run."""

    runtime: "HarnessRuntime"
    scenario: Scenario
    root_source: LoadedScriptSource
    workspace_modules: WorkspaceModuleSet
    synthetic_builtins: ModuleType = field(init=False)
    modules: dict[str, ModuleType] = field(init=False)
    python_builtins: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.synthetic_builtins = ModuleType("__builtins__")
        for name, value in self.runtime.build_namespace().items():
            setattr(self.synthetic_builtins, name, value)
        self.synthetic_builtins.__all__ = sorted(
            name for name in vars(self.synthetic_builtins) if not name.startswith("_")
        )

        self.modules: dict[str, ModuleType] = {
            "__builtins__": self.synthetic_builtins,
        }
        self.python_builtins = dict(SAFE_PYTHON_BUILTINS)
        self.python_builtins["__import__"] = self.import_module

    def import_module(
        self,
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] | list[str] | None = None,
        level: int = 0,
    ) -> ModuleType:
        """Restrict imports to sibling workspace modules plus synthetic builtins."""
        del globals, locals, fromlist

        if level != 0:
            raise UnsupportedFeatureError("relative imports are not supported by the harness")
        if name == "__builtins__":
            return self.synthetic_builtins
        if "." in name:
            raise UnsupportedFeatureError(
                f"dotted imports are not supported by the harness: {name}"
            )

        module_path = self.workspace_modules.resolve(name)
        if module_path is None:
            raise UnsupportedFeatureError(
                f"imports outside the scenario workspace are not supported: {name}"
            )
        return self.load_module(name)

    def build_module(self, module_name: str, module_path: Any) -> ModuleType:
        module = ModuleType(module_name)
        module.__file__ = str(module_path)
        module.__package__ = ""
        module.__builtins__ = self.python_builtins
        if module_name == self.root_source.module_name:
            module.__dict__.update(copy.deepcopy(self.scenario.globals))
        return module

    def load_module(self, module_name: str) -> ModuleType:
        """Load and execute one module under the run-local import cache."""
        cached = self.modules.get(module_name)
        if cached is not None:
            return cached

        module_path = self.workspace_modules.resolve(module_name)
        if module_path is None:
            raise ImportError(f"module not found in workspace: {module_name}")

        source = load_script_source(module_path)
        module = self.build_module(module_name, source.path)
        self.modules[module_name] = module
        self.runtime._record_event(
            category="runtime",
            name="module_import",
            payload={"module": module_name, "path": str(source.path)},
        )

        try:
            issues = validate_source(
                source.text,
                path=source.path,
            )
            if has_blocking_issues(
                issues,
                strict_warnings=self.runtime.options.strict_validation,
            ):
                raise StaticValidationError(
                    "\n".join(
                        format_issues(
                            issues,
                            strict_warnings=self.runtime.options.strict_validation,
                        )
                    )
                )

            code = compile(source.text, str(source.path), "exec")
            exec(code, module.__dict__)
        except Exception:
            self.modules.pop(module_name, None)
            raise
        return module

    def execute_root(self) -> ModuleType:
        """Execute the scenario entry script and return its module object."""
        return self.load_module(self.root_source.module_name)


class HarnessRuntime:
    """Coordinates runtime state, builtin registration, and trace capture."""

    def __init__(
        self,
        *,
        state: GameState | None = None,
        recorder: TraceRecorder | None = None,
        options: RuntimeOptions | None = None,
    ) -> None:
        self.state = GameState() if state is None else state
        self.recorder = TraceRecorder() if recorder is None else recorder
        self.options = RuntimeOptions() if options is None else options
        self.builtins = BuiltinShim()
        self._active_workspace_root: Path | None = None
        self._active_script_path: Path | None = None
        self._active_scenario: Scenario | None = None
        self._rng = random.Random()
        self.state.strict_mode = self.state.strict_mode or self.options.strict_mode
        self._restore_rng()
        self._register_core_values()
        self._register_phase_two_builtins()
        self._register_phase_three_builtins()
        self._register_phase_four_builtins()
        self._register_phase_seven_builtins()

    def build_namespace(self) -> dict[str, Any]:
        """Return the current synthetic builtin namespace."""
        return dict(self.builtins.namespace)

    def _register_core_values(self) -> None:
        self.builtins.register("Items", Items, implemented=True, notes="Enum-like namespace")
        self.builtins.register("Entities", Entities, implemented=True, notes="Enum-like namespace")
        self.builtins.register("Grounds", Grounds, implemented=True, notes="Enum-like namespace")
        self.builtins.register("Unlocks", Unlocks, implemented=True, notes="Enum-like namespace")
        self.builtins.register("Hats", Hats, implemented=True, notes="Enum-like namespace")
        self.builtins.register(
            "Leaderboards",
            Leaderboards,
            implemented=True,
            notes="Enum-like namespace",
        )
        self.builtins.register("North", North, implemented=True, notes="Direction constant")
        self.builtins.register("East", East, implemented=True, notes="Direction constant")
        self.builtins.register("South", South, implemented=True, notes="Direction constant")
        self.builtins.register("West", West, implemented=True, notes="Direction constant")

    def _register_phase_two_builtins(self) -> None:
        self.builtins.register(
            "get_time",
            self.get_time,
            implemented=True,
            notes="Phase 2 runtime clock",
        )
        self.builtins.register(
            "get_tick_count",
            self.get_tick_count,
            implemented=True,
            notes="Phase 2 runtime clock",
        )

    def _register_phase_three_builtins(self) -> None:
        for name, value, notes in [
            ("move", self.move, "Phase 3 movement"),
            ("can_move", self.can_move, "Phase 3 movement"),
            ("get_pos_x", self.get_pos_x, "Phase 3 sensor"),
            ("get_pos_y", self.get_pos_y, "Phase 3 sensor"),
            ("get_world_size", self.get_world_size, "Phase 3 sensor"),
            ("get_entity_type", self.get_entity_type, "Phase 3 sensor"),
            ("get_ground_type", self.get_ground_type, "Phase 3 sensor"),
            ("till", self.till, "Phase 3 terrain"),
            ("clear", self.clear, "Phase 3 terrain"),
            ("plant", self.plant, "Phase 3 planting"),
            ("harvest", self.harvest, "Phase 3 harvesting"),
            ("can_harvest", self.can_harvest, "Phase 3 harvesting"),
            ("num_items", self.num_items, "Phase 3 inventory"),
            ("use_item", self.use_item, "Phase 3 inventory"),
            ("get_cost", self.get_cost, "Phase 3 inventory"),
            ("unlock", self.unlock, "Phase 3 inventory"),
            ("num_unlocked", self.num_unlocked, "Phase 3 inventory"),
            ("set_execution_speed", self.set_execution_speed, "Phase 3 debug control"),
            ("set_world_size", self.set_world_size, "Phase 3 debug control"),
            ("change_hat", self.change_hat, "Phase 3 hat control"),
            ("print", self.print_text, "Phase 3 output"),
            ("quick_print", self.quick_print, "Phase 3 output"),
            ("random", self.random_builtin, "Phase 3 utility"),
            ("len", self.len_builtin, "Phase 3 utility"),
            ("range", self.range_builtin, "Phase 3 utility"),
            ("str", self.str_builtin, "Phase 3 utility"),
            ("min", self.min_builtin, "Phase 3 utility"),
            ("max", self.max_builtin, "Phase 3 utility"),
            ("abs", self.abs_builtin, "Phase 3 utility"),
        ]:
            self.builtins.register(name, value, implemented=True, notes=notes)

    def _register_phase_four_builtins(self) -> None:
        for name, value, notes in [
            ("get_water", self.get_water, "Phase 4 watering"),
            ("measure", self.measure, "Phase 4 crop measurement"),
            ("swap", self.swap, "Phase 4 cactus sorting"),
        ]:
            self.builtins.register(name, value, implemented=True, notes=notes)

    def _register_phase_seven_builtins(self) -> None:
        for name, value, notes in [
            ("simulate", self.simulate_builtin, "Phase 7 nested simulation"),
            ("leaderboard_run", self.leaderboard_run_builtin, "Phase 7 leaderboard preset runner"),
        ]:
            self.builtins.register(name, value, implemented=True, notes=notes)

    def _restore_rng(self) -> None:
        if self.state.rng_state is not None:
            self._rng.setstate(self.state.rng_state)
            return

        self._rng.seed(self.state.rng_seed)
        self.state.rng_state = self._rng.getstate()

    def _store_rng(self) -> None:
        self.state.rng_state = self._rng.getstate()

    def get_tick_count(self) -> int:
        """Return the current raw tick counter."""
        return self.state.tick_count

    def get_time(self) -> float:
        """Return the current derived elapsed time in seconds."""
        return self.state.elapsed_seconds

    def available_power(self) -> float:
        """Return the remaining active and stored power budget."""
        return pybuiltins.max(
            0.0,
            float(self.state.active_power) + self._inventory_amount(Items.Power),
        )

    def _drain_power_units(self, amount: float) -> None:
        if amount <= 0:
            return

        if self.state.active_power > 0:
            drained = pybuiltins.min(float(self.state.active_power), amount)
            self.state.active_power -= drained
            amount -= drained

        if amount <= 0:
            return

        self._set_inventory_amount(
            Items.Power,
            self._inventory_amount(Items.Power) - amount,
        )

    def speed_factor(self) -> float:
        """Return the multiplicative speed factor from upgrades and power."""
        factor = SPEED_UPGRADE_FACTOR ** self.state.speed_level
        if self.available_power() > 0:
            factor *= POWER_SPEED_MULTIPLIER
        return factor

    def _ticks_per_second_for_factor(self, factor: float) -> float:
        ticks_per_second = self.options.base_ticks_per_second * factor
        if self.state.execution_speed > 0:
            ticks_per_second = min(
                ticks_per_second,
                self.options.base_ticks_per_second * self.state.execution_speed,
            )
        return ticks_per_second

    def ticks_per_second(self) -> float:
        """Return the current effective tick throughput."""
        return self._ticks_per_second_for_factor(self.speed_factor())

    def seconds_for_ticks(self, ticks: int) -> float:
        """Translate ticks into elapsed seconds under the current speed state."""
        if ticks < 0:
            raise ValueError("ticks must be non-negative")
        return ticks / self.ticks_per_second()

    def advance_ticks(self, ticks: int, *, fixed_seconds: float | None = None) -> None:
        """Advance runtime time without eagerly updating every tile."""
        if ticks < 0:
            raise ValueError("ticks must be non-negative")

        self.state.tick_count += ticks
        if fixed_seconds is None:
            base_factor = SPEED_UPGRADE_FACTOR ** self.state.speed_level
            normal_tps = self._ticks_per_second_for_factor(base_factor)
            boosted_tps = self._ticks_per_second_for_factor(base_factor * POWER_SPEED_MULTIPLIER)
            power_seconds_available = self.available_power() * POWER_SECONDS_PER_UNIT

            if power_seconds_available <= 0 or boosted_tps <= normal_tps:
                self.state.elapsed_seconds += ticks / normal_tps
                return

            boosted_ticks_available = power_seconds_available * boosted_tps
            if ticks <= boosted_ticks_available:
                boosted_seconds = ticks / boosted_tps
                self.state.elapsed_seconds += boosted_seconds
                self._drain_power_units(boosted_seconds / POWER_SECONDS_PER_UNIT)
                return

            remaining_ticks = ticks - boosted_ticks_available
            self.state.elapsed_seconds += power_seconds_available + (remaining_ticks / normal_tps)
            self._drain_power_units(power_seconds_available / POWER_SECONDS_PER_UNIT)
            return

        if fixed_seconds < 0:
            raise ValueError("fixed_seconds must be non-negative")
        self.state.elapsed_seconds += fixed_seconds
        self._drain_power_units(fixed_seconds / POWER_SECONDS_PER_UNIT)

    def consume_success_ticks(self) -> None:
        """Apply the default 200-tick cost for successful fallible actions."""
        self.advance_ticks(SUCCESSFUL_ACTION_TICKS)

    def consume_failure_ticks(self) -> None:
        """Apply the default 1-tick cost for failed fallible actions."""
        self.advance_ticks(FAILED_ACTION_TICKS)

    def consume_fixed_duration_action(self) -> None:
        """Apply the fixed one-second duration used by print-like actions."""
        self.advance_ticks(0, fixed_seconds=FIXED_DURATION_SECONDS)

    def random_value(self) -> float:
        """Return a deterministic random number and persist the RNG state."""
        value = self._rng.random()
        self.state.random_calls += 1
        self._store_rng()
        return value

    def wrap_coordinate(self, coordinate: int) -> int:
        """Wrap a coordinate onto the current square farm."""
        return coordinate % self.state.world_size

    def get_tile(self, x: int, y: int, *, sync: bool = True) -> TileState:
        """Return a tile, optionally synchronizing its lazy state first."""
        wrapped_x = self.wrap_coordinate(x)
        wrapped_y = self.wrap_coordinate(y)
        if sync:
            return self.sync_tile(wrapped_x, wrapped_y)
        return self.state.tiles[wrapped_y][wrapped_x]

    def current_tile(self, *, sync: bool = True) -> TileState:
        """Return the tile currently under the drone."""
        return self.get_tile(self.state.drone_x, self.state.drone_y, sync=sync)

    def _record_event(
        self,
        *,
        category: str,
        name: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.recorder.record(
            tick=self.state.tick_count,
            seconds=self.state.elapsed_seconds,
            category=category,
            name=name,
            payload=payload,
        )

    def _normalize_cost(self, cost: dict[str, float] | None) -> dict[str, float] | None:
        if cost is None:
            return None
        return {item: float(amount) for item, amount in cost.items()}

    def _inventory_amount(self, item: str) -> float:
        return float(self.state.inventory.get(item, 0.0))

    def _set_inventory_amount(self, item: str, amount: float) -> None:
        if amount <= 0:
            self.state.inventory.pop(item, None)
            return
        self.state.inventory[item] = float(amount)

    def _can_afford_cost(self, cost: dict[str, float] | None) -> bool:
        if cost is None:
            return False
        for item, amount in cost.items():
            if self._inventory_amount(item) < float(amount):
                return False
        return True

    def _spend_cost(self, cost: dict[str, float]) -> None:
        for item, amount in cost.items():
            self._set_inventory_amount(item, self._inventory_amount(item) - float(amount))

    def _direction_delta(self, direction: Any) -> tuple[int, int] | None:
        if direction in DIRECTION_DELTAS:
            return DIRECTION_DELTAS[direction]
        return None

    def _strict_failure(
        self,
        message: str,
        *,
        return_value: Any = False,
        cost_kind: str = "failure",
    ) -> Any:
        if cost_kind == "failure":
            self.consume_failure_ticks()
        elif cost_kind == "success":
            self.consume_success_ticks()
        if self.state.strict_mode:
            raise StrictModeInvalidActionError(message)
        return return_value

    def _consume_sensor_tick(self, *, name: str, payload: dict[str, Any] | None = None) -> None:
        self.consume_failure_ticks()
        self._record_event(category="sensor", name=name, payload=payload)

    def _is_tile_blocked_for_movement(self, x: int, y: int) -> bool:
        tile = self.get_tile(x, y)
        if tile.entity is not None and tile.entity.entity_type in MOVEMENT_BLOCKING_ENTITIES:
            return True
        return "blocks_movement" in tile.flags

    def _expand_level(self) -> int:
        return int(self.state.unlocks.get(Unlocks.Expand, 0))

    def _unlocked_world_size(self) -> int:
        expand_level = self._expand_level()
        if expand_level in EXPAND_WORLD_SIZES:
            return EXPAND_WORLD_SIZES[expand_level]
        max_known_level = pybuiltins.max(EXPAND_WORLD_SIZES)
        if expand_level > max_known_level:
            return EXPAND_WORLD_SIZES[max_known_level]
        return self.state.world_size

    def _reset_field(self, *, world_size: int | None = None, reset_hat: bool = True) -> None:
        target_world_size = self.state.world_size if world_size is None else int(world_size)
        self.state.world_size = target_world_size
        self.state.tiles = GameState._build_square_tiles(target_world_size)
        self.state.drone_x = 0
        self.state.drone_y = 0
        self.state.scenario_limits.pop(DINOSAUR_STATE_KEY, None)
        if reset_hat:
            self.state.current_hat = DEFAULT_HAT

    def _thing_level(self, thing: str) -> int:
        if thing == Unlocks.Speed:
            return pybuiltins.max(int(self.state.unlocks.get(thing, 0)), self.state.speed_level)
        if thing == Unlocks.Expand:
            return self._current_unlock_level(thing)
        if thing in self.state.unlocks:
            return int(self.state.unlocks[thing])
        if thing in ALWAYS_UNLOCKED_THINGS:
            return 1
        required_unlock = THING_UNLOCK_REQUIREMENTS.get(thing)
        if required_unlock is None:
            return 0
        return 1 if int(self.state.unlocks.get(required_unlock, 0)) > 0 else 0

    def _current_unlock_level(self, thing: str) -> int:
        if thing == Unlocks.Speed:
            return pybuiltins.max(int(self.state.unlocks.get(thing, 0)), self.state.speed_level)
        if thing == Unlocks.Expand:
            reverse_sizes = {size: level for level, size in EXPAND_WORLD_SIZES.items()}
            return pybuiltins.max(
                int(self.state.unlocks.get(thing, 0)),
                reverse_sizes.get(self.state.world_size, 0),
            )
        return int(self.state.unlocks.get(thing, 0))

    def _entity_cost_scale(self, entity: str, spec: Any) -> int:
        if spec.cost_unlock is None:
            return 1
        unlock_level = self._thing_level(spec.cost_unlock)
        return 1 if unlock_level <= 0 else 2 ** (unlock_level - 1)

    def _current_entity_spec(self) -> Any | None:
        tile = self.current_tile()
        if tile.entity is None:
            return None
        return ENTITY_SPECS.get(tile.entity.entity_type)

    def _dinosaur_state(self) -> dict[str, Any]:
        state = self.state.scenario_limits.get(DINOSAUR_STATE_KEY)
        if state is None:
            state = {
                "tail": [],
                "apple_position": None,
                "next_apple_position": None,
                "apples_eaten": 0,
            }
            self.state.scenario_limits[DINOSAUR_STATE_KEY] = state
        return state

    def _clear_dinosaur_entities(self) -> None:
        for row in self.state.tiles:
            for tile in row:
                if tile.entity is None:
                    continue
                if tile.entity.entity_type in {Entities.Dinosaur, Entities.Apple}:
                    tile.entity = None
                    tile.last_updated_tick = self.state.tick_count
                    tile.last_updated_seconds = self.state.elapsed_seconds

    def _occupied_dinosaur_positions(self, dino_state: dict[str, Any]) -> set[tuple[int, int]]:
        occupied: set[tuple[int, int]] = set()
        for x, y in dino_state["tail"]:
            occupied.add((int(x), int(y)))
        return occupied

    def _dinosaur_free_positions(self, dino_state: dict[str, Any]) -> list[tuple[int, int]]:
        occupied = self._occupied_dinosaur_positions(dino_state)
        occupied.add((self.state.drone_x, self.state.drone_y))
        free_positions: list[tuple[int, int]] = []
        for y in range(self.state.world_size):
            for x in range(self.state.world_size):
                if (x, y) in occupied:
                    continue
                free_positions.append((x, y))
        return free_positions

    def _spawn_dinosaur_apple(self, dino_state: dict[str, Any]) -> bool:
        if dino_state["apple_position"] is not None:
            return True

        cost = self._cost_for_thing(Entities.Apple)
        free_positions = self._dinosaur_free_positions(dino_state)
        if not free_positions or cost is None or not self._can_afford_cost(cost):
            dino_state["next_apple_position"] = None
            return False

        spawn_index = int(dino_state["apples_eaten"]) % len(free_positions)
        apple_position = free_positions[spawn_index]
        next_position = None
        if len(free_positions) > 1:
            next_position = free_positions[(spawn_index + 1) % len(free_positions)]

        self._spend_cost(cost)
        self.set_tile_entity(
            apple_position[0],
            apple_position[1],
            EntityState(entity_type=Entities.Apple),
        )
        dino_state["apple_position"] = apple_position
        dino_state["next_apple_position"] = next_position
        return True

    def _dinosaur_move_cost_ticks(self) -> int:
        dino_state = self._dinosaur_state()
        apples_eaten = int(dino_state["apples_eaten"])
        return int(DINO_BASE_MOVE_TICKS * (DINO_MOVE_DISCOUNT_PER_APPLE**apples_eaten))

    def _can_move_dinosaur(self, target_x: int, target_y: int) -> bool:
        dino_state = self._dinosaur_state()
        if self._is_tile_blocked_for_movement(target_x, target_y):
            return False

        tail = [(int(x), int(y)) for x, y in dino_state["tail"]]
        current_entity = self.current_tile().entity
        growing = current_entity is not None and current_entity.entity_type == Entities.Apple
        if (target_x, target_y) not in tail:
            return True
        if growing or not tail:
            return False
        return (target_x, target_y) == tail[0]

    def _update_dinosaur_tail_after_move(self, target_x: int, target_y: int) -> None:
        dino_state = self._dinosaur_state()
        tail = [(int(x), int(y)) for x, y in dino_state["tail"]]
        current_x = self.state.drone_x
        current_y = self.state.drone_y
        current_tile = self.current_tile(sync=False)
        current_entity = current_tile.entity
        growing = current_entity is not None and current_entity.entity_type == Entities.Apple

        if not growing and tail:
            freed_x, freed_y = tail.pop(0)
            freed_tile = self.get_tile(freed_x, freed_y, sync=False)
            if (
                freed_tile.entity is not None
                and freed_tile.entity.entity_type == Entities.Dinosaur
            ):
                freed_tile.entity = None
                freed_tile.last_updated_tick = self.state.tick_count
                freed_tile.last_updated_seconds = self.state.elapsed_seconds

        if growing or tail:
            tail.append((current_x, current_y))
            self.set_tile_entity(
                current_x,
                current_y,
                EntityState(entity_type=Entities.Dinosaur, mature=True, required_growth=0.2, growth=0.2),
            )
        else:
            current_tile.entity = None
            current_tile.last_updated_tick = self.state.tick_count
            current_tile.last_updated_seconds = self.state.elapsed_seconds

        target_tile = self.get_tile(target_x, target_y, sync=False)
        landed_on_apple = (
            target_tile.entity is not None and target_tile.entity.entity_type == Entities.Apple
        )
        if not landed_on_apple and (
            target_tile.entity is not None and target_tile.entity.entity_type == Entities.Dinosaur
        ):
            target_tile.entity = None
            target_tile.last_updated_tick = self.state.tick_count
            target_tile.last_updated_seconds = self.state.elapsed_seconds

        self.state.drone_x = target_x
        self.state.drone_y = target_y
        dino_state["tail"] = tail

        if landed_on_apple:
            dino_state["apples_eaten"] = int(dino_state["apples_eaten"]) + 1
        elif growing:
            dino_state["apple_position"] = None
            self._spawn_dinosaur_apple(dino_state)

    def _harvest_dinosaur_tail(self) -> float:
        dino_state = self._dinosaur_state()
        tail_length = len(dino_state["tail"])
        if tail_length <= 0:
            self._clear_dinosaur_entities()
            dino_state["tail"] = []
            dino_state["apple_position"] = None
            dino_state["next_apple_position"] = None
            dino_state["apples_eaten"] = 0
            return 0.0

        bone_yield = float(tail_length**2) * self._yield_scale(Unlocks.Dinosaurs)
        self._apply_inventory_gain({Items.Bone: bone_yield})
        self._clear_dinosaur_entities()
        dino_state["tail"] = []
        dino_state["apple_position"] = None
        dino_state["next_apple_position"] = None
        dino_state["apples_eaten"] = 0
        return bone_yield

    def _enter_dinosaur_mode(self) -> None:
        dino_state = self._dinosaur_state()
        dino_state["tail"] = []
        dino_state["apple_position"] = None
        dino_state["next_apple_position"] = None
        dino_state["apples_eaten"] = 0
        self._clear_dinosaur_entities()
        self._spawn_dinosaur_apple(dino_state)

    def _yield_scale(
        self,
        unlock_name: str | None,
        *,
        zero_level_counts_as_upgrade: bool = False,
    ) -> float:
        if unlock_name is None:
            return 1.0
        level = self._current_unlock_level(unlock_name)
        if zero_level_counts_as_upgrade:
            return float(2**level)
        if level <= 0:
            return 1.0
        return float(2 ** (level - 1))

    def _seeded_value(
        self,
        x: int,
        y: int,
        salt: int,
        planted_tick: int | None = None,
    ) -> int:
        return (
            ((self.state.rng_seed or 0) * 1315423911)
            + ((x + 1) * 2654435761)
            + ((y + 1) * 2246822519)
            + (salt * 3266489917)
            + ((0 if planted_tick is None else planted_tick) * 668265263)
        ) & 0xFFFFFFFF

    def _assign_entity_metadata(self, x: int, y: int, entity: EntityState) -> None:
        if entity.entity_type == Entities.Sunflower and "petals" not in entity.metadata:
            entity.metadata["petals"] = SUNFLOWER_MIN_PETALS + (
                self._seeded_value(x, y, 11, entity.planted_tick)
                % (SUNFLOWER_MAX_PETALS - SUNFLOWER_MIN_PETALS + 1)
            )
        elif entity.entity_type == Entities.Cactus and "size" not in entity.metadata:
            entity.metadata["size"] = self._seeded_value(x, y, 23, entity.planted_tick) % 10
        elif entity.entity_type == Entities.Pumpkin and "dies_on_maturity" not in entity.metadata:
            entity.metadata["dies_on_maturity"] = (
                self._seeded_value(x, y, 37, entity.planted_tick) % 5
            ) == 0

    def _adjacent_coordinates(self, x: int, y: int) -> list[tuple[int, int]]:
        return [
            (self.wrap_coordinate(x + dx), self.wrap_coordinate(y + dy))
            for dx, dy in DIRECTION_DELTAS.values()
        ]

    def _tree_growth_multiplier(self, x: int, y: int) -> float:
        adjacent_trees = 0
        for neighbor_x, neighbor_y in self._adjacent_coordinates(x, y):
            neighbor = self.get_tile(neighbor_x, neighbor_y, sync=False)
            if neighbor.entity is None:
                continue
            if neighbor.entity.entity_type == Entities.Tree and not neighbor.entity.mature:
                adjacent_trees += 1
        return 1.0 / (1.0 + (adjacent_trees * TREE_ADJACENCY_GROWTH_PENALTY))

    def _ensure_passive_ground_entity(self, tile: TileState, x: int, y: int) -> None:
        if tile.entity is not None:
            return
        if tile.ground_type != Grounds.Grassland:
            return
        if "maze" in tile.flags:
            return

        grass_spec = ENTITY_SPECS[Entities.Grass]
        tile.entity = EntityState(
            entity_type=Entities.Grass,
            required_growth=grass_spec.required_growth,
            planted_tick=tile.last_updated_tick,
            planted_seconds=tile.last_updated_seconds,
            mature=False,
        )
        self._assign_entity_metadata(x, y, tile.entity)

    def _maze_treasure_position(self) -> tuple[int, int] | None:
        for y, row in enumerate(self.state.tiles):
            for x, tile in enumerate(row):
                if "maze" not in tile.flags or tile.entity is None:
                    continue
                if tile.entity.entity_type == Entities.Treasure:
                    return (x, y)
        return None

    def _count_entities(self, entity_type: str) -> int:
        count = 0
        for y in range(self.state.world_size):
            for x in range(self.state.world_size):
                tile = self.get_tile(x, y)
                if tile.entity is not None and tile.entity.entity_type == entity_type:
                    count += 1
        return count

    def _collect_component(self, x: int, y: int, predicate: Any) -> list[tuple[int, int]]:
        visited: set[tuple[int, int]] = set()
        pending = [(self.wrap_coordinate(x), self.wrap_coordinate(y))]

        while pending:
            current_x, current_y = pending.pop()
            if (current_x, current_y) in visited:
                continue
            if not predicate(current_x, current_y):
                continue
            visited.add((current_x, current_y))
            for neighbor_x, neighbor_y in self._adjacent_coordinates(current_x, current_y):
                if (neighbor_x, neighbor_y) not in visited:
                    pending.append((neighbor_x, neighbor_y))

        return list(visited)

    def _harvest_group(self, positions: list[tuple[int, int]]) -> None:
        for x, y in positions:
            tile = self.get_tile(x, y)
            tile.entity = None
            tile.last_updated_tick = self.state.tick_count
            tile.last_updated_seconds = self.state.elapsed_seconds

    def _default_harvest_items(self, entity: EntityState) -> dict[str, float]:
        if entity.entity_type == Entities.Grass:
            return {
                Items.Hay: self._yield_scale(
                    Unlocks.Grass,
                    zero_level_counts_as_upgrade=True,
                )
            }
        if entity.entity_type == Entities.Bush:
            return {Items.Wood: self._yield_scale(Unlocks.Trees)}
        if entity.entity_type == Entities.Tree:
            return {Items.Wood: 5.0 * self._yield_scale(Unlocks.Trees)}
        if entity.entity_type == Entities.Carrot:
            return {Items.Carrot: self._yield_scale(Unlocks.Carrots)}
        if entity.entity_type == Entities.Apple:
            return {Items.Bone: self._yield_scale(Unlocks.Dinosaurs)}
        return {}

    def _apply_inventory_gain(self, item_yield: dict[str, float]) -> None:
        for item, amount in item_yield.items():
            self._set_inventory_amount(item, self._inventory_amount(item) + float(amount))

    def _harvest_pumpkins(self, x: int, y: int) -> tuple[list[tuple[int, int]], dict[str, float]]:
        start_tile = self.get_tile(x, y)
        start_entity = start_tile.entity
        if start_entity is None or start_entity.entity_type != Entities.Pumpkin or not start_entity.mature:
            return ([(x, y)], {})

        component = self._collect_component(
            x,
            y,
            lambda tile_x, tile_y: (
                (self.get_tile(tile_x, tile_y).entity is not None)
                and self.get_tile(tile_x, tile_y).entity.entity_type == Entities.Pumpkin
                and self.get_tile(tile_x, tile_y).entity.mature
            ),
        )
        return (
            component,
            {
                Items.Pumpkin: float(len(component) ** 3)
                * self._yield_scale(Unlocks.Pumpkins)
            },
        )

    def _harvest_cactus_chain(self, x: int, y: int) -> tuple[list[tuple[int, int]], dict[str, float]]:
        start_tile = self.get_tile(x, y)
        start_entity = start_tile.entity
        if start_entity is None or start_entity.entity_type != Entities.Cactus or not start_entity.mature:
            return ([(x, y)], {})

        visited: set[tuple[int, int]] = set()
        pending = [(x, y)]
        while pending:
            current_x, current_y = pending.pop()
            if (current_x, current_y) in visited:
                continue

            current_tile = self.get_tile(current_x, current_y)
            current_entity = current_tile.entity
            if current_entity is None or current_entity.entity_type != Entities.Cactus or not current_entity.mature:
                continue

            visited.add((current_x, current_y))
            current_size = int(current_entity.metadata.get("size", 0))
            for neighbor_x, neighbor_y in self._adjacent_coordinates(current_x, current_y):
                neighbor = self.get_tile(neighbor_x, neighbor_y)
                if neighbor.entity is None or neighbor.entity.entity_type != Entities.Cactus or not neighbor.entity.mature:
                    continue
                neighbor_size = int(neighbor.entity.metadata.get("size", 0))
                if neighbor_size >= current_size:
                    pending.append((neighbor_x, neighbor_y))

        return (
            list(visited),
            {
                Items.Cactus: float(len(visited) ** 2)
                * self._yield_scale(Unlocks.Cactus)
            },
        )

    def _sunflower_power_yield(self, petals: int) -> float:
        sunflower_count = pybuiltins.max(1, self._count_entities(Entities.Sunflower))
        power_yield = float(pybuiltins.max(1, int(math.sqrt(sunflower_count))))
        power_yield *= self._yield_scale(Unlocks.Sunflowers)

        all_petals: list[int] = []
        for y in range(self.state.world_size):
            for x in range(self.state.world_size):
                tile = self.get_tile(x, y)
                if tile.entity is None or tile.entity.entity_type != Entities.Sunflower:
                    continue
                all_petals.append(int(tile.entity.metadata.get("petals", SUNFLOWER_MIN_PETALS)))

        if sunflower_count >= 10 and all_petals and petals >= pybuiltins.max(all_petals):
            power_yield *= SUNFLOWER_MAX_BONUS_MULTIPLIER
        return power_yield

    def _spoil_other_sunflowers(self, harvested_x: int, harvested_y: int, harvested_petals: int) -> None:
        max_petals = None
        for y in range(self.state.world_size):
            for x in range(self.state.world_size):
                tile = self.get_tile(x, y)
                if tile.entity is None or tile.entity.entity_type != Entities.Sunflower:
                    continue
                petals = int(tile.entity.metadata.get("petals", SUNFLOWER_MIN_PETALS))
                if max_petals is None or petals > max_petals:
                    max_petals = petals

        if max_petals is None or harvested_petals >= max_petals:
            return

        for y in range(self.state.world_size):
            for x in range(self.state.world_size):
                if (x, y) == (harvested_x, harvested_y):
                    continue
                tile = self.get_tile(x, y)
                if tile.entity is not None and tile.entity.entity_type == Entities.Sunflower:
                    tile.entity = None
                    tile.last_updated_tick = self.state.tick_count
                    tile.last_updated_seconds = self.state.elapsed_seconds

    def _cost_for_thing(self, thing: str, level: int | None = None) -> dict[str, float] | None:
        entity_spec = ENTITY_SPECS.get(thing)
        if entity_spec is not None:
            scale = self._entity_cost_scale(thing, entity_spec)
            return self._normalize_cost(
                {
                    item: float(amount) * scale
                    for item, amount in entity_spec.base_cost.items()
                }
            )

        unlock_levels = UNLOCK_COSTS.get(thing)
        if unlock_levels is None:
            return None

        target_level = level
        if target_level is None:
            current_level = self._current_unlock_level(thing)
            if current_level > 0:
                return None
            target_level = 1

        if target_level <= 0 or target_level > len(unlock_levels):
            return None

        return self._normalize_cost(unlock_levels[target_level - 1])

    def set_tile_entity(self, x: int, y: int, entity: EntityState | None) -> TileState:
        """Replace the entity on a tile after synchronizing it."""
        tile = self.get_tile(x, y)
        tile.entity = entity
        if entity is not None:
            if entity.planted_tick is None:
                entity.planted_tick = self.state.tick_count
            if entity.planted_seconds is None:
                entity.planted_seconds = self.state.elapsed_seconds
            if entity.required_growth is not None and entity.growth >= entity.required_growth:
                entity.growth = entity.required_growth
                entity.mature = True
            self._assign_entity_metadata(self.wrap_coordinate(x), self.wrap_coordinate(y), entity)
        tile.last_updated_tick = self.state.tick_count
        tile.last_updated_seconds = self.state.elapsed_seconds
        return tile

    def set_tile_water(self, x: int, y: int, water: float) -> TileState:
        """Update water level and restart deterministic decay scheduling."""
        if water < 0:
            water = 0.0
        if water > 1:
            water = 1.0

        tile = self.get_tile(x, y)
        tile.water = water
        tile.water_decay_steps = 0
        if water <= 0:
            tile.next_water_decay_seconds = None
        else:
            tile.next_water_decay_seconds = (
                self.state.elapsed_seconds + self._water_decay_interval_seconds(x, y, 0)
            )
        tile.last_updated_tick = self.state.tick_count
        tile.last_updated_seconds = self.state.elapsed_seconds
        return tile

    def sync_tile(self, x: int, y: int) -> TileState:
        """Apply lazy growth and water updates to a tile up to the current time."""
        wrapped_x = self.wrap_coordinate(x)
        wrapped_y = self.wrap_coordinate(y)
        tile = self.state.tiles[wrapped_y][wrapped_x]
        current_seconds = self.state.elapsed_seconds

        if tile.last_updated_seconds >= current_seconds:
            tile.last_updated_tick = self.state.tick_count
            tile.last_updated_seconds = current_seconds
            return tile

        self._ensure_passive_ground_entity(tile, wrapped_x, wrapped_y)
        cursor = tile.last_updated_seconds
        if tile.water > 0 and tile.next_water_decay_seconds is None:
            tile.next_water_decay_seconds = (
                cursor + self._water_decay_interval_seconds(wrapped_x, wrapped_y, tile.water_decay_steps)
            )

        while (
            tile.water > 0
            and tile.next_water_decay_seconds is not None
            and tile.next_water_decay_seconds <= current_seconds
        ):
            self._advance_tile_growth(
                tile,
                wrapped_x,
                wrapped_y,
                tile.next_water_decay_seconds - cursor,
            )
            cursor = tile.next_water_decay_seconds
            tile.water *= WATER_DECAY_FACTOR
            if tile.water < 1e-9:
                tile.water = 0.0
            tile.water_decay_steps += 1
            if tile.water > 0:
                tile.next_water_decay_seconds = (
                    cursor
                    + self._water_decay_interval_seconds(
                        wrapped_x,
                        wrapped_y,
                        tile.water_decay_steps,
                    )
                )
            else:
                tile.next_water_decay_seconds = None

        self._advance_tile_growth(tile, wrapped_x, wrapped_y, current_seconds - cursor)
        tile.last_updated_tick = self.state.tick_count
        tile.last_updated_seconds = current_seconds
        return tile

    def _advance_tile_growth(
        self,
        tile: TileState,
        x: int,
        y: int,
        delta_seconds: float,
    ) -> None:
        if delta_seconds <= 0 or tile.entity is None or tile.entity.mature:
            return

        growth_multiplier = 1.0 + (tile.water * 4.0)
        if tile.entity.entity_type == Entities.Tree:
            growth_multiplier *= self._tree_growth_multiplier(x, y)
        tile.entity.growth += delta_seconds * growth_multiplier
        if tile.entity.required_growth is not None and tile.entity.growth >= tile.entity.required_growth:
            tile.entity.growth = tile.entity.required_growth
            tile.entity.mature = True
            if (
                tile.entity.entity_type == Entities.Pumpkin
                and bool(tile.entity.metadata.get("dies_on_maturity"))
            ):
                tile.entity.entity_type = Entities.Dead_Pumpkin
                tile.entity.mature = False

    def _water_decay_interval_seconds(self, x: int, y: int, step: int) -> float:
        seed = (
            (self.state.rng_seed or 0) * 1315423911
            + (x + 1) * 2654435761
            + (y + 1) * 2246822519
            + step * 3266489917
        ) & 0xFFFFFFFF
        interval_rng = random.Random(seed)
        return WATER_DECAY_MIN_SECONDS + (
            interval_rng.random() * (WATER_DECAY_MAX_SECONDS - WATER_DECAY_MIN_SECONDS)
        )

    def move(self, direction: Any) -> bool:
        delta = self._direction_delta(direction)
        if delta is None:
            return self._strict_failure(f"invalid direction for move(): {direction!r}")
        target_x = self.wrap_coordinate(self.state.drone_x + delta[0])
        target_y = self.wrap_coordinate(self.state.drone_y + delta[1])
        if self.state.current_hat == Hats.Dinosaur_Hat:
            if not self._can_move_dinosaur(target_x, target_y):
                return self._strict_failure("destination tile blocks movement")

            move_ticks = self._dinosaur_move_cost_ticks()
            self._update_dinosaur_tail_after_move(target_x, target_y)
            self.advance_ticks(move_ticks)
            self._record_event(
                category="action",
                name="move",
                payload={"direction": direction, "x": target_x, "y": target_y},
            )
            return True

        if self._is_tile_blocked_for_movement(target_x, target_y):
            return self._strict_failure("destination tile blocks movement")

        self.state.drone_x = target_x
        self.state.drone_y = target_y
        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="move",
            payload={"direction": direction, "x": target_x, "y": target_y},
        )
        return True

    def can_move(self, direction: Any) -> bool:
        delta = self._direction_delta(direction)
        allowed = False
        if delta is not None:
            target_x = self.wrap_coordinate(self.state.drone_x + delta[0])
            target_y = self.wrap_coordinate(self.state.drone_y + delta[1])
            if self.state.current_hat == Hats.Dinosaur_Hat:
                allowed = self._can_move_dinosaur(target_x, target_y)
            else:
                allowed = not self._is_tile_blocked_for_movement(target_x, target_y)
        self._consume_sensor_tick(
            name="can_move",
            payload={"direction": direction, "result": allowed},
        )
        return allowed

    def get_pos_x(self) -> int:
        value = self.state.drone_x
        self._consume_sensor_tick(name="get_pos_x", payload={"value": value})
        return value

    def get_pos_y(self) -> int:
        value = self.state.drone_y
        self._consume_sensor_tick(name="get_pos_y", payload={"value": value})
        return value

    def get_world_size(self) -> int:
        value = self.state.world_size
        self._consume_sensor_tick(name="get_world_size", payload={"value": value})
        return value

    def get_entity_type(self) -> str | None:
        tile = self.current_tile()
        value = None if tile.entity is None else tile.entity.entity_type
        self._consume_sensor_tick(name="get_entity_type", payload={"value": value})
        return value

    def get_ground_type(self) -> str:
        value = self.current_tile().ground_type
        self._consume_sensor_tick(name="get_ground_type", payload={"value": value})
        return value

    def till(self) -> None:
        tile = self.current_tile()
        tile.ground_type = (
            Grounds.Soil if tile.ground_type == Grounds.Grassland else Grounds.Grassland
        )
        tile.last_updated_tick = self.state.tick_count
        tile.last_updated_seconds = self.state.elapsed_seconds
        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="till",
            payload={"ground_type": tile.ground_type},
        )
        return None

    def clear(self) -> None:
        self._reset_field(world_size=self.state.world_size, reset_hat=True)
        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="clear",
            payload={"world_size": self.state.world_size},
        )
        return None

    def can_harvest(self) -> bool:
        tile = self.current_tile()
        entity = tile.entity
        result = False
        if entity is not None:
            if entity.entity_type == Entities.Dead_Pumpkin:
                result = False
            elif entity.entity_type == Entities.Treasure:
                result = True
            else:
                spec = ENTITY_SPECS.get(entity.entity_type)
                if spec is None:
                    result = bool(entity.mature)
                elif spec.harvestable_when_mature:
                    result = spec.required_growth is None or entity.mature
        self._consume_sensor_tick(name="can_harvest", payload={"result": result})
        return result

    def harvest(self) -> bool:
        tile = self.current_tile()
        entity = tile.entity
        if entity is None:
            return self._strict_failure("harvest() called on an empty tile")
        if entity.entity_type == Entities.Dead_Pumpkin:
            return self._strict_failure("dead pumpkins cannot be harvested")

        removed_type = entity.entity_type
        removed_positions = [(self.state.drone_x, self.state.drone_y)]
        harvest_items: dict[str, float] = {}

        if removed_type == Entities.Pumpkin:
            removed_positions, harvest_items = self._harvest_pumpkins(
                self.state.drone_x,
                self.state.drone_y,
            )
        elif removed_type == Entities.Sunflower and entity.mature:
            petals = int(entity.metadata.get("petals", SUNFLOWER_MIN_PETALS))
            harvest_items = {Items.Power: self._sunflower_power_yield(petals)}
            self._spoil_other_sunflowers(
                self.state.drone_x,
                self.state.drone_y,
                petals,
            )
        elif removed_type == Entities.Cactus:
            removed_positions, harvest_items = self._harvest_cactus_chain(
                self.state.drone_x,
                self.state.drone_y,
            )
        elif removed_type == Entities.Treasure and "maze" in tile.flags:
            maze_tiles = [
                (x, y)
                for y, row in enumerate(self.state.tiles)
                for x, maze_tile in enumerate(row)
                if "maze" in maze_tile.flags
            ]
            maze_side = int(math.sqrt(len(maze_tiles))) if maze_tiles else 1
            harvest_items = {
                Items.Gold: float(maze_side * maze_side)
                * self._yield_scale(Unlocks.Mazes)
            }
            removed_positions = maze_tiles or removed_positions
        else:
            harvest_items = self._default_harvest_items(entity)

        explicit_items = entity.metadata.get("harvest_items")
        if isinstance(explicit_items, dict):
            for item, amount in explicit_items.items():
                harvest_items[str(item)] = harvest_items.get(str(item), 0.0) + float(amount)

        self._harvest_group(removed_positions)
        if removed_type == Entities.Treasure:
            for x, y in removed_positions:
                self.get_tile(x, y).flags.discard("maze")
        self.consume_success_ticks()
        self._apply_inventory_gain(harvest_items)
        self._record_event(
            category="action",
            name="harvest",
            payload={
                "entity": removed_type,
                "mature": bool(entity.mature),
                "yielded_items": dict(harvest_items),
                "removed_tiles": removed_positions,
            },
        )
        return True

    def plant(self, entity: str) -> bool:
        spec = ENTITY_SPECS.get(entity)
        if spec is None:
            return self._strict_failure(f"unsupported entity for plant(): {entity!r}")
        if self._thing_level(entity) <= 0:
            return self._strict_failure(f"entity is not unlocked: {entity}")

        tile = self.current_tile()
        if tile.entity is not None and tile.entity.entity_type != Entities.Dead_Pumpkin:
            return self._strict_failure("cannot plant on an occupied tile")
        if tile.ground_type not in spec.allowed_grounds:
            return self._strict_failure(
                f"cannot plant {entity} on ground {tile.ground_type}"
            )

        cost = self._cost_for_thing(entity)
        if cost is None:
            return self._strict_failure(f"entity has no planting cost data: {entity}")
        if not self._can_afford_cost(cost):
            return self._strict_failure(f"cannot afford planting cost for {entity}")

        self._spend_cost(cost)
        self.set_tile_entity(
            self.state.drone_x,
            self.state.drone_y,
            EntityState(
                entity_type=entity,
                required_growth=spec.required_growth,
                planted_tick=self.state.tick_count,
                planted_seconds=self.state.elapsed_seconds,
                mature=False,
            ),
        )
        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="plant",
            payload={"entity": entity, "cost": dict(cost)},
        )
        return True

    def num_items(self, item: str) -> float:
        value = self._inventory_amount(item)
        self._consume_sensor_tick(name="num_items", payload={"item": item, "value": value})
        return value

    def get_water(self) -> float:
        value = self.current_tile().water
        self._consume_sensor_tick(name="get_water", payload={"value": value})
        return value

    def _use_water_once(self) -> bool:
        tile = self.current_tile()
        if tile.water >= 1.0:
            return False

        self._set_inventory_amount(Items.Water, self._inventory_amount(Items.Water) - 1.0)
        self.set_tile_water(self.state.drone_x, self.state.drone_y, 1.0)
        return True

    def _use_fertilizer_once(self) -> bool:
        tile = self.current_tile()
        if tile.entity is None or tile.entity.mature or tile.entity.entity_type == Entities.Dead_Pumpkin:
            return False

        self._set_inventory_amount(
            Items.Fertilizer,
            self._inventory_amount(Items.Fertilizer) - 1.0,
        )
        fertilizer_growth = 2.0 * (1.0 + (tile.water * 4.0))
        if tile.entity.entity_type == Entities.Tree:
            fertilizer_growth *= self._tree_growth_multiplier(
                self.state.drone_x,
                self.state.drone_y,
            )
        tile.entity.growth += fertilizer_growth
        tile.water = 0.0
        tile.next_water_decay_seconds = None
        if tile.entity.required_growth is not None and tile.entity.growth >= tile.entity.required_growth:
            tile.entity.growth = tile.entity.required_growth
            tile.entity.mature = True
            if (
                tile.entity.entity_type == Entities.Pumpkin
                and bool(tile.entity.metadata.get("dies_on_maturity"))
            ):
                tile.entity.entity_type = Entities.Dead_Pumpkin
                tile.entity.mature = False
        tile.last_updated_tick = self.state.tick_count
        tile.last_updated_seconds = self.state.elapsed_seconds
        return True

    def _build_fresh_maze(self, side_length: int) -> bool:
        if side_length <= 0 or side_length > self.state.world_size:
            return False

        start_x = self.state.drone_x
        start_y = self.state.drone_y
        treasure_x = self.wrap_coordinate(start_x + side_length - 1)
        treasure_y = self.wrap_coordinate(start_y + side_length - 1)

        for y_offset in range(side_length):
            for x_offset in range(side_length):
                x = self.wrap_coordinate(start_x + x_offset)
                y = self.wrap_coordinate(start_y + y_offset)
                tile = self.get_tile(x, y)
                tile.flags.add("maze")
                on_vertical_path = x == start_x
                on_horizontal_path = y == treasure_y
                if (x, y) == (treasure_x, treasure_y):
                    tile.entity = EntityState(
                        entity_type=Entities.Treasure,
                        mature=True,
                        metadata={"maze_side_length": side_length},
                    )
                elif on_vertical_path or on_horizontal_path:
                    tile.entity = None
                else:
                    tile.entity = EntityState(entity_type=Entities.Hedge, mature=True)
                tile.last_updated_tick = self.state.tick_count
                tile.last_updated_seconds = self.state.elapsed_seconds

        return True

    def _use_weird_substance(self, n: int) -> bool:
        tile = self.current_tile()
        if tile.entity is None or tile.entity.entity_type != Entities.Bush:
            return False

        maze_level = self._current_unlock_level(Unlocks.Mazes)
        if maze_level <= 0:
            return False
        scale = 2 ** (maze_level - 1)
        if n <= 0 or n % scale != 0:
            return False

        side_length = n // scale
        if side_length > self.state.world_size:
            return False

        self._set_inventory_amount(
            Items.Weird_Substance,
            self._inventory_amount(Items.Weird_Substance) - float(n),
        )
        return self._build_fresh_maze(side_length)

    def use_item(self, item: str, n: int = 1) -> bool:
        if n <= 0:
            return self._strict_failure("use_item() requires n >= 1")
        if self._inventory_amount(item) < n:
            return self._strict_failure(f"not enough inventory for {item}")

        used_any = False
        if item == Items.Water:
            for _index in range(n):
                if not self._use_water_once():
                    break
                used_any = True
        elif item == Items.Fertilizer:
            for _index in range(n):
                if not self._use_fertilizer_once():
                    break
                used_any = True
        elif item == Items.Weird_Substance:
            used_any = self._use_weird_substance(n)
        else:
            return self._strict_failure(f"item is not usable in the harness yet: {item}")

        if not used_any:
            return self._strict_failure(f"use_item({item}) had no effect")

        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="use_item",
            payload={"item": item, "count": n},
        )
        return True

    def get_cost(self, thing: str, level: int | None = None) -> dict[str, float] | None:
        self.consume_failure_ticks()
        result = self._cost_for_thing(thing, level)
        self._record_event(
            category="sensor",
            name="get_cost",
            payload={"thing": thing, "level": level, "value": result},
        )
        return result

    def unlock(self, unlock_name: str) -> bool:
        next_level = self._current_unlock_level(unlock_name) + 1
        cost = self._cost_for_thing(unlock_name, next_level)
        if cost is None:
            return self._strict_failure(f"unlock is already maxed or unsupported: {unlock_name}")
        if not self._can_afford_cost(cost):
            return self._strict_failure(f"cannot afford unlock cost for {unlock_name}")

        self._spend_cost(cost)
        self.state.unlocks[unlock_name] = next_level

        if unlock_name == Unlocks.Speed:
            self.state.speed_level = next_level
        elif unlock_name == Unlocks.Expand:
            self._reset_field(world_size=EXPAND_WORLD_SIZES.get(next_level, self.state.world_size), reset_hat=False)

        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="unlock",
            payload={"unlock": unlock_name, "level": next_level, "cost": dict(cost)},
        )
        return True

    def num_unlocked(self, thing: str) -> int:
        value = self._thing_level(thing)
        self._consume_sensor_tick(name="num_unlocked", payload={"thing": thing, "value": value})
        return value

    def measure(self, direction: Any | None = None) -> float | tuple[int, int] | None:
        target_x = self.state.drone_x
        target_y = self.state.drone_y
        if direction is not None:
            delta = self._direction_delta(direction)
            if delta is None:
                return self._strict_failure(
                    f"invalid direction for measure(): {direction!r}",
                    return_value=None,
                )
            target_x = self.wrap_coordinate(target_x + delta[0])
            target_y = self.wrap_coordinate(target_y + delta[1])

        target_tile = self.get_tile(target_x, target_y)
        value: float | tuple[int, int] | None = None
        if "maze" in target_tile.flags:
            value = self._maze_treasure_position()
        elif target_tile.entity is not None:
            if target_tile.entity.entity_type == Entities.Sunflower:
                value = float(target_tile.entity.metadata.get("petals", SUNFLOWER_MIN_PETALS))
            elif target_tile.entity.entity_type == Entities.Cactus:
                value = float(target_tile.entity.metadata.get("size", 0))
            elif target_tile.entity.entity_type == Entities.Treasure:
                value = self._maze_treasure_position()
            elif target_tile.entity.entity_type == Entities.Apple:
                value = self._dinosaur_state().get("next_apple_position")

        self._consume_sensor_tick(
            name="measure",
            payload={"direction": direction, "value": value},
        )
        return value

    def swap(self, direction: Any) -> bool:
        delta = self._direction_delta(direction)
        if delta is None:
            return self._strict_failure(f"invalid direction for swap(): {direction!r}")

        target_x = self.wrap_coordinate(self.state.drone_x + delta[0])
        target_y = self.wrap_coordinate(self.state.drone_y + delta[1])
        current_tile = self.current_tile()
        target_tile = self.get_tile(target_x, target_y)
        current_type = None if current_tile.entity is None else current_tile.entity.entity_type
        target_type = None if target_tile.entity is None else target_tile.entity.entity_type
        if current_type not in SWAPPABLE_ENTITIES or target_type not in SWAPPABLE_ENTITIES:
            return self._strict_failure("swap() does not support one of the entities")

        current_tile.entity, target_tile.entity = target_tile.entity, current_tile.entity
        current_tile.last_updated_tick = self.state.tick_count
        current_tile.last_updated_seconds = self.state.elapsed_seconds
        target_tile.last_updated_tick = self.state.tick_count
        target_tile.last_updated_seconds = self.state.elapsed_seconds
        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="swap",
            payload={
                "direction": direction,
                "source": current_type,
                "target": target_type,
            },
        )
        return True

    def set_execution_speed(self, speed: float) -> None:
        self.state.execution_speed = 0.0 if speed <= 0 else float(speed)
        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="set_execution_speed",
            payload={"speed": self.state.execution_speed},
        )
        return None

    def set_world_size(self, size: float) -> None:
        target_size = int(size)
        if target_size < 3:
            target_size = self._unlocked_world_size()
        if target_size <= 0:
            target_size = 1

        self._reset_field(world_size=target_size, reset_hat=False)
        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="set_world_size",
            payload={"world_size": target_size},
        )
        return None

    def change_hat(self, hat: str) -> None:
        previous_hat = self.state.current_hat
        bone_yield = 0.0

        if previous_hat == Hats.Dinosaur_Hat and hat != Hats.Dinosaur_Hat:
            bone_yield = self._harvest_dinosaur_tail()

        self.state.current_hat = hat
        if hat == Hats.Dinosaur_Hat and previous_hat != Hats.Dinosaur_Hat:
            self._enter_dinosaur_mode()

        self.consume_success_ticks()
        self._record_event(
            category="action",
            name="change_hat",
            payload={"previous_hat": previous_hat, "hat": hat, "bone_yield": bone_yield},
        )
        return None

    def _normalize_print_values(self, values: tuple[Any, ...]) -> list[str]:
        return [pybuiltins.str(value) for value in values]

    def print_text(self, *values: Any) -> None:
        rendered_values = self._normalize_print_values(values)
        self.consume_fixed_duration_action()
        if self.options.capture_prints:
            self._record_event(
                category="output",
                name="print",
                payload={"values": rendered_values, "text": " ".join(rendered_values)},
            )
        return None

    def quick_print(self, *values: Any) -> None:
        rendered_values = self._normalize_print_values(values)
        if self.options.capture_prints:
            self._record_event(
                category="output",
                name="quick_print",
                payload={"values": rendered_values, "text": " ".join(rendered_values)},
            )
        return None

    def random_builtin(self) -> float:
        self.consume_failure_ticks()
        value = self.random_value()
        self._record_event(category="utility", name="random", payload={"value": value})
        return value

    def len_builtin(self, obj: Any) -> int:
        self.consume_failure_ticks()
        value = pybuiltins.len(obj)
        self._record_event(category="utility", name="len", payload={"value": value})
        return value

    def range_builtin(self, start: int, stop: int | None = None, step: int = 1) -> range:
        self.consume_failure_ticks()
        if stop is None:
            value = pybuiltins.range(start)
        else:
            value = pybuiltins.range(start, stop, step)
        self._record_event(category="utility", name="range", payload={"start": start, "stop": stop, "step": step})
        return value

    def str_builtin(self, obj: Any) -> str:
        self.consume_failure_ticks()
        value = pybuiltins.str(obj)
        self._record_event(category="utility", name="str", payload={"value": value})
        return value

    def min_builtin(self, *args: Any) -> Any:
        values = args[0] if pybuiltins.len(args) == 1 else args
        comparisons = pybuiltins.max(pybuiltins.len(values) - 1, 1)
        self.advance_ticks(comparisons)
        value = pybuiltins.min(*args)
        self._record_event(category="utility", name="min", payload={"value": value, "comparisons": comparisons})
        return value

    def max_builtin(self, *args: Any) -> Any:
        values = args[0] if pybuiltins.len(args) == 1 else args
        comparisons = pybuiltins.max(pybuiltins.len(values) - 1, 1)
        self.advance_ticks(comparisons)
        value = pybuiltins.max(*args)
        self._record_event(category="utility", name="max", payload={"value": value, "comparisons": comparisons})
        return value

    def abs_builtin(self, x: float) -> float:
        self.consume_failure_ticks()
        value = pybuiltins.abs(x)
        self._record_event(category="utility", name="abs", payload={"value": value})
        return value

    def _resolve_workspace_script(self, file_name: Any) -> Path:
        if self._active_workspace_root is None:
            raise UnsupportedFeatureError("nested scenario execution requires an active workspace")

        candidate = Path(pybuiltins.str(file_name))
        if candidate.suffix != ".py":
            candidate = candidate.with_suffix(".py")
        if not candidate.is_absolute():
            candidate = (self._active_workspace_root / candidate).resolve()
        else:
            candidate = candidate.resolve()

        try:
            candidate.relative_to(self._active_workspace_root)
        except ValueError as exc:
            raise UnsupportedFeatureError(
                f"nested scenario path escapes the active workspace: {candidate}"
            ) from exc
        return candidate

    def _normalize_unlock_levels(self, unlocks: Any) -> dict[str, int]:
        if unlocks is None:
            return {}
        if isinstance(unlocks, dict):
            return {pybuiltins.str(key): int(value) for key, value in unlocks.items()}
        values_method = getattr(unlocks, "values", None)
        if callable(values_method):
            return {pybuiltins.str(value): 1 for value in values_method()}
        try:
            return {pybuiltins.str(value): 1 for value in unlocks}
        except TypeError as exc:
            raise UnsupportedFeatureError(
                "simulate() unlocks must be a dict, iterable, or enum-like namespace"
            ) from exc

    def _normalize_item_amounts(self, items: Any) -> dict[str, float]:
        if items is None:
            return {}
        if not isinstance(items, dict):
            raise UnsupportedFeatureError("scenario items must be a dict of item amounts")
        return {pybuiltins.str(key): float(value) for key, value in items.items()}

    def _build_nested_state(
        self,
        *,
        unlocks: dict[str, int] | None = None,
        items: dict[str, float] | None = None,
        seed: int = 0,
        speedup: float = 0.0,
    ) -> GameState:
        return GameState(
            world_size=1,
            inventory={} if items is None else dict(items),
            unlocks={} if unlocks is None else dict(unlocks),
            rng_seed=seed,
            execution_speed=float(speedup),
            strict_mode=self.state.strict_mode,
        )

    def _run_nested_scenario(self, scenario: Scenario) -> RunResult:
        nested_runtime = HarnessRuntime(
            state=copy.deepcopy(scenario.initial_state),
            recorder=TraceRecorder(),
            options=copy.deepcopy(self.options),
        )
        result = nested_runtime._execute_scenario(scenario)
        self._record_event(
            category="runtime",
            name="nested_run",
            payload={
                "scenario": scenario.name,
                "mode": scenario.mode.value,
                "script_path": str(scenario.script_path),
                "status": result.status.value,
                "success": result.success,
                "tick_count": result.tick_count,
                "elapsed_seconds": result.elapsed_seconds,
            },
        )

        if result.status == RunStatus.UNSUPPORTED:
            raise UnsupportedFeatureError(result.errors[0] if result.errors else "nested run unsupported")
        if not result.success:
            message = result.errors[0] if result.errors else "nested run failed"
            raise RuntimeError(message)
        return result

    def simulate_builtin(
        self,
        filename: str,
        sim_unlocks: Any,
        sim_items: dict[Any, Any],
        sim_globals: dict[str, Any],
        seed: float,
        speedup: float,
    ) -> float:
        nested_script = self._resolve_workspace_script(filename)
        nested_state = self._build_nested_state(
            unlocks=self._normalize_unlock_levels(sim_unlocks),
            items=self._normalize_item_amounts(sim_items),
            seed=int(seed),
            speedup=float(speedup),
        )
        if not isinstance(sim_globals, dict):
            raise UnsupportedFeatureError("simulate() globals must be a dict")

        self.consume_success_ticks()
        scenario = Scenario(
            name=f"simulate:{nested_script.stem}",
            script_path=nested_script,
            mode=ScenarioMode.SIMULATE,
            mode_source="injected",
            seed=int(seed),
            speedup=float(speedup),
            globals={pybuiltins.str(key): value for key, value in sim_globals.items()},
            initial_state=nested_state,
        )
        result = self._run_nested_scenario(scenario)
        self._record_event(
            category="action",
            name="simulate",
            payload={
                "filename": pybuiltins.str(filename),
                "seed": int(seed),
                "speedup": float(speedup),
                "elapsed_seconds": result.elapsed_seconds,
            },
        )
        return result.elapsed_seconds

    def leaderboard_run_builtin(self, leaderboard: str, file_name: str, speedup: float) -> None:
        if leaderboard != Leaderboards.Fastest_Reset:
            raise UnsupportedFeatureError(
                f"leaderboard_run() preset not implemented for {leaderboard}"
            )

        nested_script = self._resolve_workspace_script(file_name)
        self.consume_success_ticks()
        scenario = build_preset_scenario(
            "fastest-reset",
            script_path=nested_script,
            name=f"leaderboard:{nested_script.stem}",
            speedup=float(speedup),
            strict_mode=self.state.strict_mode,
            metadata={"leaderboard": leaderboard},
        )
        result = self._run_nested_scenario(scenario)
        self._record_event(
            category="action",
            name="leaderboard_run",
            payload={
                "leaderboard": leaderboard,
                "file_name": pybuiltins.str(file_name),
                "speedup": float(speedup),
                "elapsed_seconds": result.elapsed_seconds,
            },
        )
        return None

    def _assertion_path_parts(self, path: str) -> list[str]:
        if "/" in path:
            return [part for part in path.split("/") if part]
        return [part for part in path.split(".") if part]

    def _resolve_assertion_value(self, root: Any, path: str) -> Any:
        current = root
        for part in self._assertion_path_parts(path):
            if isinstance(current, dict):
                if part not in current:
                    raise KeyError(part)
                current = current[part]
                continue
            if isinstance(current, list):
                current = current[int(part)]
                continue
            if hasattr(current, part):
                current = getattr(current, part)
                continue
            raise KeyError(part)
        return current

    def _assertion_matches(self, actual: Any, assertion: ScenarioAssertion) -> bool:
        operator = assertion.operator
        expected = assertion.expected
        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "gt":
            return actual > expected
        if operator == "gte":
            return actual >= expected
        if operator == "lt":
            return actual < expected
        if operator == "lte":
            return actual <= expected
        if operator == "truthy":
            return bool(actual)
        if operator == "falsy":
            return not bool(actual)
        if operator == "contains":
            return expected in actual
        raise UnsupportedFeatureError(f"unsupported assertion operator: {operator}")

    def _evaluate_assertions(
        self,
        scenario: Scenario,
        *,
        return_value: Any,
    ) -> list[str]:
        failures: list[str] = []
        if not scenario.assertions:
            return failures

        context = {
            "scenario_name": scenario.name,
            "return_value": return_value,
            "tick_count": self.state.tick_count,
            "elapsed_seconds": self.state.elapsed_seconds,
            "final_state": self.state,
        }

        for assertion in scenario.assertions:
            try:
                actual = self._resolve_assertion_value(context, assertion.path)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                failures.append(f"assertion path could not be resolved: {assertion.path} ({exc})")
                continue

            if self._assertion_matches(actual, assertion):
                continue
            failures.append(
                f"assertion failed for {assertion.path}: expected {assertion.operator} {assertion.expected!r}, got {actual!r}"
            )
        return failures

    def run(self, scenario: Scenario) -> RunResult:
        """Execute one scenario in an isolated module and state environment."""
        scenario_state = copy.deepcopy(scenario.initial_state)
        if scenario.seed is not None:
            scenario_state.rng_seed = int(scenario.seed)
            scenario_state.rng_state = random.Random(scenario_state.rng_seed).getstate()
        if scenario.speedup > 0:
            scenario_state.execution_speed = float(scenario.speedup)
        if scenario.strict_mode:
            scenario_state.strict_mode = True

        isolated_runtime = HarnessRuntime(
            state=scenario_state,
            recorder=TraceRecorder(),
            options=copy.deepcopy(self.options),
        )
        result = isolated_runtime._execute_scenario(scenario)
        self.state = isolated_runtime.state
        self.recorder = isolated_runtime.recorder
        return result

    def _execute_scenario(self, scenario: Scenario) -> RunResult:
        script_source = load_script_source(scenario.script_path)
        workspace_modules = discover_workspace_modules(script_source.path)
        self._active_workspace_root = workspace_modules.root_dir
        self._active_script_path = script_source.path
        self._active_scenario = scenario
        session = _ExecutionSession(
            runtime=self,
            scenario=scenario,
            root_source=script_source,
            workspace_modules=workspace_modules,
        )

        self._record_event(
            category="runtime",
            name="run_start",
            payload={
                "scenario": scenario.name,
                "script_path": str(script_source.path),
                "mode": scenario.mode.value,
                "mode_source": scenario.mode_source,
                "entrypoint": scenario.entrypoint,
                "world_size": self.state.world_size,
                "rng_seed": self.state.rng_seed,
            },
        )

        try:
            module = session.execute_root()
            return_value = None
            if scenario.entrypoint is not None:
                entrypoint = getattr(module, scenario.entrypoint, None)
                if entrypoint is None or not callable(entrypoint):
                    raise UnsupportedFeatureError(
                        f"scenario entrypoint is not callable: {scenario.entrypoint}"
                    )
                return_value = entrypoint()
                self._record_event(
                    category="runtime",
                    name="entrypoint_completed",
                    payload={
                        "entrypoint": scenario.entrypoint,
                        "return_value": pybuiltins.repr(return_value),
                    },
                )
        except UnsupportedFeatureError as exc:
            self._record_event(
                category="runtime",
                name="run_unsupported",
                payload={"error_type": type(exc).__name__, "message": str(exc)},
            )
            return self._build_run_result(
                scenario,
                script_source.path,
                status=RunStatus.UNSUPPORTED,
                success=False,
                errors=[f"{type(exc).__name__}: {exc}"],
            )
        except StaticValidationError as exc:
            self._record_event(
                category="runtime",
                name="run_failed",
                payload={"error_type": type(exc).__name__, "message": str(exc)},
            )
            return self._build_run_result(
                scenario,
                script_source.path,
                status=RunStatus.FAILED,
                success=False,
                errors=str(exc).splitlines(),
            )
        except Exception:
            formatted_traceback = traceback.format_exc().rstrip()
            self._record_event(
                category="runtime",
                name="run_failed",
                payload={"traceback": formatted_traceback},
            )
            return self._build_run_result(
                scenario,
                script_source.path,
                status=RunStatus.FAILED,
                success=False,
                errors=[formatted_traceback],
            )

        assertion_failures = self._evaluate_assertions(scenario, return_value=return_value)
        if assertion_failures:
            self._record_event(
                category="runtime",
                name="run_failed",
                payload={"assertion_failures": list(assertion_failures)},
            )
            return self._build_run_result(
                scenario,
                script_source.path,
                status=RunStatus.FAILED,
                success=False,
                errors=assertion_failures,
                return_value=return_value,
            )

        self._record_event(
            category="runtime",
            name="run_completed",
            payload={"module": module.__name__, "return_value": pybuiltins.repr(return_value)},
        )
        return self._build_run_result(
            scenario,
            script_source.path,
            status=RunStatus.COMPLETED,
            success=True,
            return_value=return_value,
        )

    def _build_run_result(
        self,
        scenario: Scenario,
        script_path: Any,
        *,
        status: RunStatus,
        success: bool,
        errors: list[str] | None = None,
        return_value: Any = None,
    ) -> RunResult:
        return RunResult(
            scenario_name=scenario.name,
            status=status,
            success=success,
            tick_count=self.state.tick_count,
            elapsed_seconds=self.state.elapsed_seconds,
            return_value=return_value,
            events=list(self.recorder.events),
            errors=[] if errors is None else list(errors),
            final_state=copy.deepcopy(self.state),
            script_path=script_path,
        )

    def unsupported_result(self, scenario: Scenario, message: str) -> RunResult:
        """Build a normalized unsupported result for callers that want one."""
        return RunResult(
            scenario_name=scenario.name,
            status=RunStatus.UNSUPPORTED,
            success=False,
            tick_count=self.state.tick_count,
            elapsed_seconds=self.state.elapsed_seconds,
            errors=[message],
            final_state=self.state,
            script_path=scenario.script_path,
        )
