from __builtins__ import *
import utils
utils.set_entrypoint("main")
from utils import *
from normal import *
from sunflower import *
from maze import *
from pumpkin import *
from cactus import *
from dino import *


# Ordered from the reset notes and local docs:
# bootstrap to pumpkins quickly, pull power online once pumpkins exist,
# then scale pumpkins into cactus, mazes, megafarm, dinosaurs, and finally
# the expensive cleanup upgrades that are not part of the main leaderboard gate.
UPGRADE_ROUTE = [
	(Unlocks.Speed, 1),
	(Unlocks.Grass, 1),
	(Unlocks.Expand, 1),
	(Unlocks.Plant, 1),
	(Unlocks.Carrots, 1),
	(Unlocks.Speed, 2),
	(Unlocks.Watering, 1),
	(Unlocks.Trees, 1),
	(Unlocks.Pumpkins, 1),
	(Unlocks.Sunflowers, 1),
	(Unlocks.Fertilizer, 1),
	(Unlocks.Expand, 2),
	(Unlocks.Speed, 3),
	(Unlocks.Carrots, 2),
	(Unlocks.Trees, 2),
	(Unlocks.Watering, 2),
	(Unlocks.Pumpkins, 2),
	(Unlocks.Fertilizer, 2),
	(Unlocks.Grass, 2),
	(Unlocks.Expand, 3),
	(Unlocks.Speed, 4),
	(Unlocks.Carrots, 3),
	(Unlocks.Trees, 3),
	(Unlocks.Watering, 3),
	(Unlocks.Pumpkins, 3),
	(Unlocks.Polyculture, 1),
	(Unlocks.Fertilizer, 3),
	(Unlocks.Expand, 4),
	(Unlocks.Speed, 5),
	(Unlocks.Carrots, 4),
	(Unlocks.Trees, 4),
	(Unlocks.Watering, 4),
	(Unlocks.Pumpkins, 4),
	(Unlocks.Fertilizer, 4),
	(Unlocks.Grass, 3),
	(Unlocks.Expand, 5),
	(Unlocks.Carrots, 5),
	(Unlocks.Trees, 5),
	(Unlocks.Watering, 5),
	(Unlocks.Pumpkins, 5),
	(Unlocks.Cactus, 1),
	(Unlocks.Mazes, 1),
	(Unlocks.Expand, 6),
	(Unlocks.Pumpkins, 6),
	(Unlocks.Cactus, 2),
	(Unlocks.Mazes, 2),
	(Unlocks.Megafarm, 1),
	(Unlocks.Expand, 7),
	(Unlocks.Pumpkins, 7),
	(Unlocks.Cactus, 3),
	(Unlocks.Mazes, 3),
	(Unlocks.Megafarm, 2),
	(Unlocks.Dinosaurs, 1),
	(Unlocks.Carrots, 6),
	(Unlocks.Trees, 6),
	(Unlocks.Watering, 6),
	(Unlocks.Grass, 4),
	(Unlocks.Pumpkins, 8),
	(Unlocks.Cactus, 4),
	(Unlocks.Mazes, 4),
	(Unlocks.Megafarm, 3),
	(Unlocks.Dinosaurs, 2),
	(Unlocks.Expand, 8),
	(Unlocks.Carrots, 7),
	(Unlocks.Trees, 7),
	(Unlocks.Watering, 7),
	(Unlocks.Grass, 5),
	(Unlocks.Pumpkins, 9),
	(Unlocks.Cactus, 5),
	(Unlocks.Mazes, 5),
	(Unlocks.Megafarm, 4),
	(Unlocks.Dinosaurs, 3),
	(Unlocks.Expand, 9),
	(Unlocks.Carrots, 8),
	(Unlocks.Trees, 8),
	(Unlocks.Watering, 8),
	(Unlocks.Grass, 6),
	(Unlocks.Pumpkins, 10),
	(Unlocks.Cactus, 6),
	(Unlocks.Mazes, 6),
	(Unlocks.Megafarm, 5),
	(Unlocks.Dinosaurs, 4),
	(Unlocks.Dinosaurs, 5),
	(Unlocks.Dinosaurs, 6),
	(Unlocks.Leaderboard, 1),
	(Unlocks.Carrots, 9),
	(Unlocks.Trees, 9),
	(Unlocks.Watering, 9),
	(Unlocks.Grass, 7),
	(Unlocks.Carrots, 10),
	(Unlocks.Trees, 10),
	(Unlocks.Grass, 8),
	(Unlocks.Polyculture, 2),
	(Unlocks.Polyculture, 3),
	(Unlocks.Polyculture, 4),
	(Unlocks.Grass, 9),
	(Unlocks.Grass, 10),
	(Unlocks.Polyculture, 5),
]

