# Mechanics And API

This is the low-level reference for tick cost, speed scaling, and builtin behavior.

## Tick And Time Model

Recent wiki execution notes:

- Base tick time is about `2.5ms`.
- That is `400` ticks per second at speed level 0 with no power.
- A successful 200-tick action like `move()` or `harvest()` therefore takes about `0.5s` at base speed.
- Each `Speed` upgrade multiplies execution speed by `1.5`.
- `Power` doubles the current speed again while available.

### Useful Speed Factors

| Speed level | No power factor | With power factor | Ticks/sec no power | Ticks/sec with power |
| --- | ---: | ---: | ---: | ---: |
| 0 | 1.0 | 2.0 | 400 | 800 |
| 1 | 1.5 | 3.0 | 600 | 1200 |
| 2 | 2.25 | 4.5 | 900 | 1800 |
| 3 | 3.375 | 6.75 | 1350 | 2700 |
| 4 | 5.0625 | 10.125 | 2025 | 4050 |
| 5 | 7.59375 | 15.1875 | 3037.5 | 6075 |

## Action Cost Cheat Sheet

Use current local stub values when exact zero-cost behavior matters.

| Operation | Typical cost |
| --- | --- |
| successful `move`, `harvest`, `plant`, `use_item`, `swap`, `unlock`, `clear` | `200` ticks |
| failed fallible action | `1` tick |
| getters/sensors like `get_pos_x`, `get_ground_type`, `can_harvest`, `measure`, `num_items`, `get_cost` | `1` tick |
| `quick_print` | `0` ticks in local stub |
| `get_tick_count` | `0` ticks |
| `get_time` | `0` ticks in local stub, but some wiki pages still list `1` |
| `print`, `do_a_flip` | fixed `1` second, not affected by speed |
| `set_execution_speed`, `set_world_size`, `change_hat`, successful `spawn_drone` | `200` ticks |

## Operation-Cost Rules That Matter For Optimization

From the recent `Operation_Costs` page:

- simple literals and variable lookups are free,
- empty list/set/dict/tuple literals cost at least `1`,
- list and dict construction cost scales with element count,
- direct calls to user-defined functions add no overhead beyond the body,
- indirect user-defined function calls through a variable add `1` tick,
- builtin functions bound to variables do not pay extra indirection cost,
- string-key dict lookups cost `max(len(key) // 8, 1)`,
- tuple/list comparisons recurse and can become surprisingly expensive,
- entering a `for` loop costs `1`,
- an `if` condition costs `1` plus the cost of evaluating the condition.

Practical style guidance:

- Prefer numeric enum keys or dense lists over long string-key dict hot paths.
- Reuse measured values instead of recomputing sensor calls in inner loops.
- Keep comparison-heavy structures simple.

## Important Builtin Behaviors

### Movement And Ground

- Farm edges wrap.
- `till()` toggles between `Grounds.Grassland` and `Grounds.Soil`.
- `clear()` resets position to `(0, 0)` and the local stub says it also resets the hat.
- `set_world_size(size)` is only a debug limiter, not progression research.

### Sensors

- `get_entity_type()` returns `None` if empty.
- `get_ground_type()` returns the current ground enum.
- `measure()` overloads:
  - sunflower: petal count,
  - cactus: size,
  - treasure/apple: next position tuple,
  - dinosaur: local stub says dinosaur type number,
  - pumpkin: older wiki says a mysterious value; the local stub omits that claim.

### Inventory And Research

- `get_cost(thing)` works for entities and unlocks in the current stub.
- `unlock(Unlocks.X)` mirrors clicking research.
- `num_unlocked()` is the standard way to test unlock state and current upgrade level.

### Companion API

- Current local stub: `get_companion()` returns `(entity, (x, y))` or `None`.
- Some older wiki pages still show `[entity, x, y]`.
- Code in this workspace should follow the stub shape.

### Multi-Drone API

- `spawn_drone(function)` starts another worker at the caller's current position.
- `wait_for(handle)` blocks until it finishes and returns its result.
- `has_finished(handle)` polls completion.
- `num_drones()` and `max_drones()` are cheap sensors.

## Current Enum Surface In This Workspace

Confirmed locally:

- `Items`: `Hay`, `Wood`, `Carrot`, `Pumpkin`, `Cactus`, `Water`, `Fertilizer`, `Weird_Substance`, `Power`, `Gold`, `Bone`, plus some cosmetic/legacy items.
- `Entities`: `Grass`, `Bush`, `Tree`, `Carrot`, `Pumpkin`, `Dead_Pumpkin`, `Sunflower`, `Cactus`, `Hedge`, `Treasure`, `Apple`, `Dinosaur`.
- `Grounds`: `Grassland`, `Soil`.
- `Unlocks`: includes progression, utility, simulation, leaderboard, and megafarm unlocks.

## Known Version / Documentation Conflicts

- `quick_print()` is `0` ticks in the local stub and recent operation-cost page, but older available-functions snippets still list `1`.
- `get_time()` is `0` ticks in the local stub, while some wiki pages still group it with 1-tick getters.
- `measure()` behavior around pumpkins differs between sources.
- Old wiki pages still mention removed functions like `timed_reset()` and old item names like `Water_Tank`.

When route performance hinges on a disputed detail, trust the local stub first, then verify with a small in-game probe.

## Sources

- https://thefarmerwasreplaced.wiki.gg/wiki/Execution_Details
- https://thefarmerwasreplaced.wiki.gg/wiki/Operation_Costs
- https://thefarmerwasreplaced.wiki.gg/wiki/Available_Functions
- local `__builtins__.py`

