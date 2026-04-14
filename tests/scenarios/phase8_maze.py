from Saves.Save0.__builtins__ import *


def run():
	plant(Entities.Bush)
	use_item(Items.Weird_Substance, 2)
	target = measure()
	quick_print(get_tick_count(), "checkpoint", "treasure", target[0], target[1])
	move(North)
	move(East)
	quick_print(get_tick_count(), "checkpoint", "tile", get_entity_type())
	harvest()
	quick_print(get_tick_count(), "checkpoint", "gold", num_items(Items.Gold))