POWER_LOW_WATERMARK = 16000
POWER_HIGH_WATERMARK = 64000
PUMPKIN_START_CARROT_MULTIPLIER = 2
ITEM_GOALS = {
	Items.Hay: 1000000000,
	Items.Wood: 10000000000,
	Items.Carrot: 1000000000,
	Items.Cactus: 1000000000,
	Items.Bone: 100000000,
	Items.Gold: 100000000,
}
LAST_LOGGED_UPGRADE_STEP = None


def phase_name(world_mode):
	if world_mode == SUNFLOWER_WORLD:
		return "sunflower"
	if world_mode == MAZE_WORLD:
		return "maze"
	if world_mode == PUMPKIN_WORLD:
		return "pumpkin"
	if world_mode == DINO_WORLD:
		return "dino"
	if world_mode == CACTUS_WORLD:
		return "cactus"
	return "normal"


def can_afford_cost(cost):
	if cost == None:
		return False

	for item in cost:
		if num_items(item) < cost[item]:
			return False

	return True


def missing_item_amount(missing_items, item):
	if item not in missing_items:
		return 0
	return missing_items[item]


def add_missing_costs(missing_items, cost):
	for item in cost:
		shortfall = cost[item] - num_items(item)
		if shortfall <= 0:
			continue

		if item not in missing_items:
			missing_items[item] = 0

		missing_items[item] += shortfall


def add_missing_goal_items(missing_items):
	for item in ITEM_GOALS:
		shortfall = ITEM_GOALS[item] - num_items(item)
		if shortfall <= 0:
			continue

		if item not in missing_items:
			missing_items[item] = 0

		missing_items[item] += shortfall


def next_upgrade_step():
	for target_unlock, target_level in UPGRADE_ROUTE:
		if num_unlocked(target_unlock) < target_level:
			return target_unlock, target_level

	return None


def step_cost(step):
	if step == None:
		return None

	target_unlock, target_level = step
	return get_cost(target_unlock, target_level)


def upgrade_missing_items():
	missing_items = {}
	step = next_upgrade_step()

	if step != None:
		cost = step_cost(step)
		if cost != None:
			add_missing_costs(missing_items, cost)
		return missing_items

	add_missing_goal_items(missing_items)
	return missing_items


def buy_available_upgrades():
	bought_any = False

	while True:
		step = next_upgrade_step()
		cost = step_cost(step)

		if not can_afford_cost(cost):
			return bought_any

		target_unlock, _target_level = step
		if not unlock(target_unlock):
			return bought_any

		bought_any = True

	return bought_any


def log_next_upgrade_step():
	global LAST_LOGGED_UPGRADE_STEP
	step = next_upgrade_step()

	if step == LAST_LOGGED_UPGRADE_STEP:
		return

	LAST_LOGGED_UPGRADE_STEP = step
	if step == None:
		quick_print(get_tick_count(), "next", "items")
		return

	target_unlock, target_level = step
	quick_print(get_tick_count(), "next", target_unlock, target_level)


def pumpkin_start_carrots():
	return pumpkin_carrot_budget() * PUMPKIN_START_CARROT_MULTIPLIER


def pumpkin_start_fertilizer():
	return PUMPKIN_FERTILIZER_BUFFER + pumpkin_area()


def can_start_pumpkin_phase():
	return (
		num_items(Items.Carrot) >= pumpkin_start_carrots()
		and num_items(Items.Fertilizer) >= pumpkin_start_fertilizer()
	)


def maze_phase_substance_budget():
	return maze_substance_cost() * MAZE_RUNS_PER_PHASE


