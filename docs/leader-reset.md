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

## General Guide For The Intended Reset Route

The current scaffold is too linear. The real route should search more deliberately along the Pareto frontier instead of tunneling on the first available crop.

The working priority should be:

1. Bootstrap just enough hay and wood to reach `Plant`, `Carrots`, `Trees`, and `Watering`.
2. Pivot the economy toward pumpkins as soon as pumpkin planting is sustainable.
3. Keep enough carrots to continue planting pumpkins instead of spending the carrot stock blindly on upgrades.
4. Keep enough fertilizer to recover `Dead_Pumpkin` losses and force large contiguous pumpkin groups into mega-pumpkin harvests.
5. Convert pumpkin output into `Weird_Substance`, then run fresh mazes for gold.
6. Use maze gold to reach `Megafarm`.
7. After `Megafarm`, pivot to cactus and dinosaur algorithms for the leaderboard endgame of `2,000,000 Bone` and `1,000,000 Gold`.

This means the script should optimize for the next bottleneck, not for one crop in isolation. In practice:

- bushes and trees are bootstrap resources, not the main plan;
- carrots are mainly a pumpkin input once pumpkins are online;
- pumpkins are the first compounding economy engine;
- mazes are the shortest path to gold and therefore to `Megafarm`;
- cactus and dinosaurs matter most after the megafarm transition.

## Continuous Priorities During The Route

Several systems should stay active across multiple phases instead of being treated as isolated chapters.

### Watering

- Water active production tiles because waiting quickly dominates action cost once the farm expands.
- Do not blindly top every tile to `1.0`; use enough water to improve throughput where growth time matters.
- Remember fertilizer consumes the current water value on that tile, so fertilizer-heavy pumpkin loops need deliberate re-watering rules.

### Sunflowers And Power

- Keep dedicated sunflower production online once `Sunflowers` is unlocked.
- Maintain a power buffer so movement, harvesting, unlocking, and drone work run under the doubled speed multiplier as often as possible.
- Follow the safe sunflower rule from the docs: measure petals and harvest highest-petal flowers first.

### Upgrades

- Keep buying `Speed` aggressively because it multiplies all later work.
- Buy `Expand` when the extra area pays back faster than delaying the current bottleneck; remember each expand clears the farm.
- Keep plant-yield upgrades moving when they do not starve the carrot, pumpkin, fertilizer, or maze budgets needed for the next transition.

## Mechanic-Specific Route Implications

These are the key mechanic takeaways from the docs that should shape `leader_reset.py`.

- Pumpkins: contiguous mature groups have cubic payoff, so dead pumpkins must be repaired quickly and harvest timing should protect large groups.
- Fertilizer: each use advances `2` base seconds and consumes tile water, so it is best used on high-value pumpkin tiles with a re-watering policy.
- Mazes: for reset routing, fresh mazes are simpler and efficient enough; maze reuse is extra complexity with little route value.
- Sunflowers: exact multiplier details are version-conflicted, but highest-petal-first harvesting is safe across sources.
- Dinosaurs: this is a deterministic planning problem, so the script should switch from reactive farming to precomputed sweep logic once that phase matters.
- Megafarm: drone workers need explicit field partitioning so they do not collide or duplicate measurement work.

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

- Replace the phase-2 bush/carrot tunnel with explicit carrot, fertilizer, pumpkin, and power budgets.
- Build a real pumpkin engine that preserves contiguous groups, repairs dead pumpkins, and converts output into `Weird_Substance`.
- Add a maze phase that intentionally farms gold for the `Megafarm` transition instead of treating mazes as a fallback.
- Keep sunflowers and watering active as continuous throughput systems instead of separate side phases.
- After `Megafarm`, partition the farm for drones and move the endgame onto cactus and dinosaur algorithms.

## Sources

- local `leader_reset.py`
- original reset notes moved from the old root `README.md`
- `docs/progression-and-unlocks.md`
- `docs/entities-and-growth.md`
- `docs/mechanics-and-api.md`
