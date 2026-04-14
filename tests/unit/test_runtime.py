from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tfwr_harness.errors import StrictModeInvalidActionError
from tfwr_harness.game_data import (
    DEFAULT_HAT,
    East,
    Entities,
    Grounds,
    Hats,
    Items,
    North,
    South,
    Unlocks,
    West,
)
from tfwr_harness.models import EntityState, GameState, RunStatus, Scenario, ScenarioAssertion, ScenarioMode
from tfwr_harness.runtime import HarnessRuntime, RuntimeOptions
from tfwr_harness.scenarios import build_preset_scenario


class HarnessRuntimeClockTests(unittest.TestCase):
    def test_advance_ticks_uses_speed_level_and_power(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(
                world_size=1,
                speed_level=2,
                active_power=1.0,
            )
        )

        runtime.advance_ticks(200)

        self.assertEqual(200, runtime.get_tick_count())
        self.assertAlmostEqual(200 / 1800.0, runtime.get_time())

    def test_execution_speed_limit_caps_elapsed_time_conversion(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(
                world_size=1,
                speed_level=5,
                execution_speed=2.0,
            )
        )

        runtime.advance_ticks(200)

        self.assertAlmostEqual(0.25, runtime.get_time())

    def test_random_value_is_deterministic_across_runtimes(self) -> None:
        left = HarnessRuntime(state=GameState(world_size=1, rng_seed=123))
        right = HarnessRuntime(state=GameState(world_size=1, rng_seed=123))

        left_values = [left.random_value() for _ in range(3)]
        right_values = [right.random_value() for _ in range(3)]

        self.assertEqual(left_values, right_values)
        self.assertEqual(3, left.state.random_calls)


class HarnessRuntimeTileTests(unittest.TestCase):
    def test_sync_tile_advances_growth_without_eager_world_updates(self) -> None:
        state = GameState(
            world_size=2,
            tiles=GameState._build_square_tiles(2),
        )
        runtime = HarnessRuntime(state=state)
        runtime.set_tile_entity(
            0,
            0,
            EntityState(
                entity_type="Entities.Carrot",
                required_growth=6.0,
            ),
        )
        runtime.set_tile_water(0, 0, 0.5)

        runtime.advance_ticks(200)
        runtime.sync_tile(0, 0)

        self.assertAlmostEqual(1.5, runtime.get_tile(0, 0, sync=False).entity.growth)
        self.assertEqual(0.0, runtime.get_tile(1, 1, sync=False).last_updated_seconds)

    def test_sync_tile_water_decay_is_deterministic(self) -> None:
        def build_runtime() -> HarnessRuntime:
            runtime = HarnessRuntime(state=GameState(world_size=1, rng_seed=77))
            runtime.set_tile_entity(
                0,
                0,
                EntityState(
                    entity_type="Entities.Tree",
                    required_growth=20.0,
                ),
            )
            runtime.set_tile_water(0, 0, 1.0)
            return runtime

        left = build_runtime()
        right = build_runtime()

        left.advance_ticks(4000)
        right.advance_ticks(4000)
        left.sync_tile(0, 0)
        right.sync_tile(0, 0)

        self.assertAlmostEqual(left.get_tile(0, 0, sync=False).water, right.get_tile(0, 0, sync=False).water)
        self.assertAlmostEqual(
            left.get_tile(0, 0, sync=False).entity.growth,
            right.get_tile(0, 0, sync=False).entity.growth,
        )

    def test_grassland_spawns_grass_lazily(self) -> None:
        runtime = HarnessRuntime(state=GameState(world_size=1))

        runtime.advance_ticks(200)
        tile = runtime.get_tile(0, 0)

        self.assertIsNotNone(tile.entity)
        self.assertEqual(Entities.Grass, tile.entity.entity_type)
        self.assertTrue(tile.entity.mature)

    def test_tree_growth_slows_with_adjacent_trees(self) -> None:
        solo = HarnessRuntime(state=GameState(world_size=2))
        crowded = HarnessRuntime(state=GameState(world_size=2))
        solo.set_tile_entity(0, 0, EntityState(entity_type=Entities.Tree, required_growth=20.0))
        crowded.set_tile_entity(0, 0, EntityState(entity_type=Entities.Tree, required_growth=20.0))
        crowded.set_tile_entity(1, 0, EntityState(entity_type=Entities.Tree, required_growth=20.0))

        solo.advance_ticks(400)
        crowded.advance_ticks(400)
        solo.sync_tile(0, 0)
        crowded.sync_tile(0, 0)

        self.assertGreater(
            solo.get_tile(0, 0, sync=False).entity.growth,
            crowded.get_tile(0, 0, sync=False).entity.growth,
        )

    def test_phase_two_clock_builtins_are_registered(self) -> None:
        runtime = HarnessRuntime()
        namespace = runtime.build_namespace()

        self.assertIn("get_time", namespace)
        self.assertIn("get_tick_count", namespace)
        self.assertIn("move", namespace)
        self.assertIn("plant", namespace)
        self.assertIn("Entities", namespace)
        self.assertIn("North", namespace)


