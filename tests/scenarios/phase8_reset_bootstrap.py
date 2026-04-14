from Saves.Save0.__builtins__ import *


def log_step(name, value, remaining):
	quick_print(get_tick_count(), "checkpoint", name, value, remaining)


def run():
	unlock(Unlocks.Speed)
	log_step("speed", num_unlocked(Unlocks.Speed), num_items(Items.Hay))
	unlock(Unlocks.Grass)
	log_step("grass", num_unlocked(Unlocks.Grass), num_items(Items.Hay))
	unlock(Unlocks.Expand)
	log_step("expand", get_world_size(), num_items(Items.Wood))
	unlock(Unlocks.Plant)
	unlock(Unlocks.Carrots)
	log_step("carrots", num_unlocked(Unlocks.Carrots), num_items(Items.Wood))
