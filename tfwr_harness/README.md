# TFWR Harness

This package is the local test harness scaffold described in `plan.md`.

It runs TFWR-like scripts under CPython with a synthetic builtin shim. That is
useful for local testing, validation, and repeatable scenario fixtures, but it
is not a full reimplementation of the game's language or engine.

## Current Scope

- Canonical entrypoint: `python -m tfwr_harness`
- Core contracts for runtime state, scenarios, trace events, and run results
- Harness-specific error types
- Scenario manifest loading
- Isolated script execution with a synthetic `__builtins__` module
- Workspace-only import loading for sibling helper modules
- Static validation result shape
- Test layout for unit, integration, scenarios, and golden traces
- Golden parity helpers for comparing selected checkpoints and final-state slices

## Commands

- `python -m tfwr_harness --help`
- `python -m tfwr_harness validate leader_reset.py`
- `python -m tfwr_harness run-scenario tests/scenarios/example_carrot.json`
- `python -m tfwr_harness describe-scenario tests/scenarios/example_reset.json`
- `python -m tfwr_harness list-presets`
- `python -m tfwr_harness normalize-trace output.txt --output tests/golden/capture.json`

## Canonical Acceptance Command

Use one local command for the validator plus regression suite:

- `python -m tfwr_harness validate leader_reset.py && python -m unittest`

For harness work that changes scenario execution semantics, also run at least:

- `python -m tfwr_harness run-scenario tests/scenarios/phase9_simulate.json`
- `python -m tfwr_harness run-scenario tests/scenarios/phase9_reset_smoke.json`

## Phase 7 Scenario Shape

Scenario manifests now support a diff-friendly top-level shape:

- `script_path`, optional `entrypoint`, and `mode`
- optional `preset` such as `fastest-reset` or `fastest-reset-smoke`
- `seed`, `speedup`, and `strict`
- injected module `globals`
- `world`, `items`, `unlocks`, and `board`
- declarative `assertions`

The older nested `initial_state` object is still accepted for compatibility, but
new fixtures should prefer the top-level fields above.

## Notes On Parity

The harness should aim to mirror observable game behavior where practical:

- board state and tile occupancy
- inventory and unlock levels
- action timing and tick costs
- builtin return values and failure modes

Harness-only conveniences are allowed when they improve testing ergonomics:

- JSON scenario manifests
- normalized trace output
- golden parity snapshots that compare selected checkpoints instead of full raw logs
- strict-mode failures for invalid actions
- static validation for TFWR-vs-CPython differences

## Regression Rules

- A harness regression is any unit, integration, or scenario test failure in `python -m unittest`.
- A parity regression is any failure in the golden parity tests or any intentional change to the normalized snapshot shape without a corresponding golden update.
- Golden updates are only safe when the runtime behavior change is intended and the updated snapshot still reflects the same selected checkpoints and final-state slice policy.

## Unsupported In V1

- Real multi-drone scheduling and worker coordination
- Full megafarm execution semantics
- Full in-game language semantics beyond CPython plus validator coverage
- Full reset-route parity for `leader_reset.py` while its maze and dinosaur planning hooks remain placeholders

## Agent Notes Placeholder

- TODO: record implementation notes and cross-module decisions here as phases land.

## Parity Discoveries Placeholder

- TODO: record confirmed game quirks, wiki conflicts, and golden-trace findings here.
