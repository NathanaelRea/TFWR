from __future__ import annotations

import unittest
from pathlib import Path

from tfwr_harness.game_data import Entities, Items, Unlocks
from tfwr_harness.runtime import HarnessRuntime
from tfwr_harness.scenarios import load_scenario_manifest


ROOT = Path(__file__).resolve().parents[2]


class ScenarioManifestIntegrationTests(unittest.TestCase):
    def run_manifest(self, manifest_name: str):
        scenario = load_scenario_manifest(ROOT / "tests" / "scenarios" / manifest_name)
        return HarnessRuntime().run(scenario)

    def test_example_carrot_manifest_runs_end_to_end(self) -> None:
        result = self.run_manifest("example_carrot.json")

        self.assertTrue(result.success)
        self.assertEqual(5, result.return_value)
        self.assertEqual(Entities.Carrot, result.final_state.tiles[0][0].entity.entity_type)

    def test_phase9_reset_smoke_manifest_reaches_first_unlock_milestone(self) -> None:
        result = self.run_manifest("phase9_reset_smoke.json")

        self.assertTrue(result.success, msg="\n".join(result.errors))
        self.assertGreaterEqual(result.final_state.unlocks.get(Unlocks.Watering, 0), 1)

    def test_phase9_simulate_manifest_runs_nested_runtime(self) -> None:
        result = self.run_manifest("phase9_simulate.json")

        self.assertTrue(result.success, msg="\n".join(result.errors))
        self.assertTrue(any(event.name == "simulate" for event in result.events))
        self.assertEqual(0.0, result.final_state.inventory.get(Items.Hay, 0.0))


if __name__ == "__main__":
    unittest.main()
