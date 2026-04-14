# Golden Traces

This folder is reserved for normalized golden traces and expected run outputs.

- Store stable serialized traces here once the runtime emits them.
- Keep filenames aligned with scenario names.
- Record parity notes when a golden trace intentionally encodes a game quirk.
- Each golden JSON bundle should include:
- scenario metadata
- capture workflow metadata
- accepted mismatch notes
- an `expected` snapshot built from selected checkpoints and final-state slices
- The current Phase 8 bundles are harness reference snapshots.
- They use the same normalized shape that real in-game captures should use, but `capture.real_game_capture` is intentionally `null` until someone imports a concrete `output.txt`.
- Recommended in-game capture workflow:
- add machine-oriented `quick_print(get_tick_count(), "checkpoint", ...)` lines to the scenario script
- copy the game's `output.txt`
- normalize it through:
- `python -m tfwr_harness normalize-trace output.txt --output tests/golden/<scenario>_capture.json`
- store the resulting JSON alongside the harness golden for review
- When updating a golden, confirm the behavior change is intentional and re-run `python -m unittest`.
- Current Phase 8 goldens:
- `phase8_reset_bootstrap.json`
- `phase8_pumpkin_fertilizer.json`
- `phase8_maze.json`
