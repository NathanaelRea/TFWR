# Scenario Fixtures

This folder is reserved for declarative scenario manifests consumed by
`tfwr_harness.scenarios`.

- Put reusable JSON scenario inputs here.
- Keep manifests small and deterministic.
- Prefer scenario names that match the script and mechanic under test.
- Prefer purpose-built parity fixtures over full leaderboard routes when a phase only needs one mechanic slice.
- For captured-output parity work, keep each script's `quick_print(...)` checkpoints explicit and machine-friendly.
- Add new manifests here and keep helper scripts beside them when the scenario needs custom code.
- Validate a manifest with:
- `python -m tfwr_harness describe-scenario tests/scenarios/<name>.json`
- Run it with:
- `python -m tfwr_harness run-scenario tests/scenarios/<name>.json`
- Phase 8 fixtures:
- `phase8_reset_bootstrap.json`
- `phase8_pumpkin_fertilizer.json`
- `phase8_maze.json`
- Phase 9 fixtures:
- `phase9_reset_smoke.json`
- `phase9_simulate.json`
