"""Command-line entrypoint for the local TFWR harness.

The CLI is a harness-only workflow layer around validation, scenario execution,
and trace normalization. It aims to keep one canonical local interface for the
Phase 10 acceptance path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .errors import HarnessError, InvalidScenarioError
from .loader import load_script_source
from .models import RunResult, RunStatus
from .parity import build_run_parity_snapshot
from .runtime import HarnessRuntime
from .scenarios import load_scenario_manifest, list_scenario_presets, scenario_to_dict
from .traces import normalize_output_capture_text, normalize_trace_events
from .validator import ValidationSeverity, has_blocking_issues, validate_source


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m tfwr_harness",
        description="Local TFWR harness workflow for validation, scenarios, and traces.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="tfwr_harness phase-10 workflow",
    )

    subparsers = parser.add_subparsers(dest="command")

    describe_parser = subparsers.add_parser(
        "describe-scenario",
        help="Load a JSON scenario manifest and print a normalized summary.",
    )
    describe_parser.add_argument("manifest", type=Path)

    run_parser = subparsers.add_parser(
        "run-scenario",
        help="Execute a JSON scenario manifest and print a normalized run result.",
    )
    run_parser.add_argument("manifest", type=Path)
    run_parser.add_argument(
        "--recent-events",
        type=int,
        default=10,
        help="How many trailing events to include in the readable failure summary.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Run static TFWR-vs-CPython validation on a script file.",
    )
    validate_parser.add_argument("script", type=Path)
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat validator warnings as blocking issues.",
    )

    normalize_parser = subparsers.add_parser(
        "normalize-trace",
        help="Normalize captured output text into structured JSON trace events.",
    )
    normalize_parser.add_argument("capture", type=Path)
    normalize_parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the normalized JSON instead of stdout only.",
    )

    subparsers.add_parser(
        "list-presets",
        help="List the built-in named scenario presets.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the harness CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "describe-scenario":
            return _describe_scenario(args.manifest)
        if args.command == "run-scenario":
            return _run_scenario(args.manifest, recent_events=args.recent_events)
        if args.command == "validate":
            return _validate_script(args.script, strict=args.strict)
        if args.command == "normalize-trace":
            return _normalize_trace(args.capture, output_path=args.output)
        if args.command == "list-presets":
            return _list_presets()

        parser.print_help()
        return 0
    except HarnessError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _describe_scenario(manifest_path: Path) -> int:
    scenario = load_scenario_manifest(manifest_path)
    print(json.dumps(scenario_to_dict(scenario), indent=2, sort_keys=True))
    return 0


def _run_scenario(manifest_path: Path, *, recent_events: int) -> int:
    scenario = load_scenario_manifest(manifest_path)
    result = HarnessRuntime().run(scenario)
    summary = _run_result_to_dict(result, recent_events=recent_events)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if result.status == RunStatus.COMPLETED and result.success:
        return 0
    if result.status == RunStatus.UNSUPPORTED:
        return 2
    return 1


def _validate_script(script_path: Path, *, strict: bool = False) -> int:
    source = load_script_source(script_path)
    issues = validate_source(source.text, path=source.path)
    print(
        json.dumps(
            [issue.to_dict() for issue in issues],
            indent=2,
            sort_keys=True,
        )
    )
    if has_blocking_issues(issues, strict_warnings=strict):
        return 1
    has_error = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
    return 1 if has_error else 0


def _normalize_trace(capture_path: Path, *, output_path: Path | None) -> int:
    capture_text = Path(capture_path).read_text(encoding="utf-8")
    try:
        normalized = normalize_output_capture_text(capture_text)
    except ValueError as exc:
        raise InvalidScenarioError(f"invalid capture text for normalization: {capture_path}") from exc
    rendered = json.dumps(normalized, indent=2, sort_keys=True)
    print(rendered)
    if output_path is not None:
        Path(output_path).write_text(rendered + "\n", encoding="utf-8")
    return 0


def _list_presets() -> int:
    data = [
        {"name": preset}
        for preset in list_scenario_presets()
    ]
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def _run_result_to_dict(result: RunResult, *, recent_events: int) -> dict[str, Any]:
    summary = {
        "scenario_name": result.scenario_name,
        "status": result.status.value,
        "success": result.success,
        "tick_count": result.tick_count,
        "elapsed_seconds": result.elapsed_seconds,
        "script_path": None if result.script_path is None else str(result.script_path),
        "return_value": result.return_value,
        "errors": list(result.errors),
        "events": normalize_trace_events(result.events),
        "final_state": None,
    }
    if result.final_state is not None:
        summary["final_state"] = build_run_parity_snapshot(result)["final_state"]

    if result.status != RunStatus.COMPLETED or not result.success:
        summary["failure_context"] = _failure_context(result, recent_events=recent_events)
    return summary


def _failure_context(result: RunResult, *, recent_events: int) -> dict[str, Any]:
    recent = result.events[-recent_events:] if recent_events > 0 else []
    return {
        "recent_events": normalize_trace_events(recent),
        "final_state": build_run_parity_snapshot(result)["final_state"],
    }