class HarnessRuntimeBuiltinTests(unittest.TestCase):
    def test_move_wraps_around_world_edges(self) -> None:
        runtime = HarnessRuntime(state=GameState(world_size=3))

        moved = runtime.move(West)

        self.assertTrue(moved)
        self.assertEqual(2, runtime.state.drone_x)
        self.assertEqual(0, runtime.state.drone_y)
        self.assertEqual(200, runtime.get_tick_count())

    def test_can_move_respects_blocking_hedges(self) -> None:
        state = GameState(world_size=2)
        runtime = HarnessRuntime(state=state)
        runtime.set_tile_entity(
            0,
            1,
            EntityState(entity_type=Entities.Hedge),
        )

        self.assertFalse(runtime.can_move(North))
        self.assertEqual(1, runtime.get_tick_count())

    def test_till_and_clear_reset_field_and_hat(self) -> None:
        state = GameState(world_size=2, current_hat="Hats.Tree_Hat")
        runtime = HarnessRuntime(state=state)
        runtime.move(East)
        runtime.till()
        runtime.set_tile_entity(1, 0, EntityState(entity_type=Entities.Bush))

        runtime.clear()

        self.assertEqual((0, 0), (runtime.state.drone_x, runtime.state.drone_y))
        self.assertEqual(DEFAULT_HAT, runtime.state.current_hat)
        self.assertEqual(Grounds.Grassland, runtime.get_tile(1, 0, sync=False).ground_type)
        self.assertIsNone(runtime.get_tile(1, 0, sync=False).entity)

    def test_till_toggles_ground_back_to_grassland(self) -> None:
        runtime = HarnessRuntime(state=GameState(world_size=1))

        runtime.till()
        runtime.till()

        self.assertEqual(Grounds.Grassland, runtime.get_ground_type())

    def test_plant_consumes_cost_and_harvest_removes_immature_entity(self) -> None:
        state = GameState(
            world_size=1,
            inventory={Items.Hay: 3.0, Items.Wood: 3.0},
            unlocks={Unlocks.Plant: 1, Unlocks.Carrots: 1},
        )
        runtime = HarnessRuntime(state=state)
        runtime.till()

        planted = runtime.plant(Entities.Carrot)

        self.assertTrue(planted)
        self.assertEqual(2.0, runtime.state.inventory[Items.Hay])
        self.assertEqual(2.0, runtime.state.inventory[Items.Wood])
        self.assertEqual(Entities.Carrot, runtime.current_tile().entity.entity_type)
        self.assertFalse(runtime.can_harvest())

        harvested = runtime.harvest()

        self.assertTrue(harvested)
        self.assertIsNone(runtime.current_tile().entity)

    def test_plant_returns_false_when_ground_is_invalid(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(
                world_size=1,
                inventory={Items.Hay: 1.0, Items.Wood: 1.0},
                unlocks={Unlocks.Plant: 1, Unlocks.Carrots: 1},
            )
        )

        self.assertFalse(runtime.plant(Entities.Carrot))
        self.assertEqual(1, runtime.get_tick_count())
        self.assertEqual(1.0, runtime.state.inventory[Items.Hay])
        self.assertIsNone(runtime.current_tile(sync=False).entity)

    def test_harvest_returns_false_on_empty_tile(self) -> None:
        runtime = HarnessRuntime(state=GameState(world_size=1))

        self.assertFalse(runtime.harvest())
        self.assertEqual(1, runtime.get_tick_count())

    def test_harvest_applies_explicit_metadata_yield(self) -> None:
        runtime = HarnessRuntime(state=GameState(world_size=1))
        runtime.set_tile_entity(
            0,
            0,
            EntityState(
                entity_type=Entities.Treasure,
                metadata={"harvest_items": {Items.Gold: 9.0}},
            ),
        )

        self.assertTrue(runtime.can_harvest())
        self.assertTrue(runtime.harvest())
        self.assertEqual(9.0, runtime.state.inventory[Items.Gold])

    def test_watering_and_fertilizer_update_growth_and_reset_water(self) -> None:
        state = GameState(
            world_size=1,
            inventory={Items.Water: 1.0, Items.Fertilizer: 1.0},
            unlocks={Unlocks.Watering: 1, Unlocks.Fertilizer: 1},
        )
        runtime = HarnessRuntime(state=state)
        runtime.till()
        runtime.set_tile_entity(0, 0, EntityState(entity_type=Entities.Carrot, required_growth=6.0))

        self.assertTrue(runtime.use_item(Items.Water))
        self.assertEqual(1.0, runtime.get_water())

        self.assertTrue(runtime.use_item(Items.Fertilizer))
        self.assertEqual(0.0, runtime.get_water())
        self.assertTrue(runtime.current_tile().entity.mature)

    def test_pumpkin_group_harvest_uses_cubic_yield(self) -> None:
        state = GameState(world_size=2, unlocks={Unlocks.Pumpkins: 1})
        runtime = HarnessRuntime(state=state)
        for y in range(2):
            for x in range(2):
                runtime.get_tile(x, y).ground_type = Grounds.Soil
                runtime.set_tile_entity(
                    x,
                    y,
                    EntityState(
                        entity_type=Entities.Pumpkin,
                        required_growth=2.0,
                        growth=2.0,
                        mature=True,
                    ),
                )

        self.assertTrue(runtime.harvest())
        self.assertEqual(64.0, runtime.state.inventory[Items.Pumpkin])
        for y in range(2):
            for x in range(2):
                self.assertIsNone(runtime.get_tile(x, y).entity)

    def test_dead_pumpkin_can_be_replanted(self) -> None:
        state = GameState(
            world_size=1,
            inventory={Items.Carrot: 1.0},
            unlocks={Unlocks.Pumpkins: 1},
        )
        runtime = HarnessRuntime(state=state)
        runtime.till()
        runtime.set_tile_entity(0, 0, EntityState(entity_type=Entities.Dead_Pumpkin))

        self.assertFalse(runtime.can_harvest())
        self.assertTrue(runtime.plant(Entities.Pumpkin))
        self.assertEqual(Entities.Pumpkin, runtime.current_tile().entity.entity_type)

    def test_sunflower_measure_and_power_bonus_follow_max_petal_rule(self) -> None:
        state = GameState(world_size=4, unlocks={Unlocks.Sunflowers: 1})
        runtime = HarnessRuntime(state=state)
        for y in range(4):
            for x in range(4):
                runtime.get_tile(x, y).ground_type = Grounds.Soil
                runtime.set_tile_entity(
                    x,
                    y,
                    EntityState(
                        entity_type=Entities.Sunflower,
                        required_growth=7.0,
                        growth=7.0,
                        mature=True,
                        metadata={"petals": 9},
                    ),
                )
        runtime.set_tile_entity(
            0,
            0,
            EntityState(
                entity_type=Entities.Sunflower,
                required_growth=7.0,
                growth=7.0,
                mature=True,
                metadata={"petals": 15},
            ),
        )

        self.assertEqual(15.0, runtime.measure())
        self.assertTrue(runtime.harvest())
        self.assertEqual(20.0, runtime.state.inventory[Items.Power])

    def test_power_inventory_drains_while_speed_boost_is_active(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(
                world_size=1,
                inventory={Items.Power: 1.0},
            )
        )

        runtime.advance_ticks(16000)

        self.assertAlmostEqual(25.0, runtime.get_time())
        self.assertEqual(0.0, runtime.state.inventory.get(Items.Power, 0.0))

    def test_cactus_measure_swap_and_sorted_harvest(self) -> None:
        state = GameState(world_size=2, unlocks={Unlocks.Cactus: 1})
        runtime = HarnessRuntime(state=state)
        for y in range(2):
            for x in range(2):
                runtime.get_tile(x, y).ground_type = Grounds.Soil
        runtime.set_tile_entity(
            0,
            0,
            EntityState(entity_type=Entities.Cactus, required_growth=1.0, growth=1.0, mature=True, metadata={"size": 3}),
        )
        runtime.set_tile_entity(
            1,
            0,
            EntityState(entity_type=Entities.Cactus, required_growth=1.0, growth=1.0, mature=True, metadata={"size": 1}),
        )
        runtime.set_tile_entity(
            0,
            1,
            EntityState(entity_type=Entities.Cactus, required_growth=1.0, growth=1.0, mature=True, metadata={"size": 2}),
        )
        runtime.set_tile_entity(
            1,
            1,
            EntityState(entity_type=Entities.Cactus, required_growth=1.0, growth=1.0, mature=True, metadata={"size": 4}),
        )

        self.assertEqual(3.0, runtime.measure())
        self.assertEqual(1.0, runtime.measure(East))
        self.assertTrue(runtime.swap(East))
        self.assertEqual(1.0, runtime.measure())
        self.assertTrue(runtime.harvest())
        self.assertEqual(16.0, runtime.state.inventory[Items.Cactus])

    def test_weird_substance_creates_fresh_maze_and_treasure_gold(self) -> None:
        state = GameState(
            world_size=2,
            inventory={Items.Weird_Substance: 2.0},
            unlocks={Unlocks.Plant: 1, Unlocks.Mazes: 1},
        )
        runtime = HarnessRuntime(state=state)
        runtime.set_tile_entity(0, 0, EntityState(entity_type=Entities.Bush))

        self.assertTrue(runtime.use_item(Items.Weird_Substance, 2))
        self.assertEqual((1, 1), runtime.measure())
        self.assertFalse(runtime.can_move(East))
        self.assertTrue(runtime.move(North))
        self.assertTrue(runtime.move(East))
        self.assertTrue(runtime.can_harvest())
        self.assertTrue(runtime.harvest())
        self.assertEqual(4.0, runtime.state.inventory[Items.Gold])

    def test_get_cost_uses_unlock_scaling_and_unlock_none_semantics(self) -> None:
        state = GameState(
            world_size=1,
            unlocks={Unlocks.Carrots: 3, Unlocks.Sunflowers: 1},
        )
        runtime = HarnessRuntime(state=state)

        carrot_cost = runtime.get_cost(Entities.Carrot)
        sunflower_unlock_cost = runtime.get_cost(Unlocks.Sunflowers)
        speed_level_two_cost = runtime.get_cost(Unlocks.Speed, 2)

        self.assertEqual({Items.Hay: 4.0, Items.Wood: 4.0}, carrot_cost)
        self.assertIsNone(sunflower_unlock_cost)
        self.assertEqual({Items.Wood: 20.0}, speed_level_two_cost)

    def test_unlock_returns_false_when_inventory_is_insufficient(self) -> None:
        runtime = HarnessRuntime(state=GameState(world_size=1))

        self.assertFalse(runtime.unlock(Unlocks.Plant))
        self.assertEqual(1, runtime.get_tick_count())
        self.assertEqual(0, runtime.num_unlocked(Unlocks.Plant))

    def test_unlock_expand_clears_field_and_updates_world_size(self) -> None:
        state = GameState(
            world_size=1,
            inventory={Items.Hay: 30.0},
        )
        runtime = HarnessRuntime(state=state)
        runtime.set_tile_entity(0, 0, EntityState(entity_type=Entities.Bush))

        unlocked = runtime.unlock(Unlocks.Expand)

        self.assertTrue(unlocked)
        self.assertEqual(1, runtime.state.unlocks[Unlocks.Expand])
        self.assertEqual(2, runtime.state.world_size)
        self.assertEqual((0, 0), (runtime.state.drone_x, runtime.state.drone_y))
        self.assertIsNone(runtime.get_tile(0, 0, sync=False).entity)
        self.assertEqual(0.0, runtime.state.inventory.get(Items.Hay, 0.0))

    def test_print_and_quick_print_record_normalized_output(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(world_size=1),
            options=RuntimeOptions(capture_prints=True),
        )

        runtime.quick_print("phase", 3)
        runtime.print_text("phase", 3)

        self.assertEqual(2, len(runtime.recorder.events))
        self.assertEqual("quick_print", runtime.recorder.events[0].name)
        self.assertEqual("phase 3", runtime.recorder.events[0].payload["text"])
        self.assertEqual("print", runtime.recorder.events[1].name)
        self.assertEqual(1.0, runtime.get_time())

    def test_strict_mode_raises_on_soft_fail_action(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(world_size=1, strict_mode=True),
        )

        with self.assertRaises(StrictModeInvalidActionError):
            runtime.move("Diagonal")

    def test_set_world_size_uses_debug_behavior_and_reset_threshold(self) -> None:
        state = GameState(
            world_size=6,
            unlocks={Unlocks.Expand: 5},
        )
        runtime = HarnessRuntime(state=state)

        runtime.set_world_size(4)
        self.assertEqual(4, runtime.state.world_size)

        runtime.set_world_size(2)
        self.assertEqual(6, runtime.state.world_size)

    def test_num_unlocked_derives_entity_availability_from_unlocks(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(
                world_size=1,
                unlocks={Unlocks.Plant: 1, Unlocks.Trees: 1},
            )
        )

        self.assertEqual(1, runtime.num_unlocked(Entities.Bush))
        self.assertEqual(1, runtime.num_unlocked(Entities.Tree))
        self.assertEqual(0, runtime.num_unlocked(Entities.Cactus))

    def test_change_hat_to_dinosaur_spawns_apple_and_measure_returns_next_position(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(
                world_size=2,
                inventory={Items.Cactus: 8.0},
                unlocks={Unlocks.Dinosaurs: 1},
            )
        )

        runtime.change_hat(Hats.Dinosaur_Hat)

        self.assertEqual(Hats.Dinosaur_Hat, runtime.state.current_hat)
        self.assertEqual(Entities.Apple, runtime.get_tile(1, 0, sync=False).entity.entity_type)
        self.assertEqual((0, 1), runtime.measure(East))
        self.assertEqual(6.0, runtime.state.inventory[Items.Cactus])

    def test_dinosaur_tail_grows_when_moving_away_from_apple_and_hat_swap_harvests_bones(self) -> None:
        runtime = HarnessRuntime(
            state=GameState(
                world_size=2,
                inventory={Items.Cactus: 8.0},
                unlocks={Unlocks.Dinosaurs: 1},
            )
        )

        runtime.change_hat(Hats.Dinosaur_Hat)
        runtime.move(East)
        runtime.move(North)

        self.assertEqual(Entities.Dinosaur, runtime.get_tile(1, 0, sync=False).entity.entity_type)
        self.assertEqual(4.0, runtime.state.inventory[Items.Cactus])

        runtime.change_hat(DEFAULT_HAT)

        self.assertEqual(DEFAULT_HAT, runtime.state.current_hat)
        self.assertEqual(1.0, runtime.state.inventory[Items.Bone])
        self.assertIsNone(runtime.get_tile(1, 0, sync=False).entity)
        current_entity = runtime.get_tile(1, 1, sync=False).entity
        self.assertTrue(
            current_entity is None
            or current_entity.entity_type not in {Entities.Apple, Entities.Dinosaur}
        )

    def test_dinosaur_can_move_allows_vacated_tail_but_blocks_when_growing(self) -> None:
        runtime = HarnessRuntime(state=GameState(world_size=3))
        runtime.state.current_hat = Hats.Dinosaur_Hat
        runtime.state.scenario_limits["_dinosaur"] = {
            "tail": [(0, 1)],
            "apple_position": None,
            "next_apple_position": None,
            "apples_eaten": 0,
        }
        runtime.set_tile_entity(0, 1, EntityState(entity_type=Entities.Dinosaur, mature=True))

        self.assertTrue(runtime.can_move(North))

        runtime.set_tile_entity(0, 0, EntityState(entity_type=Entities.Apple))
        runtime.state.scenario_limits["_dinosaur"]["apple_position"] = (0, 0)

        self.assertFalse(runtime.can_move(North))


