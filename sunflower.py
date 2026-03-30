from __builtins__ import *
from utils import *

SUNFLOWER_DRONE_START_ROW = 0
SUNFLOWER_DRONE_ROW_STEP = 1
SUNFLOWER_HARVEST_START_INDEX = 0
SUNFLOWER_HARVEST_STEP = 1
SUNFLOWER_HARVEST_POSITIONS = []
SUNFLOWER_HARVEST_PETALS = None


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


def note_sunflower(assume_ready):
	petals = measure()
	STATE["sunflower_count"] += 1
	if not assume_ready and not can_harvest():
		return

	STATE["sunflower_ready_count"] += 1
	if STATE["sunflower_max_petals"] == None or petals > STATE["sunflower_max_petals"]:
		STATE["sunflower_max_petals"] = petals

	if petals not in STATE["sunflower_targets"]:
		STATE["sunflower_targets"][petals] = []

	STATE["sunflower_targets"][petals].append((get_pos_x(), get_pos_y()))


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


def wait_for_sunflower_growth():
	while True:
		if get_entity_type() != Entities.Sunflower:
			prepare_sunflower_tile()
			continue
		if can_harvest():
			return


def maintain_sunflower():
	if not prepare_sunflower_tile():
		return
	maintain_soil_water()
	note_sunflower(False)


def sunflower_summary():
	return {
		"sunflower_ready_count": STATE["sunflower_ready_count"],
		"sunflower_targets": STATE["sunflower_targets"],
		"sunflower_max_petals": STATE["sunflower_max_petals"],
		"sunflower_count": STATE["sunflower_count"],
	}


def merge_sunflower_summary(summary):
	STATE["sunflower_ready_count"] += summary["sunflower_ready_count"]
	STATE["sunflower_count"] += summary["sunflower_count"]

	if summary["sunflower_max_petals"] != None:
		if STATE["sunflower_max_petals"] == None or summary["sunflower_max_petals"] > STATE["sunflower_max_petals"]:
			STATE["sunflower_max_petals"] = summary["sunflower_max_petals"]

	for petals in summary["sunflower_targets"]:
		if petals not in STATE["sunflower_targets"]:
			STATE["sunflower_targets"][petals] = []

		positions = summary["sunflower_targets"][petals]
		index = 0

		while index < len(positions):
			STATE["sunflower_targets"][petals].append(positions[index])
			index += 1


def sunflower_sweep_worker():
	reset_cycle_state()
	sweep_selected_rows(maintain_sunflower, SUNFLOWER_DRONE_START_ROW, SUNFLOWER_DRONE_ROW_STEP)
	return sunflower_summary()


def sunflower_last_row(start_row, row_step):
	size = sunflower_rows()
	row = start_row
	last_row = start_row

	while row < size:
		last_row = row
		row += row_step

	return last_row


def run_sunflower_verify_rows(start_row, row_step):
	size = get_world_size()
	last_row = sunflower_last_row(start_row, row_step)
	y = start_row

	while y < size:
		goto(0, y)
		x = 0

		while x < size:
			if prepare_sunflower_tile():
				maintain_soil_water()
				is_last_tile = y == last_row and x == size - 1
				if is_last_tile:
					wait_for_sunflower_growth()
				note_sunflower(True)

			if x < size - 1:
				move(East)
			x += 1

		y += row_step


def sunflower_verify_worker():
	reset_cycle_state()
	run_sunflower_verify_rows(SUNFLOWER_DRONE_START_ROW, SUNFLOWER_DRONE_ROW_STEP)
	return sunflower_summary()


