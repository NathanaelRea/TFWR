from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfwr_harness.errors import ParityMismatchError
from tfwr_harness.game_data import Items, Unlocks
from tfwr_harness.models import GameState, RunResult, RunStatus
from tfwr_harness.parity import assert_parity_matches_golden, build_run_parity_snapshot
from tfwr_harness.traces import TraceRecorder, normalize_output_capture_text, normalize_trace_events


class TraceNormalizationTests(unittest.TestCase):
    def test_normalize_trace_events_drops_output_text_for_comparison(self) -> None:
        recorder = TraceRecorder()
        recorder.record(
            tick=7,
            seconds=0.5,
            category="output",
            name="quick_print",
            payload={"values": ["checkpoint", "speed"], "text": "checkpoint speed"},
        )

        normalized = normalize_trace_events(recorder.events, comparison_mode=True)

        self.assertEqual(["checkpoint", "speed"], normalized[0]["payload"]["values"])
        self.assertNotIn("text", normalized[0]["payload"])

    def test_normalize_output_capture_text_supports_plain_lines_and_jsonl(self) -> None:
        capture = "\n".join(
            [
                "200 checkpoint speed 1 180",
                json.dumps(
                    {
                        "tick": 402,
                        "category": "output",
                        "name": "quick_print",
                        "payload": {"values": ["checkpoint", "grass", 1, 80], "text": "ignore me"},
                    }
                ),
            ]
        )

        normalized = normalize_output_capture_text(capture)

        self.assertEqual(2, len(normalized))
        self.assertEqual(200, normalized[0]["tick"])
        self.assertEqual(["checkpoint", "speed", 1, 180], normalized[0]["payload"]["values"])
        self.assertEqual(402, normalized[1]["tick"])
        self.assertNotIn("text", normalized[1]["payload"])


class ParitySnapshotTests(unittest.TestCase):
    def test_build_run_parity_snapshot_filters_inventory_unlocks_and_checkpoints(self) -> None:
        recorder = TraceRecorder()
        recorder.record(
            tick=200,
            seconds=0.5,
            category="output",
            name="quick_print",
            payload={"values": ["checkpoint", "speed", 1, 180], "text": "checkpoint speed 1 180"},
        )
        recorder.record(
            tick=201,
            seconds=0.5025,
            category="sensor",
            name="num_items",
            payload={"item": Items.Hay, "value": 180},
        )
        result = RunResult(
            scenario_name="parity",
            status=RunStatus.COMPLETED,
            success=True,
            tick_count=200,
            elapsed_seconds=0.5,
            events=recorder.events,
            final_state=GameState(
                world_size=1,
                inventory={Items.Hay: 180.0, Items.Wood: 50.0},
                unlocks={Unlocks.Speed: 1, Unlocks.Grass: 1},
            ),
        )

        snapshot = build_run_parity_snapshot(
            result,
            inventory_items=[Items.Hay],
            unlocks=[Unlocks.Speed],
            tile_positions=[(0, 0)],
            event_names=["quick_print"],
        )

        self.assertEqual({Items.Hay: 180}, snapshot["final_state"]["inventory"])
        self.assertEqual({Unlocks.Speed: 1}, snapshot["final_state"]["unlocks"])
        self.assertEqual(1, len(snapshot["checkpoints"]))
        self.assertEqual("quick_print", snapshot["checkpoints"][0]["name"])

    def test_assert_parity_matches_golden_raises_readable_difference(self) -> None:
        result = RunResult(
            scenario_name="parity",
            status=RunStatus.COMPLETED,
            success=True,
            tick_count=200,
            elapsed_seconds=0.5,
            final_state=GameState(world_size=1, inventory={Items.Hay: 180.0}),
        )

        golden = {
            "format_version": 1,
            "scenario": {"name": "parity"},
            "accepted_mismatches": [],
            "expected": {
                "format_version": 1,
                "scenario_name": "parity",
                "status": "completed",
                "success": True,
                "tick_count": 201,
                "elapsed_seconds": 0.5,
                "errors": [],
                "checkpoints": [],
                "final_state": {
                    "world": {
                        "world_size": 1,
                        "drone_x": 0,
                        "drone_y": 0,
                        "current_hat": None,
                    },
                    "inventory": {Items.Hay: 180},
                    "unlocks": {},
                    "tiles": {},
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            golden_path = Path(temp_dir) / "golden.json"
            golden_path.write_text(json.dumps(golden, indent=2, sort_keys=True), encoding="utf-8")

            with self.assertRaises(ParityMismatchError) as context:
                assert_parity_matches_golden(
                    result,
                    golden_path,
                    inventory_items=[Items.Hay],
                    unlocks=[],
                    tile_positions=[],
                    event_names=[],
                )

        self.assertIn("expected/tick_count", str(context.exception))


if __name__ == "__main__":
    unittest.main()
