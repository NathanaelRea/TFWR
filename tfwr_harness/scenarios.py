"""Scenario manifest loading, presets, and serialization helpers.

Scenario manifests are a harness abstraction. They let the same runtime execute
repeatable board setups, assertions, and preset reset flows without depending
on live save data from the game.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .errors import InvalidScenarioError
from .game_data import Items, Unlocks
from .models import EntityState, GameState, Scenario, ScenarioAssertion, ScenarioMode, TileState

RESET_CODE_UNLOCK_BASELINE = {
    Unlocks.Loops: 1,
    Unlocks.Senses: 1,
    Unlocks.Operators: 1,
    Unlocks.Variables: 1,
    Unlocks.Functions: 1,
    Unlocks.Lists: 1,
    Unlocks.Dictionaries: 1,
    Unlocks.Import: 1,
    Unlocks.Timing: 1,
    Unlocks.Utilities: 1,
    Unlocks.Costs: 1,
    Unlocks.Auto_Unlock: 1,
    Unlocks.Simulation: 1,
}

SCENARIO_PRESETS = (
    "fastest-reset",
    "fastest-reset-smoke",
)


def load_scenario_manifest(path: Path) -> Scenario:
    """Load a JSON scenario manifest from disk."""
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise InvalidScenarioError(f"scenario manifest not found: {resolved}")

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InvalidScenarioError(f"invalid scenario JSON: {resolved}") from exc

    return _scenario_from_raw(
        _resolve_manifest_presets(raw),
        base_dir=resolved.parent,
        manifest_path=resolved,
        mode_source="manifest",
    )


def build_preset_scenario(
    preset_name: str,
    *,
    script_path: Path,
    name: str | None = None,
    entrypoint: str | None = None,
    seed: int | None = None,
    speedup: float | None = None,
    strict_mode: bool = False,
    globals: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    notes: list[str] | None = None,
) -> Scenario:
    """Build an injected scenario from one of the Phase 7 named presets."""
    raw: dict[str, Any] = {
        "name": script_path.stem if name is None else name,
        "script_path": str(script_path),
        "preset": preset_name,
    }
    if entrypoint is not None:
        raw["entrypoint"] = entrypoint
    if seed is not None:
        raw["seed"] = seed
    if speedup is not None:
        raw["speedup"] = speedup
    if strict_mode:
        raw["strict"] = True
    if globals:
        raw["globals"] = dict(globals)
    if metadata:
        raw["metadata"] = dict(metadata)
    if notes:
        raw["notes"] = list(notes)

    resolved_script = Path(script_path).resolve()
    return _scenario_from_raw(
        _resolve_manifest_presets(raw),
        base_dir=resolved_script.parent,
        manifest_path=None,
        mode_source="injected",
    )


def list_scenario_presets() -> tuple[str, ...]:
    """Return the stable list of named scenario presets."""
    return SCENARIO_PRESETS


def scenario_to_dict(scenario: Scenario) -> dict[str, Any]:
    """Serialize a scenario to a stable JSON-friendly shape."""
    return {
        "name": scenario.name,
        "description": scenario.description,
        "manifest_path": None if scenario.manifest_path is None else str(scenario.manifest_path),
        "manifest_version": scenario.manifest_version,
        "script_path": str(scenario.script_path),
        "mode": scenario.mode.value,
        "mode_source": scenario.mode_source,
        "entrypoint": scenario.entrypoint,
        "preset": scenario.preset,
        "seed": scenario.seed,
        "speedup": scenario.speedup,
        "strict": scenario.strict_mode,
        "args": list(scenario.args),
        "globals": dict(scenario.globals),
        "world": {
            "size": scenario.initial_state.world_size,
            "drone_x": scenario.initial_state.drone_x,
            "drone_y": scenario.initial_state.drone_y,
            "tick_count": scenario.initial_state.tick_count,
            "elapsed_seconds": scenario.initial_state.elapsed_seconds,
            "speed_level": scenario.initial_state.speed_level,
            "execution_speed": scenario.initial_state.execution_speed,
            "active_power": scenario.initial_state.active_power,
            "current_hat": scenario.initial_state.current_hat,
            "scenario_limits": dict(scenario.initial_state.scenario_limits),
            "rng_seed": scenario.initial_state.rng_seed,
            "random_calls": scenario.initial_state.random_calls,
        },
        "items": dict(scenario.initial_state.inventory),
        "unlocks": dict(scenario.initial_state.unlocks),
        "board": [
            [_tile_to_dict(tile) for tile in row]
            for row in scenario.initial_state.tiles
        ],
        "assertions": [
            {
                "path": assertion.path,
                "expected": assertion.expected,
                "operator": assertion.operator,
            }
            for assertion in scenario.assertions
        ],
        "metadata": dict(scenario.metadata),
        "notes": list(scenario.notes),
    }


def _scenario_from_raw(
    raw: Any,
    *,
    base_dir: Path,
    manifest_path: Path | None,
    mode_source: str,
) -> Scenario:
    if not isinstance(raw, dict):
        raise InvalidScenarioError("scenario manifest root must be an object")

    name = raw.get("name")
    script_path = raw.get("script_path")
    if not isinstance(name, str) or not name:
        raise InvalidScenarioError("scenario manifest requires a non-empty 'name'")
    if not isinstance(script_path, str) or not script_path:
        raise InvalidScenarioError("scenario manifest requires a non-empty 'script_path'")

    return Scenario(
        name=name,
        description=str(raw.get("description", "")),
        script_path=(base_dir / script_path).resolve(),
        manifest_path=manifest_path,
        manifest_version=int(raw.get("manifest_version", 1)),
        mode=_load_mode(raw.get("mode", ScenarioMode.NORMAL.value)),
        mode_source=str(raw.get("mode_source", mode_source)),
        entrypoint=_optional_string(raw.get("entrypoint"), field_name="entrypoint"),
        preset=_optional_string(raw.get("preset"), field_name="preset"),
        seed=_optional_int(raw.get("seed"), field_name="seed"),
        speedup=float(raw.get("speedup", 0.0)),
        strict_mode=bool(raw.get("strict", raw.get("strict_mode", False))),
        args=_string_list(raw.get("args", []), field_name="args"),
        globals=_string_key_dict(raw.get("globals", {}), field_name="globals"),
        initial_state=_load_initial_state(_compose_initial_state_raw(raw)),
        assertions=_load_assertions(raw.get("assertions", [])),
        metadata=_string_key_dict(raw.get("metadata", {}), field_name="metadata"),
        notes=_string_list(raw.get("notes", []), field_name="notes"),
    )


def _resolve_manifest_presets(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise InvalidScenarioError("scenario manifest root must be an object")

    preset = raw.get("preset")
    if preset is None:
        return copy.deepcopy(raw)
    if not isinstance(preset, str) or not preset:
        raise InvalidScenarioError("'preset' must be a non-empty string")

    base_manifest = _preset_manifest(preset)
    return _merge_objects(base_manifest, raw)


def _preset_manifest(preset_name: str) -> dict[str, Any]:
    if preset_name == "fastest-reset":
        return {
            "mode": ScenarioMode.LEADERBOARD.value,
            "seed": 0,
            "speedup": 32.0,
            "strict": False,
            "world": {
                "size": 1,
                "drone_x": 0,
                "drone_y": 0,
            },
            "items": {},
            "unlocks": dict(RESET_CODE_UNLOCK_BASELINE),
            "assertions": [
                {
                    "path": "final_state/unlocks/Unlocks.Leaderboard",
                    "expected": 1,
                    "operator": "gte",
                }
            ],
            "metadata": {
                "preset": "fastest-reset",
                "leaderboard": "Leaderboards.Fastest_Reset",
            },
            "notes": [
                "Starts from a reset-like state rather than the live save inventory.",
                "Language and utility unlocks needed by automation are pre-enabled.",
                "Success requires Unlocks.Leaderboard to be unlocked by the run.",
            ],
        }
    if preset_name == "fastest-reset-smoke":
        return {
            "mode": ScenarioMode.LEADERBOARD.value,
            "seed": 0,
            "speedup": 32.0,
            "strict": False,
            "world": {
                "size": 1,
                "drone_x": 0,
                "drone_y": 0,
            },
            "items": {
                Items.Hay: 200.0,
                Items.Wood: 80.0,
                Items.Carrot: 120.0,
            },
            "unlocks": dict(RESET_CODE_UNLOCK_BASELINE),
            "assertions": [
                {
                    "path": "final_state/unlocks/Unlocks.Watering",
                    "expected": 1,
                    "operator": "gte",
                }
            ],
            "metadata": {
                "preset": "fastest-reset-smoke",
                "leaderboard": "Leaderboards.Fastest_Reset",
                "success_milestone": "Unlocks.Watering",
            },
            "notes": [
                "Smoke preset for the earliest reset bootstrap milestones.",
            ],
        }
    raise InvalidScenarioError(f"unknown scenario preset: {preset_name}")


def _merge_objects(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = {key: copy.deepcopy(value) for key, value in base.items()}
        for key, value in override.items():
            if key in merged:
                merged[key] = _merge_objects(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


def _compose_initial_state_raw(raw: dict[str, Any]) -> dict[str, Any]:
    state_raw = raw.get("initial_state", {})
    if state_raw is None:
        state_raw = {}
    if not isinstance(state_raw, dict):
        raise InvalidScenarioError("'initial_state' must be an object")

    composed = copy.deepcopy(state_raw)

    world = raw.get("world")
    if world is not None:
        if not isinstance(world, dict):
            raise InvalidScenarioError("'world' must be an object")
        world_copy = copy.deepcopy(world)
        if "size" in world_copy and "world_size" not in world_copy:
            world_copy["world_size"] = world_copy.pop("size")
        composed.update(world_copy)

    if "board" in raw:
        composed["tiles"] = copy.deepcopy(raw["board"])
    elif "tiles" in raw:
        composed["tiles"] = copy.deepcopy(raw["tiles"])

    if "items" in raw:
        composed["inventory"] = copy.deepcopy(raw["items"])
    if "unlocks" in raw:
        composed["unlocks"] = copy.deepcopy(raw["unlocks"])
    if "seed" in raw and "rng_seed" not in composed:
        composed["rng_seed"] = raw["seed"]
    if "speedup" in raw and "execution_speed" not in composed:
        composed["execution_speed"] = raw["speedup"]
    if "strict" in raw and "strict_mode" not in composed:
        composed["strict_mode"] = raw["strict"]

    return composed


def _load_mode(raw: Any) -> ScenarioMode:
    if isinstance(raw, ScenarioMode):
        return raw
    if not isinstance(raw, str):
        raise InvalidScenarioError("'mode' must be a string")
    try:
        return ScenarioMode(raw)
    except ValueError as exc:
        raise InvalidScenarioError(f"unsupported scenario mode: {raw}") from exc


def _load_initial_state(raw: Any) -> GameState:
    if raw is None:
        return GameState()
    if not isinstance(raw, dict):
        raise InvalidScenarioError("'initial_state' must be an object")

    return GameState(
        world_size=int(raw.get("world_size", 1)),
        drone_x=int(raw.get("drone_x", 0)),
        drone_y=int(raw.get("drone_y", 0)),
        tiles=_load_tiles(raw.get("tiles"), world_size=int(raw.get("world_size", 1))),
        inventory=_string_float_dict(raw.get("inventory", {}), field_name="initial_state.inventory"),
        unlocks=_load_unlock_levels(raw.get("unlocks", {}), field_name="initial_state.unlocks"),
        tick_count=int(raw.get("tick_count", 0)),
        elapsed_seconds=float(raw.get("elapsed_seconds", 0.0)),
        speed_level=int(raw.get("speed_level", 0)),
        execution_speed=float(raw.get("execution_speed", 0.0)),
        active_power=float(raw.get("active_power", 0.0)),
        current_hat=_optional_string(raw.get("current_hat"), field_name="initial_state.current_hat"),
        scenario_limits=_string_key_dict(
            raw.get("scenario_limits", {}),
            field_name="initial_state.scenario_limits",
        ),
        rng_seed=_optional_int(raw.get("rng_seed"), field_name="initial_state.rng_seed"),
        random_calls=int(raw.get("random_calls", 0)),
        strict_mode=bool(raw.get("strict_mode", False)),
        notes=_string_list(raw.get("notes", []), field_name="initial_state.notes"),
    )


def _load_tiles(raw: Any, *, world_size: int) -> list[list[TileState]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise InvalidScenarioError("'initial_state.tiles' must be a list")
    if len(raw) != world_size:
        raise InvalidScenarioError("'initial_state.tiles' row count must match world_size")

    rows: list[list[TileState]] = []
    for row_index, row in enumerate(raw):
        if not isinstance(row, list):
            raise InvalidScenarioError(f"'initial_state.tiles[{row_index}]' must be a list")
        if len(row) != world_size:
            raise InvalidScenarioError(
                f"'initial_state.tiles[{row_index}]' column count must match world_size"
            )

        rows.append(
            [
                _load_tile(
                    tile,
                    field_name=f"initial_state.tiles[{row_index}][{column_index}]",
                )
                for column_index, tile in enumerate(row)
            ]
        )
    return rows


def _load_tile(raw: Any, *, field_name: str) -> TileState:
    if not isinstance(raw, dict):
        raise InvalidScenarioError(f"'{field_name}' must be an object")

    return TileState(
        ground_type=str(raw.get("ground_type", "Grounds.Grassland")),
        entity=_load_entity(raw.get("entity"), field_name=f"{field_name}.entity"),
        water=float(raw.get("water", 0.0)),
        last_updated_tick=int(raw.get("last_updated_tick", 0)),
        last_updated_seconds=float(raw.get("last_updated_seconds", 0.0)),
        next_water_decay_seconds=_optional_float(
            raw.get("next_water_decay_seconds"),
            field_name=f"{field_name}.next_water_decay_seconds",
        ),
        water_decay_steps=int(raw.get("water_decay_steps", 0)),
        flags=set(_string_list(raw.get("flags", []), field_name=f"{field_name}.flags")),
    )


def _load_entity(raw: Any, *, field_name: str) -> EntityState | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise InvalidScenarioError(f"'{field_name}' must be an object or null")

    return EntityState(
        entity_type=_optional_string(raw.get("entity_type"), field_name=f"{field_name}.entity_type"),
        growth=float(raw.get("growth", 0.0)),
        required_growth=_optional_float(
            raw.get("required_growth"),
            field_name=f"{field_name}.required_growth",
        ),
        planted_tick=_optional_int(raw.get("planted_tick"), field_name=f"{field_name}.planted_tick"),
        planted_seconds=_optional_float(
            raw.get("planted_seconds"),
            field_name=f"{field_name}.planted_seconds",
        ),
        mature=bool(raw.get("mature", False)),
        metadata=_string_key_dict(raw.get("metadata", {}), field_name=f"{field_name}.metadata"),
    )


def _load_assertions(raw: Any) -> list[ScenarioAssertion]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise InvalidScenarioError("'assertions' must be a list")

    assertions: list[ScenarioAssertion] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise InvalidScenarioError(f"'assertions[{index}]' must be an object")

        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise InvalidScenarioError(f"'assertions[{index}].path' must be a non-empty string")

        assertions.append(
            ScenarioAssertion(
                path=path,
                expected=item.get("expected"),
                operator=str(item.get("operator", "equals")),
            )
        )
    return assertions


def _tile_to_dict(tile: TileState) -> dict[str, Any]:
    return {
        "ground_type": tile.ground_type,
        "entity": None if tile.entity is None else _entity_to_dict(tile.entity),
        "water": tile.water,
        "last_updated_tick": tile.last_updated_tick,
        "last_updated_seconds": tile.last_updated_seconds,
        "next_water_decay_seconds": tile.next_water_decay_seconds,
        "water_decay_steps": tile.water_decay_steps,
        "flags": sorted(tile.flags),
    }


def _entity_to_dict(entity: EntityState) -> dict[str, Any]:
    return {
        "entity_type": entity.entity_type,
        "growth": entity.growth,
        "required_growth": entity.required_growth,
        "planted_tick": entity.planted_tick,
        "planted_seconds": entity.planted_seconds,
        "mature": entity.mature,
        "metadata": dict(entity.metadata),
    }


def _string_list(raw: Any, *, field_name: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise InvalidScenarioError(f"'{field_name}' must be a list of strings")
    return list(raw)


def _string_key_dict(raw: Any, *, field_name: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict) or any(not isinstance(key, str) for key in raw):
        raise InvalidScenarioError(f"'{field_name}' must be an object with string keys")
    return dict(raw)


def _string_float_dict(raw: Any, *, field_name: str) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise InvalidScenarioError(f"'{field_name}' must be an object")

    converted: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise InvalidScenarioError(f"'{field_name}' must use string keys")
        converted[key] = float(value)
    return converted


def _load_unlock_levels(raw: Any, *, field_name: str) -> dict[str, int]:
    if raw is None:
        return {}
    if isinstance(raw, list):
        if any(not isinstance(item, str) for item in raw):
            raise InvalidScenarioError(f"'{field_name}' must be a list of strings")
        return {str(item): 1 for item in raw}
    if not isinstance(raw, dict):
        raise InvalidScenarioError(f"'{field_name}' must be an object or list of strings")

    converted: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise InvalidScenarioError(f"'{field_name}' must use string keys")
        converted[key] = int(value)
    return converted


def _optional_string(raw: Any, *, field_name: str) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise InvalidScenarioError(f"'{field_name}' must be a string or null")
    return raw


def _optional_int(raw: Any, *, field_name: str) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidScenarioError(f"'{field_name}' must be an integer or null") from exc


def _optional_float(raw: Any, *, field_name: str) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidScenarioError(f"'{field_name}' must be a number or null") from exc
