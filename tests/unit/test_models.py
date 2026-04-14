from __future__ import annotations

import unittest
from pathlib import Path

from tfwr_harness.game_data import Unlocks
from tfwr_harness.models import EntityState, GameState, RunResult, RunStatus, Scenario, ScenarioMode, TileState
from tfwr_harness.scenarios import _load_initial_state, build_preset_scenario, scenario_to_dict
from tfwr_harness.traces import TraceRecorder


class GameStateTests(unittest.TestCase):
    def test_game_state_builds_square_tile_grid(self) -> None:
        state = GameState(world_size=3)

        self.assertEqual(3, len(state.tiles))
        self.assertTrue(all(len(row) == 3 for row in state.tiles))
        self.assertEqual("Grounds.Grassland", state.tiles[0][0].ground_type)

    def test_game_state_rejects_mismatched_tile_grid(self) -> None:
        with self.assertRaises(ValueError):
            GameState(world_size=2, tiles=[[GameState._build_square_tiles(1)[0][0]]])

    def test_game_state_initializes_deterministic_rng_state(self) -> None:
        state = GameState(world_size=2, rng_seed=17)

        self.assertEqual(17, state.rng_seed)
        self.assertIsNotNone(state.rng_state)

    def test_game_state_wraps_drone_position_to_world(self) -> None:
        state = GameState(world_size=3, drone_x=8, drone_y=-1)

        self.assertEqual(2, state.drone_x)
        self.assertEqual(2, state.drone_y)


class ScenarioStateTests(unittest.TestCase):
    def test_initial_state_round_trips_tile_and_entity_fields(self) -> None:
        raw_state = {
            "world_size": 2,
            "drone_x": 1,
            "drone_y": 1,
            "speed_level": 3,
            "execution_speed": 0.0,
            "active_power": 25.0,
            "current_hat": "Hats.Tree_Hat",
            "scenario_limits": {"max_actions": 10},
            "rng_seed": 99,
            "random_calls": 2,
            "tiles": [
                [
                    {
                        "ground_type": "Grounds.Soil",
                        "water": 0.5,
                        "last_updated_seconds": 1.25,
                        "next_water_decay_seconds": 2.0,
                        "water_decay_steps": 1,
                        "entity": {
                            "entity_type": "Entities.Carrot",
                            "growth": 1.5,
                            "required_growth": 6.0,
                            "planted_tick": 50,
                            "planted_seconds": 0.5,
                            "metadata": {"lane": 0},
                        },
                        "flags": ["watched"],
                    },
                    {},
                ],
                [
                    {},
                    {"ground_type": "Grounds.Soil"},
                ],
            ],
        }

        state = _load_initial_state(raw_state)
        scenario = Scenario(
            name="fixture",
            script_path=Path("script.py"),
            mode=ScenarioMode.SIMULATE,
            entrypoint="run",
            seed=99,
            speedup=64.0,
            strict_mode=True,
            globals={"START": 3},
            initial_state=state,
        )
        serialized = scenario_to_dict(scenario)

        self.assertEqual(3, state.speed_level)
        self.assertEqual("Entities.Carrot", state.tiles[0][0].entity.entity_type)
        self.assertEqual(1, state.tiles[0][0].water_decay_steps)
        self.assertEqual({"max_actions": 10}, state.scenario_limits)
        self.assertEqual("simulate", serialized["mode"])
        self.assertEqual("run", serialized["entrypoint"])
        self.assertEqual(99, serialized["seed"])
        self.assertEqual(64.0, serialized["speedup"])
        self.assertTrue(serialized["strict"])
        self.assertEqual({"START": 3}, serialized["globals"])
        self.assertEqual(
            "Entities.Carrot",
            serialized["board"][0][0]["entity"]["entity_type"],
        )

    def test_scenario_to_dict_serializes_loaded_state(self) -> None:
        state = GameState(
            world_size=1,
            speed_level=2,
            scenario_limits={"budget": 3},
            tiles=[
                [
                    TileState(
                        ground_type="Grounds.Soil",
                        entity=EntityState(
                            entity_type="Entities.Tree",
                            growth=4.0,
                            required_growth=7.0,
                        ),
                        water=0.25,
                    )
                ]
            ],
        )

        scenario = Scenario(name="fixture", script_path=Path("script.py"), initial_state=state)
        serialized = scenario_to_dict(scenario)

        self.assertEqual(2, serialized["world"]["speed_level"])
        self.assertEqual({"budget": 3}, serialized["world"]["scenario_limits"])
        self.assertEqual("Entities.Tree", serialized["board"][0][0]["entity"]["entity_type"])

    def test_build_preset_scenario_applies_fastest_reset_baseline(self) -> None:
        scenario = build_preset_scenario(
            "fastest-reset",
            script_path=Path("leader_reset.py"),
        )

        self.assertEqual(ScenarioMode.LEADERBOARD, scenario.mode)
        self.assertEqual("injected", scenario.mode_source)
        self.assertIn(Unlocks.Simulation, scenario.initial_state.unlocks)
        self.assertEqual(
            "final_state/unlocks/Unlocks.Leaderboard",
            scenario.assertions[0].path,
        )


class TraceRecorderTests(unittest.TestCase):
    def test_trace_recorder_keeps_normalized_payload(self) -> None:
        recorder = TraceRecorder()

        event = recorder.record(
            tick=42,
            seconds=0.42,
            category="action",
            name="move",
            payload={"direction": "North"},
        )

        self.assertEqual(1, len(recorder.events))
        self.assertEqual("North", event.to_dict()["payload"]["direction"])


class RunResultTests(unittest.TestCase):
    def test_run_result_uses_normalized_status(self) -> None:
        result = RunResult(scenario_name="smoke", status=RunStatus.UNSUPPORTED)

        self.assertEqual("unsupported", result.status.value)
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