class RuntimeExecutionTests(unittest.TestCase):
    def write_script(self, directory: Path, name: str, text: str) -> Path:
        path = directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_run_executes_workspace_script_graph_with_synthetic_builtins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_script(
                root,
                "helper.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        "",
                        "def plant_carrot():",
                        "\ttill()",
                        "\tplant(Entities.Carrot)",
                    ]
                ),
            )
            script_path = self.write_script(
                root,
                "script.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        "import helper",
                        "",
                        "helper.plant_carrot()",
                    ]
                ),
            )

            runtime = HarnessRuntime(options=RuntimeOptions(capture_prints=True))
            scenario = Scenario(
                name="plant-carrot",
                script_path=script_path,
                initial_state=GameState(
                    world_size=1,
                    inventory={Items.Hay: 1.0, Items.Wood: 1.0},
                    unlocks={Unlocks.Plant: 1, Unlocks.Carrots: 1},
                ),
            )

            result = runtime.run(scenario)

            self.assertEqual(RunStatus.COMPLETED, result.status)
            self.assertTrue(result.success)
            self.assertEqual(Entities.Carrot, result.final_state.tiles[0][0].entity.entity_type)
            imported_modules = [
                event.payload["module"]
                for event in result.events
                if event.name == "module_import"
            ]
            self.assertEqual(["script", "helper"], imported_modules)

    def test_run_supports_entrypoint_globals_and_assertions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script_path = self.write_script(
                root,
                "script.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        "VALUE = START + 2",
                        "",
                        "def run():",
                        "\ttill()",
                        "\tplant(Entities.Carrot)",
                        "\treturn VALUE",
                    ]
                ),
            )

            runtime = HarnessRuntime()
            scenario = Scenario(
                name="entrypoint",
                script_path=script_path,
                mode=ScenarioMode.NORMAL,
                entrypoint="run",
                globals={"START": 3},
                initial_state=GameState(
                    world_size=1,
                    inventory={Items.Hay: 1.0, Items.Wood: 1.0},
                    unlocks={Unlocks.Plant: 1, Unlocks.Carrots: 1},
                ),
                assertions=[
                    ScenarioAssertion(path="return_value", expected=5),
                    ScenarioAssertion(
                        path="final_state/tiles/0/0/entity/entity_type",
                        expected=Entities.Carrot,
                    ),
                ],
            )

            result = runtime.run(scenario)

            self.assertEqual(RunStatus.COMPLETED, result.status)
            self.assertEqual(5, result.return_value)

    def test_run_marks_assertion_failures_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script_path = self.write_script(
                root,
                "script.py",
                "VALUE = 1\n",
            )

            runtime = HarnessRuntime()
            scenario = Scenario(
                name="assertion-fail",
                script_path=script_path,
                assertions=[
                    ScenarioAssertion(path="return_value", expected=2),
                ],
            )

            result = runtime.run(scenario)

            self.assertEqual(RunStatus.FAILED, result.status)
            self.assertFalse(result.success)
            self.assertIn("assertion failed", result.errors[0])

    def test_simulate_builtin_runs_in_isolated_nested_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_script(
                root,
                "worker.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        "VALUE = START_VALUE + 1",
                        "till()",
                        "plant(Entities.Carrot)",
                    ]
                ),
            )
            script_path = self.write_script(
                root,
                "script.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        'run_time = simulate("worker", {Unlocks.Plant: 1, Unlocks.Carrots: 1}, {Items.Hay: 1, Items.Wood: 1}, {"START_VALUE": 4}, 7, 0)',
                        "quick_print(run_time)",
                    ]
                ),
            )

            runtime = HarnessRuntime(options=RuntimeOptions(capture_prints=True))
            result = runtime.run(Scenario(name="simulate", script_path=script_path))

            self.assertEqual(RunStatus.COMPLETED, result.status)
            self.assertIsNone(result.final_state.tiles[0][0].entity)
            self.assertTrue(any(event.name == "nested_run" for event in result.events))
            self.assertTrue(any(event.name == "simulate" for event in result.events))

    def test_fastest_reset_smoke_preset_can_run_direct_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script_path = self.write_script(
                root,
                "leader_reset.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        "unlock(Unlocks.Watering)",
                    ]
                ),
            )

            runtime = HarnessRuntime()
            scenario = build_preset_scenario(
                "fastest-reset-smoke",
                script_path=script_path,
            )

            result = runtime.run(scenario)

            self.assertEqual(RunStatus.COMPLETED, result.status)
            self.assertGreaterEqual(result.final_state.unlocks.get(Unlocks.Watering, 0), 1)

    def test_run_reinitializes_module_globals_between_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script_path = self.write_script(
                root,
                "script.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        "COUNTER = 0",
                        "COUNTER = COUNTER + 1",
                        'quick_print("counter", COUNTER)',
                    ]
                ),
            )

            runtime = HarnessRuntime(options=RuntimeOptions(capture_prints=True))
            scenario = Scenario(name="counter", script_path=script_path)

            first = runtime.run(scenario)
            second = runtime.run(scenario)

            first_outputs = [event for event in first.events if event.name == "quick_print"]
            second_outputs = [event for event in second.events if event.name == "quick_print"]
            self.assertEqual("counter 1", first_outputs[0].payload["text"])
            self.assertEqual("counter 1", second_outputs[0].payload["text"])

    def test_run_is_deterministic_and_does_not_mutate_scenario_initial_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script_path = self.write_script(
                root,
                "script.py",
                "\n".join(
                    [
                        "from __builtins__ import *",
                        "quick_print(random(), random())",
                        "till()",
                        "plant(Entities.Carrot)",
                    ]
                ),
            )

            initial_state = GameState(
                world_size=1,
                rng_seed=123,
                inventory={Items.Hay: 1.0, Items.Wood: 1.0},
                unlocks={Unlocks.Plant: 1, Unlocks.Carrots: 1},
            )
            scenario = Scenario(
                name="deterministic",
                script_path=script_path,
                initial_state=initial_state,
            )
            runtime = HarnessRuntime(options=RuntimeOptions(capture_prints=True))

            first = runtime.run(scenario)
            second = runtime.run(scenario)

            first_outputs = [event for event in first.events if event.name == "quick_print"]
            second_outputs = [event for event in second.events if event.name == "quick_print"]
            self.assertEqual(first_outputs[0].payload["text"], second_outputs[0].payload["text"])
            self.assertIsNone(scenario.initial_state.tiles[0][0].entity)

    def test_run_rejects_imports_outside_workspace_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script_path = self.write_script(
                root,
                "script.py",
                "\n".join(
                    [
                        "import math",
                    ]
                ),
            )

            runtime = HarnessRuntime()
            result = runtime.run(Scenario(name="bad-import", script_path=script_path))

            self.assertEqual(RunStatus.UNSUPPORTED, result.status)
            self.assertIn("imports outside the scenario workspace", result.errors[0])

    def test_run_captures_script_traceback_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script_path = self.write_script(
                root,
                "script.py",
                "\n".join(
                    [
                        'raise ValueError("boom")',
                    ]
                ),
            )

            runtime = HarnessRuntime()
            result = runtime.run(Scenario(name="boom", script_path=script_path))

            self.assertEqual(RunStatus.FAILED, result.status)
            self.assertIn("ValueError: boom", result.errors[0])
            self.assertEqual("run_failed", result.events[-1].name)


if __name__ == "__main__":
    unittest.main()
