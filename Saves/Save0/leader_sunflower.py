from Saves.Save0.__builtins__ import *
import Saves.Save0.utils as utils
utils.set_entrypoint("leader_sunflower")
from Saves.Save0.utils import *
from Saves.Save0.sunflower import *


LEADERBOARD_POWER_TARGET = 100000


def leaderboard_complete():
	return num_items(Items.Power) >= LEADERBOARD_POWER_TARGET


def equip_sunflower_hat():
	if num_unlocked(Hats.Golden_Sunflower_Hat) > 0:
		change_hat(Hats.Golden_Sunflower_Hat)
		return

	if num_unlocked(Hats.Sunflower_Hat) > 0:
		change_hat(Hats.Sunflower_Hat)


def run_leaderboard_cycle():
	run_sunflower_sweep()


def sunflower_leaderboard_main():
	switch_to_sunflower_world(SUNFLOWER_WORLD)
	equip_sunflower_hat()

	while not leaderboard_complete():
		run_leaderboard_cycle()


sunflower_leaderboard_main()
