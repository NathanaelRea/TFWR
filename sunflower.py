from __builtins__ import *
from utils import *

SUNFLOWER_DRONE_START_ROW = 0
SUNFLOWER_DRONE_ROW_STEP = 1


def sunflower_key(x, y):
	return y * get_world_size() + x


def sunflower_rows():
	return get_world_size()


def sunflower_area():
	return sunflower_rows() * get_world_size()


def is_sunflower_tile(x, y):
	return y < sunflower_rows()


def power_threshold():
	return sunflower_area() * 2


def needs_sunflower_phase():
	return num_items(Items.Power) < power_threshold()


def prepare_sunflower_tile():
	current = get_entity_type()
	x = get_pos_x()
	y = get_pos_y()

	if not is_sunflower_tile(x, y):
		return False

	if current == Entities.Sunflower:
		return True

	if current != None and current != Entities.Dead_Pumpkin:
		harvest()

	plant_target(Entities.Sunflower)
	return True


def reset_sunflower_targets():
	STATE["sunflower_ready_count"] = 0
	STATE["sunflower_targets"] = {}
	STATE["sunflower_max_petals"] = None


def note_sunflower_target(petals):
	if petals == None:
		return

	if STATE["sunflower_max_petals"] == None or petals > STATE["sunflower_max_petals"]:
		reset_sunflower_targets()
		STATE["sunflower_max_petals"] = petals

	if petals != STATE["sunflower_max_petals"]:
		return

	if not can_harvest():
		return

	key = sunflower_key(get_pos_x(), get_pos_y())
	if key in STATE["sunflower_targets"]:
		return

	STATE["sunflower_targets"][key] = True
	STATE["sunflower_ready_count"] += 1


def maintain_sunflower():
	if not prepare_sunflower_tile():
		return

	STATE["sunflower_count"] += 1
	petals = measure()
	note_sunflower_target(petals)

	if can_harvest():
		return

	maintain_soil_water()


def sunflower_summary():
	return {
		"sunflower_count": STATE["sunflower_count"],
		"sunflower_max_petals": STATE["sunflower_max_petals"],
		"sunflower_targets": STATE["sunflower_targets"],
	}


def merge_sunflower_targets(max_petals, targets):
	if max_petals == None:
		return

	if STATE["sunflower_max_petals"] == None or max_petals > STATE["sunflower_max_petals"]:
		reset_sunflower_targets()
		STATE["sunflower_max_petals"] = max_petals

	if max_petals != STATE["sunflower_max_petals"]:
		return

	for key in targets:
		if key in STATE["sunflower_targets"]:
			continue

		STATE["sunflower_targets"][key] = True
		STATE["sunflower_ready_count"] += 1


def merge_sunflower_summary(summary):
	STATE["sunflower_count"] += summary["sunflower_count"]
	merge_sunflower_targets(
		summary["sunflower_max_petals"],
		summary["sunflower_targets"],
	)


def sunflower_sweep_worker():
	reset_cycle_state()
	sweep_selected_rows(maintain_sunflower, SUNFLOWER_DRONE_START_ROW, SUNFLOWER_DRONE_ROW_STEP)
	return sunflower_summary()


def run_sunflower_sweep():
	global SUNFLOWER_DRONE_START_ROW
	global SUNFLOWER_DRONE_ROW_STEP
	worker_count = drone_worker_count(sunflower_rows())
	reset_cycle_state()

	if worker_count <= 1:
		sweep_selected_rows(maintain_sunflower, 0, 1)
		return

	handles = []
	fallback_rows = []
	worker = 1

	while worker < worker_count:
		SUNFLOWER_DRONE_START_ROW = worker
		SUNFLOWER_DRONE_ROW_STEP = worker_count

		handle = spawn_drone(sunflower_sweep_worker)
		if handle == None:
			fallback_rows.append(worker)
		else:
			handles.append(handle)

		worker += 1

	sweep_selected_rows(maintain_sunflower, 0, worker_count)

	worker = 0
	while worker < len(handles):
		merge_sunflower_summary(wait_for(handles[worker]))
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		sweep_selected_rows(maintain_sunflower, fallback_rows[worker], worker_count)
		worker += 1


def harvest_targeted_sunflower():
	if get_entity_type() != Entities.Sunflower:
		return
	if not can_harvest():
		return

	key = sunflower_key(get_pos_x(), get_pos_y())
	if key not in STATE["sunflower_targets"]:
		return

	if measure() != STATE["sunflower_max_petals"]:
		return

	harvest()
	STATE["sunflower_harvested_count"] += 1
	plant_target(Entities.Sunflower)
	maintain_soil_water()


def harvest_ordered_sunflowers():
	if STATE["sunflower_ready_count"] <= 0:
		return 0

	sweep_world(harvest_targeted_sunflower)
	return STATE["sunflower_harvested_count"]


def sunflower_main():
	switch_to_sunflower_world(SUNFLOWER_WORLD)

	while True:
		run_sunflower_sweep()

		harvested = harvest_ordered_sunflowers()
		if harvested > 0:
			quick_print("sunflower", "harvest", harvested, "/", sunflower_area())
		else:
			quick_print(
				"sunflower",
				sunflower_phase_name(),
				STATE["sunflower_count"],
				"/",
				sunflower_area(),
			)


if should_auto_run():
	sunflower_main()
