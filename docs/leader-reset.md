# Leader Reset

This file absorbs the old root `README.md` and expands it with code-specific notes from `leader_reset.py`.

## Confirmed Unlock Hierarchy

```text
speed
grass

expand: speed
plant: speed

carrots: plant

trees: carrots
watering: carrots

pumpkins: trees
sunflowers: watering
fertilizer: watering

polyculture: pumpkins
cactus: pumpkins
mazes: fertilizer

dinosaurs: cactus
megafarm: mazes
```

## Current Reset Route

The scaffold is organized into these logical layers:

```text
phase 0: speed -> grass -> first expand -> plant
phase 1: carrots -> trees -> watering
phase 2: pumpkins -> sunflowers -> fertilizer
phase 3: polyculture -> cactus -> mazes
phase 4: dinosaurs -> megafarm
phase 5: leaderboard
```

## What The Current Script Actually Does

### Phase 0

- buys `Speed`, then `Grass`, then the first `Expand`, then `Plant`,
- stays harvest-only until `Plant` is unlocked,
- uses `can_harvest()` before harvesting once speed is online,
- strips vertically on worlds larger than `1x1`.

### Phase 1

- farms the simplest available crop for a short strip loop,
- tries to buy `Carrots`, `Trees`, and `Watering`.

### Phase 2

- expands to size `6`,
- buys `Pumpkins`, `Sunflowers`, and `Fertilizer`,
- farms carrots if available, otherwise bushes.

### Phase 3

- expands to size `12`,
- buys `Polyculture`, `Cactus`, and `Mazes`,
- uses a placeholder companion strategy,
- otherwise falls back to generic grid farming.

### Phase 4

- expands to size `20`,
- buys `Dinosaurs` and `Megafarm`,
- still uses placeholder logic for:
  - maze solving,
  - dinosaur sweep planning,
  - megafarm worker strategy.

### Phase 5

- rushes `Unlocks.Leaderboard`,
- falls back to maze, dinosaur, cactus, or generic farming depending on what is available.

## Existing Helper Behavior

Useful existing pieces already in the scaffold:

- `goto(x, y)` uses wraparound-aware shortest movement.
- `set_ground_for(entity)` toggles soil/grassland as needed.
- `visit_tile(crop)` safely handles `Dead_Pumpkin`, `can_harvest()`, and replanting.
- `farm_grid(crop)` already gives a serpentine sweep.
- `buy_expands_until(target_size)` prevents flat-priority expand spam.

## Biggest Missing Pieces

These are the highest-value gaps for a serious leaderboard attempt:

1. `farm_with_companions()` is still a placeholder.
2. `solve_maze()` is still a placeholder.
3. `solve_snake()` is still a placeholder.
4. `drone_dispatch()` only launches fallback workers instead of a real stripe or region plan.

## Optimization Heuristics To Keep

- Preserve the bootstrap rule: do not buy repeated upgrades before `Plant` if they starve the route.
- Precompute heavy plans in memory, then execute them once.
- Prefer sensor calls over failed actions when the action costs `200` on success.
- Respect that `Expand` clears the farm.
- Use `quick_print()` for cheap progress logs when profiling.

## Likely Next Improvements

- Turn phase 2 into an actual power-bootstrapping sunflower/carrot hybrid instead of generic carrot sweeps.
- Make phase 3 cactus preparation deterministic by measuring once and swapping once.
- Replace phase 4 dinosaur logic with an even-size snake fill plan and maze logic with a simple wall-follower plus fast reset-to-origin routing.
- When megafarm is online, partition the field so drones do not collide or duplicate measurement work.

## Sources

- local `leader_reset.py`
- original reset notes moved from the old root `README.md`
- `docs/progression-and-unlocks.md`
- `docs/entities-and-growth.md`
- `docs/mechanics-and-api.md`