def run_sunflower_sweep():
	global SUNFLOWER_DRONE_START_ROW
	global SUNFLOWER_DRONE_ROW_STEP
	worker_count = drone_worker_count(sunflower_rows())
	reset_cycle_state()

	if worker_count <= 1:
		if STATE["sunflower_verify_mode"]:
			run_sunflower_verify_rows(0, 1)
		else:
			sweep_selected_rows(maintain_sunflower, 0, 1)
		return

	handles = []
	fallback_rows = []
	worker = 1

	while worker < worker_count:
		SUNFLOWER_DRONE_START_ROW = worker
		SUNFLOWER_DRONE_ROW_STEP = worker_count

		if STATE["sunflower_verify_mode"]:
			handle = spawn_drone(sunflower_verify_worker)
		else:
			handle = spawn_drone(sunflower_sweep_worker)
		if handle == None:
			fallback_rows.append(worker)
		else:
			handles.append(handle)

		worker += 1

	if STATE["sunflower_verify_mode"]:
		run_sunflower_verify_rows(0, worker_count)
	else:
		sweep_selected_rows(maintain_sunflower, 0, worker_count)

	worker = 0
	while worker < len(handles):
		merge_sunflower_summary(wait_for(handles[worker]))
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		if STATE["sunflower_verify_mode"]:
			run_sunflower_verify_rows(fallback_rows[worker], worker_count)
		else:
			sweep_selected_rows(maintain_sunflower, fallback_rows[worker], worker_count)
		worker += 1


def harvest_sunflower_positions(positions, petals, start_index, step):
	harvested = 0
	index = start_index

	while index < len(positions):
		x, y = positions[index]
		goto(x, y)

		if get_entity_type() == Entities.Sunflower and can_harvest():
			if measure() == petals:
				harvest()
				harvested += 1

		index += step

	return harvested


def sunflower_harvest_worker():
	return harvest_sunflower_positions(
		SUNFLOWER_HARVEST_POSITIONS,
		SUNFLOWER_HARVEST_PETALS,
		SUNFLOWER_HARVEST_START_INDEX,
		SUNFLOWER_HARVEST_STEP,
	)


def harvest_sunflower_group(positions, petals):
	global SUNFLOWER_HARVEST_POSITIONS
	global SUNFLOWER_HARVEST_PETALS
	global SUNFLOWER_HARVEST_START_INDEX
	global SUNFLOWER_HARVEST_STEP
	worker_count = drone_worker_count(len(positions))

	if worker_count <= 1:
		return harvest_sunflower_positions(positions, petals, 0, 1)

	SUNFLOWER_HARVEST_POSITIONS = positions
	SUNFLOWER_HARVEST_PETALS = petals

	handles = []
	fallback_indexes = []
	worker = 1

	while worker < worker_count:
		SUNFLOWER_HARVEST_START_INDEX = worker
		SUNFLOWER_HARVEST_STEP = worker_count

		handle = spawn_drone(sunflower_harvest_worker)
		if handle == None:
			fallback_indexes.append(worker)
		else:
			handles.append(handle)

		worker += 1

	harvested = harvest_sunflower_positions(positions, petals, 0, worker_count)

	worker = 0
	while worker < len(handles):
		harvested += wait_for(handles[worker])
		worker += 1

	worker = 0
	while worker < len(fallback_indexes):
		harvested += harvest_sunflower_positions(
			positions,
			petals,
			fallback_indexes[worker],
			worker_count,
		)
		worker += 1

	return harvested


def harvest_ordered_sunflowers():
	if STATE["sunflower_count"] != sunflower_area():
		return 0
	if STATE["sunflower_ready_count"] != sunflower_area():
		return 0
	if STATE["sunflower_max_petals"] == None:
		return 0

	petals = STATE["sunflower_max_petals"]
	harvested = 0

	while petals >= 0:
		if petals in STATE["sunflower_targets"]:
			positions = STATE["sunflower_targets"][petals]
			harvested += harvest_sunflower_group(positions, petals)

		petals -= 1

	return harvested


def sunflower_main():
	switch_to_sunflower_world(SUNFLOWER_WORLD)

	while True:
		run_sunflower_sweep()

		harvested = harvest_ordered_sunflowers()
		if harvested > 0:
			quick_print("sunflower", "harvest", harvested, STATE["sunflower_max_petals"])
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


if should_auto_run():
	sunflower_main()
