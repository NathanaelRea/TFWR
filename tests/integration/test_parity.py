from __future__ import annotations

import unittest
from pathlib import Path

from tfwr_harness.game_data import Items, Unlocks
from tfwr_harness.parity import assert_parity_matches_golden
from tfwr_harness.runtime import HarnessRuntime
from tfwr_harness.scenarios import load_scenario_manifest


ROOT = Path(__file__).resolve().parents[2]


class HarnessParityTests(unittest.TestCase):
    def run_manifest(self, manifest_name: str):
        scenario = load_scenario_manifest(ROOT / "tests" / "scenarios" / manifest_name)
        return HarnessRuntime().run(scenario)

    def test_reset_bootstrap_matches_golden(self) -> None:
        result = self.run_manifest("phase8_reset_bootstrap.json")

        actual = assert_parity_matches_golden(
            result,
            ROOT / "tests" / "golden" / "phase8_reset_bootstrap.json",
            inventory_items=[Items.Hay, Items.Wood],
            unlocks=[
                Unlocks.Speed,
                Unlocks.Grass,
                Unlocks.Expand,
                Unlocks.Plant,
                Unlocks.Carrots,
            ],
            tile_positions=[(0, 0)],
            event_names=["quick_print"],
        )

        self.assertEqual("phase8-reset-bootstrap", actual["scenario_name"])

    def test_pumpkin_fertilizer_matches_golden(self) -> None:
        result = self.run_manifest("phase8_pumpkin_fertilizer.json")

        actual = assert_parity_matches_golden(
            result,
            ROOT / "tests" / "golden" / "phase8_pumpkin_fertilizer.json",
            inventory_items=[Items.Carrot, Items.Fertilizer, Items.Pumpkin],
            unlocks=[
                Unlocks.Plant,
                Unlocks.Pumpkins,
                Unlocks.Fertilizer,
            ],
            tile_positions=[(0, 0)],
            event_names=["quick_print"],
        )

        self.assertEqual("phase8-pumpkin-fertilizer", actual["scenario_name"])

    def test_maze_matches_golden(self) -> None:
        result = self.run_manifest("phase8_maze.json")

        actual = assert_parity_matches_golden(
            result,
            ROOT / "tests" / "golden" / "phase8_maze.json",
            inventory_items=[Items.Weird_Substance, Items.Gold],
            unlocks=[Unlocks.Plant, Unlocks.Mazes],
            tile_positions=[(0, 0), (1, 1)],
            event_names=["quick_print"],
        )

        self.assertEqual("phase8-maze", actual["scenario_name"])


if __name__ == "__main__":
    unittest.main()
