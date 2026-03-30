from __builtins__ import *
from utils import *

NORMAL_DRONE_START_ROW = 0
NORMAL_DRONE_ROW_STEP = 1
NORMAL_COMPANION_UPDATES = {}


def normal_key(x, y):
	return y * get_world_size() + x


def default_normal_entity(x, y):
	if x % 2 == 0 and y % 2 == 0:
		return Entities.Tree

	if x % 2 == 1 and y % 2 == 1:
		return Entities.Grass

	return Entities.Carrot


def reset_normal_updates():
	global NORMAL_COMPANION_UPDATES
	NORMAL_COMPANION_UPDATES = {}


def apply_normal_companion_update(source_key, update):
	if source_key in STATE["normal_companion_sources"]:
		existing = STATE["normal_companion_sources"][source_key]
		if existing != None:
			target_key = existing[0]
			if target_key in STATE["normal_companion_targets"]:
				target_record = STATE["normal_companion_targets"][target_key]
				if target_record != None and target_record[0] == source_key:
					STATE["normal_companion_targets"][target_key] = None

	STATE["normal_companion_sources"][source_key] = None

	if update == None:
		return

	target_key = update[0]
	companion_entity = update[1]
	STATE["normal_companion_sources"][source_key] = [target_key, companion_entity]
	STATE["normal_companion_targets"][target_key] = [source_key, companion_entity]


def merge_normal_summary(summary):
	for source_key in summary["normal_companion_updates"]:
		apply_normal_companion_update(source_key, summary["normal_companion_updates"][source_key])


def normal_summary():
	return {
		"normal_companion_updates": NORMAL_COMPANION_UPDATES,
	}


def normal_target_entity():
	x = get_pos_x()
	y = get_pos_y()
	key = normal_key(x, y)

	if key in STATE["normal_companion_targets"]:
		target_record = STATE["normal_companion_targets"][key]
		if target_record != None:
			return target_record[1]

	return default_normal_entity(x, y)


def note_normal_companion():
	source_key = normal_key(get_pos_x(), get_pos_y())
	current = get_entity_type()

	if current == None or current == Entities.Dead_Pumpkin:
		NORMAL_COMPANION_UPDATES[source_key] = None
		return

	companion = get_companion()
	if companion == None:
		NORMAL_COMPANION_UPDATES[source_key] = None
		return

	companion_entity, position = companion
	target_x, target_y = position
	NORMAL_COMPANION_UPDATES[source_key] = [normal_key(target_x, target_y), companion_entity]


def maintain_normal():
	desired = normal_target_entity()
	current = get_entity_type()

	if current == desired:
		if can_harvest():
			harvest()
			plant_target(desired)
	else:
		if current != None:
			harvest()
		plant_target(desired)

	maintain_soil_water()
	note_normal_companion()


def active_normal_companion_count():
	count = 0

	for target_key in STATE["normal_companion_targets"]:
		if STATE["normal_companion_targets"][target_key] != None:
			count += 1

	return count


def normal_sweep_worker():
	reset_normal_updates()
	sweep_selected_rows(maintain_normal, NORMAL_DRONE_START_ROW, NORMAL_DRONE_ROW_STEP)
	return normal_summary()


def normal_row_count(start_row):
	size = get_world_size()
	count = 0
	row = start_row

	while row < size:
		count += 1
		row += 2

	return count


def run_normal_row_group(start_row):
	global NORMAL_DRONE_START_ROW
	global NORMAL_DRONE_ROW_STEP
	worker_count = drone_worker_count(normal_row_count(start_row))

	if worker_count <= 1:
		reset_normal_updates()
		sweep_selected_rows(maintain_normal, start_row, 2)
		merge_normal_summary(normal_summary())
		return

	handles = []
	fallback_rows = []
	worker = 1

	while worker < worker_count:
		NORMAL_DRONE_START_ROW = start_row + worker * 2
		NORMAL_DRONE_ROW_STEP = worker_count * 2

		handle = spawn_drone(normal_sweep_worker)
		if handle == None:
			fallback_rows.append(NORMAL_DRONE_START_ROW)
		else:
			handles.append(handle)

		worker += 1

	reset_normal_updates()
	sweep_selected_rows(maintain_normal, start_row, worker_count * 2)
	merge_normal_summary(normal_summary())

	worker = 0
	while worker < len(handles):
		merge_normal_summary(wait_for(handles[worker]))
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		reset_normal_updates()
		sweep_selected_rows(maintain_normal, fallback_rows[worker], worker_count * 2)
		merge_normal_summary(normal_summary())
		worker += 1


def run_normal_sweep():
	run_normal_row_group(0)
	run_normal_row_group(1)


def enter_normal_phase():
	enter_normal_world()


def normal_main():
	enter_normal_phase()

	while True:
		equip_phase_hat()
		run_normal_sweep()
		quick_print("normal", "companions", active_normal_companion_count())


if should_auto_run():
	normal_main()
