# main.py automation plan

This tracker is for the active multi-phase farm script in `main.py` and its helper modules.

## Goal

- [ ] Keep the farm on a bottleneck-driven route instead of a simple unlocked-crop route.
- [ ] Hold enough shared buffers to avoid phase thrash between pumpkins, mazes, sunflowers, cactus, and dinosaurs.
- [ ] Reach and sustain the real late-game gate of `Items.Bone` and `Items.Gold` with megafarm-safe worker behavior.

## Current Baseline

- [x] World routing exists in `main.py` with separate normal, sunflower, pumpkin, maze, cactus, and dinosaur phases.
- [x] Upgrade buying already checks unlock costs against current inventory.
- [x] Pumpkin, maze, cactus, and dinosaur modules have working first-pass implementations.
- [ ] The current implementations still need strategy refinements to match the docs and local guardrails.

## Route State And Scheduling

- [x] Aggregate missing items for upgrades and long-run stock goals.
- [x] Choose between phase worlds from current shortages instead of farming only the latest unlocked crop.
- [ ] Track explicit route-state buffers for carrot reserve, fertilizer reserve, weird substance reserve, power floor, and endgame staging.
- [ ] Remove random top-tier world selection in favor of deterministic priority rules when multiple bottlenecks are active.

## Sunflowers And Power

- [x] Measure sunflower petals during sweeps and harvest only the current maximum-petal tier first.
- [ ] Keep sunflower status in state so the main loop can distinguish scan, wait, and harvest passes.
- [ ] Tune power floor and refill thresholds so sunflower time does not starve higher-value phases.
- [x] Avoid spending shared water on mature sunflower tiles.

## Pumpkins And Substance

- [x] Keep the field contiguous and repair `Entities.Dead_Pumpkin` tiles.
- [x] Gate pumpkin entry on carrot and fertilizer reserves.
- [x] Track a weird-substance budget before starting a maze block.
- [ ] Tighten fertilizer usage so it only targets tiles that improve mega-pumpkin throughput.
- [ ] Decide explicitly when to cash out pumpkins for stock versus keep merging for a larger harvest.

## Mazes

- [x] Create mazes from bushes only when enough weird substance is available.
- [x] Solve mazes with deterministic DFS plus drone branch fan-out.
- [ ] Return to a consistent staging position after each maze run.
- [ ] Add stricter gating so maze runs stop exactly when the gold bottleneck is satisfied.

## Cactus And Dinosaurs

- [x] Grow cactus fields and wait until the field is ready before harvesting.
- [x] Run a deterministic dinosaur policy based on a safe cycle.
- [ ] Replace on-field cactus bubble sorting with a measure-once, plan-in-memory swap execution.
- [ ] Tune cactus and dinosaur transitions around shared cactus inventory instead of a single budget threshold.

## Megafarm Coordination

- [x] Use drones for row-partitioned sweeps where the current code supports it.
- [ ] Partition workers by stable regions or roles instead of cloning the same logic everywhere.
- [ ] Prevent duplicate sensing and overspending of shared water or fertilizer across workers.
- [ ] Keep the main drone on the active bottleneck instead of generic fallback work.

## Validation

- [ ] Confirm every new builtin against `__builtins__.py` or existing workspace usage.
- [ ] Keep traversal wraparound-safe and origin-reset-safe after each phase change.
- [ ] Verify sunflower, pumpkin, and maze behavior against the local docs before tuning thresholds further.
- [ ] Re-check shared-resource behavior after any drone coordination change.
