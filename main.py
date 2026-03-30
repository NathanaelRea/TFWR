from __builtins__ import *
import utils
utils.set_entrypoint("main")
from utils import *
from sunflower import *
from maze import *
from pumpkin import *
from cactus import *
from dino import *


def queue_world(target_world):
	if needs_sunflower_phase():
		switch_to_sunflower_world(target_world)
		return

	if needs_maze_phase():
		enter_maze_world(target_world)
		return

	if needs_dino_phase():
		enter_dino_world(target_world)
		return

	if target_world == PUMPKIN_WORLD:
		enter_pumpkin_world()
		return

	enter_normal_world()


def enter_target_world(target_world):
	if target_world == PUMPKIN_WORLD:
		enter_pumpkin_world()
		return

	enter_normal_world()


def finish_sunflower_phase():
	queue_world(STATE["next_world_mode"])


def finish_maze_phase():
	queue_world(STATE["next_world_mode"])


def finish_dino_phase():
	queue_world(STATE["next_world_mode"])


def finish_normal_sweep():
	if STATE["world_mode"] != NORMAL_WORLD:
		return

	STATE["normal_sweeps_remaining"] -= 1
	if STATE["normal_sweeps_remaining"] <= 0:
		queue_world(PUMPKIN_WORLD)


def run_phase_sweep():
	if STATE["world_mode"] == SUNFLOWER_WORLD:
		run_sunflower_sweep()
		return

	if STATE["world_mode"] == PUMPKIN_WORLD:
		run_pumpkin_sweep()
		return

	run_cactus_sweep()


def main():
	queue_world(NORMAL_WORLD)

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

				if STATE["maze_runs_remaining"] > 0 and needs_maze_phase():
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
					STATE["sunflower_ready_count"],
					"/",
					sunflower_area(),
					STATE["sunflower_max_petals"],
				)
			continue

		if STATE["world_mode"] == PUMPKIN_WORLD:
			if harvest_mega_pumpkin():
				quick_print("pumpkin", "harvest", pumpkin_area())
				queue_world(NORMAL_WORLD)
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
			continue

		if STATE["cactus_ready_count"] < cactus_area():
			quick_print("cactus", "grow", STATE["cactus_ready_count"], "/", cactus_area())
			continue

		sort_cactus_world()
		goto(0, 0)
		harvest()
		quick_print("cactus", "harvest", cactus_area())
		queue_world(PUMPKIN_WORLD)


main()
