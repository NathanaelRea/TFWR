"""Golden parity helpers for normalized TFWR harness traces.

Phase 8 compares selected checkpoints and final-state slices rather than every
incidental runtime event. That keeps goldens stable when debug wording changes
but observable behavior does not.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ParityMismatchError
from .models import GameState, RunResult, TileState
from .traces import normalize_trace_events, normalize_trace_value

PARITY_GOLDEN_VERSION = 1


def load_golden_trace(path: Path) -> dict[str, Any]:
    """Load one JSON golden trace bundle from disk."""
    resolved = Path(path).resolve()
    return json.loads(resolved.read_text(encoding="utf-8"))


def build_run_parity_snapshot(
    result: RunResult,
    *,
    inventory_items: list[str] | None = None,
    unlocks: list[str] | None = None,
    tile_positions: list[tuple[int, int]] | None = None,
    event_names: list[str] | None = None,
    event_categories: list[str] | None = None,
) -> dict[str, Any]:
    """Build a comparison-friendly summary for a run result."""
    final_state = result.final_state
    if final_state is None:
        state_snapshot = None
    else:
        state_snapshot = {
            "world": {
                "world_size": final_state.world_size,
                "drone_x": final_state.drone_x,
                "drone_y": final_state.drone_y,
                "current_hat": final_state.current_hat,
            },
            "inventory": _select_inventory(final_state, inventory_items),
            "unlocks": _select_unlocks(final_state, unlocks),
            "tiles": _select_tiles(final_state, tile_positions),
        }

    return {
        "format_version": PARITY_GOLDEN_VERSION,
        "scenario_name": result.scenario_name,
        "status": result.status.value,
        "success": result.success,
        "tick_count": result.tick_count,
        "elapsed_seconds": normalize_trace_value(result.elapsed_seconds),
        "errors": [str(error) for error in result.errors],
        "checkpoints": _select_events(
            result.events,
            event_names=event_names,
            event_categories=event_categories,
        ),
        "final_state": state_snapshot,
    }


def assert_parity_matches_golden(
    result: RunResult,
    golden_path: Path,
    *,
    inventory_items: list[str] | None = None,
    unlocks: list[str] | None = None,
    tile_positions: list[tuple[int, int]] | None = None,
    event_names: list[str] | None = None,
    event_categories: list[str] | None = None,
) -> dict[str, Any]:
    """Compare a run result to a stored golden bundle and raise on mismatch."""
    golden = load_golden_trace(golden_path)
    expected = golden["expected"]
    actual = build_run_parity_snapshot(
        result,
        inventory_items=inventory_items,
        unlocks=unlocks,
        tile_positions=tile_positions,
        event_names=event_names,
        event_categories=event_categories,
    )
    mismatch = _first_difference(expected, actual, path="expected")
    if mismatch is not None:
        raise ParityMismatchError(
            "\n".join(
                [
                    f"parity mismatch for {golden.get('scenario', {}).get('name', result.scenario_name)}",
                    mismatch,
                ]
            )
        )
    return actual


def _select_inventory(state: GameState, inventory_items: list[str] | None) -> dict[str, Any]:
    if inventory_items is None:
        return normalize_trace_value(state.inventory)
    selected = {
        item: float(state.inventory.get(item, 0.0))
        for item in inventory_items
        if item in state.inventory or state.inventory.get(item, 0.0) != 0.0
    }
    return normalize_trace_value(selected)


def _select_unlocks(state: GameState, unlocks: list[str] | None) -> dict[str, Any]:
    if unlocks is None:
        return normalize_trace_value(state.unlocks)
    selected = {
        unlock: int(state.unlocks.get(unlock, 0))
        for unlock in unlocks
    }
    return normalize_trace_value(selected)


def _select_tiles(
    state: GameState,
    tile_positions: list[tuple[int, int]] | None,
) -> dict[str, Any]:
    if tile_positions is None:
        return {}
    selected: dict[str, Any] = {}
    for x, y in tile_positions:
        tile = state.tiles[y][x]
        selected[f"{x},{y}"] = _tile_snapshot(tile)
    return selected


def _tile_snapshot(tile: TileState) -> dict[str, Any]:
    entity = tile.entity
    if entity is None:
        entity_snapshot = None
    else:
        entity_snapshot = {
            "entity_type": entity.entity_type,
            "growth": normalize_trace_value(entity.growth),
            "required_growth": normalize_trace_value(entity.required_growth),
            "mature": entity.mature,
            "metadata": normalize_trace_value(entity.metadata),
        }

    return {
        "ground_type": tile.ground_type,
        "water": normalize_trace_value(tile.water),
        "entity": entity_snapshot,
        "flags": normalize_trace_value(tile.flags),
    }


def _select_events(
    events: list[Any],
    *,
    event_names: list[str] | None,
    event_categories: list[str] | None,
) -> list[dict[str, Any]]:
    selected = []
    for event in events:
        if event_names is not None and event.name not in event_names:
            continue
        if event_categories is not None and event.category not in event_categories:
            continue
        selected.append(event)
    return normalize_trace_events(selected, comparison_mode=True)


def _first_difference(expected: Any, actual: Any, *, path: str) -> str | None:
    if type(expected) is not type(actual):
        return f"{path}: expected {type(expected).__name__}, got {type(actual).__name__}"

    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        if missing:
            return f"{path}: missing keys {missing}"
        if extra:
            return f"{path}: unexpected keys {extra}"
        for key in sorted(expected):
            mismatch = _first_difference(
                expected[key],
                actual[key],
                path=f"{path}/{key}",
            )
            if mismatch is not None:
                return mismatch
        return None

    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: expected list length {len(expected)}, got {len(actual)}"
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            mismatch = _first_difference(
                expected_item,
                actual_item,
                path=f"{path}/{index}",
            )
            if mismatch is not None:
                return mismatch
        return None

    if expected != actual:
        return f"{path}: expected {expected!r}, got {actual!r}"
    return None
