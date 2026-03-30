from __builtins__ import *
import utils
utils.set_entrypoint("leader_sunflower")
from utils import *
from sunflower import *


LEADERBOARD_POWER_TARGET = 100000


def leaderboard_complete():
	return num_items(Items.Power) >= LEADERBOARD_POWER_TARGET


def run_leaderboard_cycle():
	run_sunflower_sweep()

	if harvest_ordered_sunflowers() > 0:
		return

	if not STATE["sunflower_verify_mode"]:
		STATE["sunflower_verify_mode"] = True


def sunflower_leaderboard_main():
	switch_to_sunflower_world(SUNFLOWER_WORLD)

	while not leaderboard_complete():
		run_leaderboard_cycle()


sunflower_leaderboard_main()