def should_refill_weird_substance():
	return (
		num_unlocked(Unlocks.Mazes) > 0
		and num_items(Items.Weird_Substance) < maze_phase_substance_budget()
		and can_start_pumpkin_phase()
	)


def can_run_maze_block():
	return num_items(Items.Weird_Substance) >= maze_phase_substance_budget()


def can_finish_maze_phase():
	return num_items(Items.Weird_Substance) >= maze_substance_cost() * STATE["maze_runs_remaining"]


def can_farm_bones():
	return get_world_size() % 2 == 0 and dino_cactus_budget() != None


def should_fill_power_buffer(missing_items):
	power = num_items(Items.Power)

	if power < POWER_LOW_WATERMARK:
		return True

	if STATE["world_mode"] == SUNFLOWER_WORLD and power < POWER_HIGH_WATERMARK:
		return True

	return (
		missing_item_amount(missing_items, Items.Power) > 0
		and power < POWER_HIGH_WATERMARK
	)


def add_unique_world(worlds, world_mode):
	if world_mode not in worlds:
		worlds.append(world_mode)


def choose_random_world(worlds):
	index = random() * len(worlds) // 1
	return worlds[index]


def top_tier_worlds(missing_items):
	worlds = []
	missing_bones = missing_item_amount(missing_items, Items.Bone)
	missing_gold = missing_item_amount(missing_items, Items.Gold)
	missing_cactus = missing_item_amount(missing_items, Items.Cactus)

	if missing_bones > 0 and can_farm_bones():
		if needs_dino_phase():
			add_unique_world(worlds, DINO_WORLD)
		elif num_items(Items.Cactus) < dino_cactus_budget():
			add_unique_world(worlds, CACTUS_WORLD)

	if missing_gold > 0:
		if can_run_maze_block():
			add_unique_world(worlds, MAZE_WORLD)
		elif should_refill_weird_substance():
			add_unique_world(worlds, PUMPKIN_WORLD)

	if missing_cactus > 0:
		add_unique_world(worlds, CACTUS_WORLD)

	return worlds


def has_lower_tier_goal(missing_items):
	return (
		missing_item_amount(missing_items, Items.Hay) > 0
		or missing_item_amount(missing_items, Items.Wood) > 0
		or missing_item_amount(missing_items, Items.Carrot) > 0
	)


def choose_target_world():
	missing_items = upgrade_missing_items()
	missing_pumpkins = missing_item_amount(missing_items, Items.Pumpkin)
	missing_substance = missing_item_amount(missing_items, Items.Weird_Substance)
	missing_power = missing_item_amount(missing_items, Items.Power)
	power = num_items(Items.Power)

	if power < POWER_LOW_WATERMARK:
		return SUNFLOWER_WORLD

	if STATE["world_mode"] == SUNFLOWER_WORLD and power < POWER_HIGH_WATERMARK:
		return SUNFLOWER_WORLD

	worlds = top_tier_worlds(missing_items)
	if len(worlds) > 0:
		return choose_random_world(worlds)

	if missing_substance > 0:
		if can_start_pumpkin_phase():
			return PUMPKIN_WORLD
		return NORMAL_WORLD

	if missing_pumpkins > 0 and can_start_pumpkin_phase():
		return PUMPKIN_WORLD

	if should_fill_power_buffer(missing_items):
		return SUNFLOWER_WORLD

	if has_lower_tier_goal(missing_items):
		return NORMAL_WORLD

	if missing_power > 0:
		return SUNFLOWER_WORLD

	return NORMAL_WORLD


def enter_phase(world_mode):
	if world_mode == SUNFLOWER_WORLD:
		switch_to_sunflower_world(world_mode)
	elif world_mode == MAZE_WORLD:
		enter_maze_world(world_mode)
	elif world_mode == PUMPKIN_WORLD:
		enter_pumpkin_world()
	elif world_mode == DINO_WORLD:
		enter_dino_world(world_mode)
	elif world_mode == CACTUS_WORLD:
		enter_cactus_world(world_mode)
	else:
		enter_normal_phase()


