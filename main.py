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


TRACKED_UPGRADES = [
	Unlocks.Speed,
	Unlocks.Expand,
	Unlocks.Grass,
	Unlocks.Trees,
	Unlocks.Carrots,
	Unlocks.Watering,
	Unlocks.Pumpkins,
	Unlocks.Fertilizer,
	Unlocks.Sunflowers,
	Unlocks.Polyculture,
	Unlocks.Cactus,
	Unlocks.Mazes,
	Unlocks.Dinosaurs,
	Unlocks.Megafarm,
]

POWER_LOW_WATERMARK = 10000
POWER_HIGH_WATERMARK = 20000
PUMPKIN_START_CARROT_MULTIPLIER = 2
ITEM_GOALS = {
	Items.Hay: 1000000000,
	Items.Wood: 10000000000,
	Items.Carrot: 1000000000,
	Items.Cactus: 1000000000,
	Items.Bone: 100000000,
	Items.Gold: 100000000,
}


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


def next_upgrade_cost(unlock):
	return get_cost(unlock, num_unlocked(unlock) + 1)


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


def upgrade_missing_items():
	missing_items = {}

	for unlock in TRACKED_UPGRADES:
		cost = next_upgrade_cost(unlock)
		if cost != None:
			add_missing_costs(missing_items, cost)

	add_missing_goal_items(missing_items)
	return missing_items


def buy_available_upgrades():
	bought_any = False
	keep_checking = True

	while keep_checking:
		keep_checking = False

		for target_unlock in TRACKED_UPGRADES:
			cost = next_upgrade_cost(target_unlock)
			if not can_afford_cost(cost):
				continue

			if unlock(target_unlock):
				quick_print("upgrade", target_unlock, num_unlocked(target_unlock))
				bought_any = True
				keep_checking = True

	return bought_any


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


def choose_target_world():
	missing_items = upgrade_missing_items()
	missing_bones = missing_item_amount(missing_items, Items.Bone)
	missing_gold = missing_item_amount(missing_items, Items.Gold)
	missing_pumpkins = missing_item_amount(missing_items, Items.Pumpkin)
	missing_cactus = missing_item_amount(missing_items, Items.Cactus)
	missing_power = missing_item_amount(missing_items, Items.Power)

	if should_fill_power_buffer(missing_items):
		return SUNFLOWER_WORLD

	if missing_bones > 0 and can_farm_bones():
		if needs_dino_phase():
			return DINO_WORLD

		if num_items(Items.Cactus) < dino_cactus_budget():
			return CACTUS_WORLD

	if missing_gold > 0 and can_run_maze_block():
		return MAZE_WORLD

	if missing_pumpkins > 0 and can_start_pumpkin_phase():
		return PUMPKIN_WORLD

	if missing_cactus > 0:
		return CACTUS_WORLD

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
	target_world = choose_target_world()
	previous_world = STATE["world_mode"]
	enter_phase(target_world)

	if previous_world != target_world:
		quick_print("phase", phase_name(target_world))


def finish_sunflower_phase():
	queue_recommended_world()


def finish_maze_phase():
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
		if STATE["world_mode"] != DINO_WORLD:
			equip_phase_hat()

		if STATE["world_mode"] == DINO_WORLD:
			harvested = run_dino_cycle()
			quick_print("dino", "harvest", harvested, "bones", num_items(Items.Bone))
			finish_dino_phase()
			continue

		if STATE["world_mode"] == MAZE_WORLD:
			if run_maze_cycle():
				STATE["maze_runs_remaining"] -= 1
				quick_print("maze", "harvest", MAZE_RUNS_PER_PHASE - STATE["maze_runs_remaining"])

				if STATE["maze_runs_remaining"] > 0 and can_finish_maze_phase():
					continue

				finish_maze_phase()
			else:
				quick_print("maze", "skip", STATE["maze_runs_remaining"])
				finish_maze_phase()
			continue

		run_phase_sweep()

		if STATE["world_mode"] == SUNFLOWER_WORLD:
			harvested = harvest_ordered_sunflowers()
			if harvested > 0:
				quick_print("sunflower", "harvest", harvested, STATE["sunflower_max_petals"])
				finish_sunflower_phase()
			else:
				quick_print(
					"sunflower",
					sunflower_phase_name(),
					STATE["sunflower_ready_count"],
					"/",
					sunflower_area(),
					STATE["sunflower_max_petals"],
				)
				if not STATE["sunflower_verify_mode"]:
					STATE["sunflower_verify_mode"] = True
			continue

		if STATE["world_mode"] == PUMPKIN_WORLD:
			if harvest_mega_pumpkin():
				restart_pumpkin_cycle()
				quick_print("pumpkin", "harvest", pumpkin_area())
				queue_recommended_world()
			else:
				quick_print(
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
				quick_print("cactus", "grow", STATE["cactus_ready_count"], "/", cactus_area())
				continue

			sort_cactus_world()
			goto(0, 0)

			if get_entity_type() == Entities.Cactus and can_harvest():
				harvest()
				quick_print("cactus", "harvest", cactus_area())
			else:
				quick_print("cactus", "retry", STATE["cactus_ready_count"], "/", cactus_area())

			finish_cactus_phase()
			continue

		quick_print(
			"normal",
			"sweeps",
			STATE["normal_sweeps_remaining"],
			"companions",
			active_normal_companion_count(),
		)
		finish_normal_sweep()


main()
