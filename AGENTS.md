# The Farmer Was Replaced

## Purpose

- This save uses The Farmer Was Replaced's Python-like scripting language.
- Treat `__builtins__.py` as the local reference for available names, signatures, and behavior.
- Treat `save.json` as the source of truth for what is currently unlocked in this specific save.

## Files

- `main.py`: active farm script.
- `__builtins__.py`: editor/type stub for the game's builtin API. It is only an approximation of the real language, but it is the best local reference.
- `save.json`: current inventory, unlocks, and editor state.

## Language Rules

- The language is Python-like, not Python.
- Do not assume Python standard library support.
- Do not add imports except when the game supports them.
- Prefer simple control flow and basic data structures already visible in `main.py` and `save.json`.
- Expect game-specific names such as `Entities`, `Items`, `Grounds`, `Hats`, `Unlocks`, `North`, `South`, `East`, and `West`.
- `None`, `True`, `False`, `while`, `for`, `break`, `continue`, `def`, `return`, `global`, lists, dicts, and sets are unlocked in this save.

## Builtin API Summary

- World interaction: `harvest()`, `can_harvest()`, `plant(entity)`, `move(direction)`, `can_move(direction)`, `swap(direction)`, `till()`, `clear()`.
- Senses: `get_pos_x()`, `get_pos_y()`, `get_world_size()`, `get_entity_type()`, `get_ground_type()`, `get_water()`, `get_companion()`, `measure()`.
- Inventory and economy: `use_item(item, n=1)`, `num_items(item)`, `get_cost(thing, level=None)`, `unlock(unlock)`, `num_unlocked(thing)`.
- Timing and debugging: `get_time()`, `get_tick_count()`, `print(...)`, `quick_print(...)`, `set_execution_speed(speed)`, `set_world_size(size)`.
- Utility functions exposed by the game: `len(...)`, `range(...)`, `str(...)`, `min(...)`, `max(...)`, `abs(...)`, `random()`.
- Cosmetic and advanced systems in the builtin stub: `change_hat(hat)`, plus drone/simulation/leaderboard helpers such as `spawn_drone`, `wait_for`, `has_finished`, `simulate`, and `leaderboard_run`.

## Current Save State

- This save has strong progression in grass, carrots, trees, pumpkins, watering, fertilizer, sunflowers, polyculture, dictionaries, cactus, mazes, timing, utilities, and movement/senses.
- The current save unlock list in `save.json` includes practical features used by `main.py`, including `plant`, `move`, `till`, `get_entity_type`, `get_ground_type`, `get_pos_x`, `get_pos_y`, `num_items`, `use_item`, `measure`, `get_companion`, `random`, `min`, `max`, `abs`, `swap`, and `can_move`.
- Do not assume every symbol present in `__builtins__.py` is usable in this save. In particular, multi-drone, leaderboard, simulation, dinosaur, and other late-game APIs should be treated as locked unless verified in `save.json` or by `num_unlocked(...)`.

## Working Rules For Agents

- Read `main.py` before making strategy changes so you preserve the current farm loop and state model.
- When adding logic, prefer the game's builtins over inventing abstractions.
- Keep code robust against missing entities and partially grown crops:
  - check `get_entity_type()` before acting on a tile;
  - use `can_harvest()` before assuming a crop is mature;
  - use `get_ground_type()` before planting soil-only crops.
- Remember action cost matters. Many world actions take `200` ticks on success, while sensor checks are usually `1` tick and some timing/debug functions are `0` ticks.
- Use `quick_print(...)` for cheap debug output and `print(...)` only when visible smoke output is actually useful.
- Be careful with `till()`: it toggles between `Grounds.Grassland` and `Grounds.Soil`.
- Remember movement wraps around the world edges.
- For cactus sorting or other movement-heavy work, measure and compute the target arrangement in memory first, then execute the swap plan; avoid repeated `goto(...)`, re-measuring, or bubble-sorting on the field when a local plan will do.
- Favor explicit loops and small helper functions over clever compact code.
- Preserve user variables and overall strategy unless the task requires a rewrite.

## Safe Assumptions

- `Entities.Grass`, `Bush`, `Tree`, `Carrot`, `Pumpkin`, `Sunflower`, `Cactus`, `Dead_Pumpkin`, `Hedge`, and `Treasure` are relevant to this save.
- `Items.Hay`, `Wood`, `Carrot`, `Pumpkin`, `Cactus`, `Water`, `Fertilizer`, `Weird_Substance`, `Power`, and `Gold` are relevant to this save.
- `Hats.Sunflower_Hat`, `Carrot_Hat`, `Pumpkin_Hat`, `Cactus_Hat`, `Tree_Hat`, and common color hats are present.

## Validation Checklist

- If you use a builtin, confirm it exists in `__builtins__.py` or is already used by `main.py`.
- If you use a progression-dependent feature, confirm it is unlocked in `save.json` or guard it with `num_unlocked(...)`.
- If you change farm traversal, verify wraparound behavior and origin reset logic still make sense.
- If you change crop handling, verify ground type, harvest readiness, and item usage still line up with the crop's rules.