def queue_recommended_world():
	buy_available_upgrades()
	log_next_upgrade_step()
	target_world = choose_target_world()
	previous_world = STATE["world_mode"]
	enter_phase(target_world)

	if previous_world != target_world:
		quick_print(get_tick_count(), "phase", phase_name(target_world))


def finish_sunflower_phase():
	queue_recommended_world()


def finish_maze_phase():
	wait_for_maze_swarm()
	queue_recommended_world()


def finish_dino_phase():
	queue_recommended_world()


def finish_cactus_phase():
	queue_recommended_world()


def finish_normal_sweep():
	if STATE["world_mode"] != NORMAL_WORLD:
		return

	STATE["normal_sweeps_remaining"] -= 1
	if STATE["normal_sweeps_remaining"] <= 0:
		queue_recommended_world()


def run_phase_sweep():
	if STATE["world_mode"] == SUNFLOWER_WORLD:
		run_sunflower_sweep()
		return

	if STATE["world_mode"] == PUMPKIN_WORLD:
		run_pumpkin_sweep()
		return

	if STATE["world_mode"] == CACTUS_WORLD:
		run_cactus_sweep()
		return

	run_normal_sweep()


def main():
	queue_recommended_world()

	while True:
		if STATE["world_mode"] == DINO_WORLD:
			harvested = run_dino_cycle()
			quick_print(get_tick_count(), "dino", "harvest", harvested, "bones", num_items(Items.Bone))
			finish_dino_phase()
			continue

		if STATE["world_mode"] == MAZE_WORLD:
			if run_maze_cycle():
				STATE["maze_runs_remaining"] -= 1
				quick_print(get_tick_count(), "maze", "harvest", MAZE_RUNS_PER_PHASE - STATE["maze_runs_remaining"])

				if STATE["maze_runs_remaining"] > 0 and can_finish_maze_phase():
					continue

				finish_maze_phase()
			else:
				quick_print(get_tick_count(), "maze", "skip", STATE["maze_runs_remaining"])
				finish_maze_phase()
			continue

		run_phase_sweep()

		if STATE["world_mode"] == SUNFLOWER_WORLD:
			harvested = STATE["sunflower_harvested_count"]
			if harvested > 0:
				quick_print(get_tick_count(), "sunflower", "harvest", harvested, "/", sunflower_area())
				finish_sunflower_phase()
			else:
				quick_print(
					get_tick_count(),
					"sunflower",
					sunflower_phase_name(),
					STATE["sunflower_count"],
					"/",
					sunflower_area(),
				)
			continue

		if STATE["world_mode"] == PUMPKIN_WORLD:
			if harvest_mega_pumpkin():
				restart_pumpkin_cycle()
				quick_print(get_tick_count(), "pumpkin", "harvest", pumpkin_area())
				queue_recommended_world()
			else:
				quick_print(
					get_tick_count(),
					"pumpkin",
					pumpkin_phase_name(),
					STATE["pumpkin_ready_count"],
					"/",
					pumpkin_area(),
					"repairs",
					STATE["pumpkin_dead_repairs"],
				)
				if not STATE["pumpkin_use_fertilizer"]:
					STATE["pumpkin_use_fertilizer"] = True
				elif not STATE["pumpkin_verify_mode"]:
					STATE["pumpkin_verify_mode"] = True
			continue

		if STATE["world_mode"] == CACTUS_WORLD:
			if STATE["cactus_ready_count"] < cactus_area():
				quick_print(get_tick_count(), "cactus", "grow", STATE["cactus_ready_count"], "/", cactus_area())
				continue

			sort_cactus_world()
			goto(0, 0)

			if get_entity_type() == Entities.Cactus and can_harvest():
				harvest()
				quick_print(get_tick_count(), "cactus", "harvest", cactus_area())
			else:
				quick_print(get_tick_count(), "cactus", "retry", STATE["cactus_ready_count"], "/", cactus_area())

			finish_cactus_phase()
			continue

		quick_print(
			get_tick_count(),
			"normal",
			"sweeps",
			STATE["normal_sweeps_remaining"],
			"companions",
			active_normal_companion_count(),
		)
		finish_normal_sweep()


main()
