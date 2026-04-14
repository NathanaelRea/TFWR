from __builtins__ import *


def run():
	till()
	plant(Entities.Pumpkin)
	quick_print(get_tick_count(), "checkpoint", "planted", get_entity_type())
	use_item(Items.Fertilizer)
	quick_print(get_tick_count(), "checkpoint", "ready", can_harvest(), get_water())
	harvest()
	quick_print(get_tick_count(), "checkpoint", "harvested", num_items(Items.Pumpkin))
