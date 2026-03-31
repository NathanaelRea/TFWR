from __builtins__ import *
from utils import *

NORMAL_DRONE_START_ROW = 0
NORMAL_DRONE_ROW_STEP = 1
NORMAL_ACTIVE_COMPANIONS = {}
NORMAL_ACTIVE_ROW_COMPANIONS = {}
NORMAL_COMPANION_UPDATES = {}
NORMAL_ROW_COMPANIONS = {}
NORMAL_ROW_Y = -1


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
	global NORMAL_ACTIVE_ROW_COMPANIONS
	global NORMAL_ROW_COMPANIONS
	global NORMAL_ROW_Y

	NORMAL_COMPANION_UPDATES = {}
	NORMAL_ACTIVE_ROW_COMPANIONS = {}
	NORMAL_ROW_COMPANIONS = {}
	NORMAL_ROW_Y = -1


def set_normal_active_companions(companions):
	global NORMAL_ACTIVE_COMPANIONS
	NORMAL_ACTIVE_COMPANIONS = companions


def merge_normal_summary(merged_updates, summary):
	for target_y in summary["normal_companion_updates"]:
		if target_y not in merged_updates:
			merged_updates[target_y] = {}

		row_updates = summary["normal_companion_updates"][target_y]
		for target_key in row_updates:
			merged_updates[target_y][target_key] = row_updates[target_key]


def normal_summary():
	return {
		"normal_companion_updates": NORMAL_COMPANION_UPDATES,
	}


def prepare_normal_row():
	global NORMAL_ACTIVE_ROW_COMPANIONS
	global NORMAL_ROW_COMPANIONS
	global NORMAL_ROW_Y

	y = get_pos_y()
	if NORMAL_ROW_Y == y:
		return

	NORMAL_ROW_Y = y
	if y in NORMAL_ACTIVE_COMPANIONS:
		NORMAL_ACTIVE_ROW_COMPANIONS = NORMAL_ACTIVE_COMPANIONS[y]
	else:
		NORMAL_ACTIVE_ROW_COMPANIONS = {}
	NORMAL_ROW_COMPANIONS = {}


def normal_target_entity():
	prepare_normal_row()
	x = get_pos_x()
	y = get_pos_y()
	key = normal_key(x, y)

	if key in NORMAL_ROW_COMPANIONS:
		return NORMAL_ROW_COMPANIONS[key]

	if key in NORMAL_ACTIVE_ROW_COMPANIONS:
		return NORMAL_ACTIVE_ROW_COMPANIONS[key]

	return default_normal_entity(x, y)


def normal_companion_updates_for_row(target_y):
	if target_y not in NORMAL_COMPANION_UPDATES:
		NORMAL_COMPANION_UPDATES[target_y] = {}

	return NORMAL_COMPANION_UPDATES[target_y]


def note_normal_companion():
	prepare_normal_row()
	x = get_pos_x()
	y = get_pos_y()

	if (x + y) % 2 == 0:
		return

	current = get_entity_type()

	if current == None or current == Entities.Dead_Pumpkin:
		return

	companion = get_companion()
	if companion == None:
		return

	companion_entity, position = companion
	target_x, target_y = position
	target_key = normal_key(target_x, target_y)
	row_updates = normal_companion_updates_for_row(target_y)
	row_updates[target_key] = companion_entity

	if target_y == y:
		NORMAL_ROW_COMPANIONS[target_key] = companion_entity


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

	for target_y in STATE["normal_row_companions"]:
		count += len(STATE["normal_row_companions"][target_y])

	return count


def normal_sweep_worker():
	reset_normal_updates()
	set_normal_active_companions(NORMAL_ACTIVE_COMPANIONS)
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
	active_companions = STATE["normal_row_companions"]
	worker_count = drone_worker_count(normal_row_count(start_row))

	if worker_count <= 1:
		reset_normal_updates()
		set_normal_active_companions(active_companions)
		sweep_selected_rows(maintain_normal, start_row, 2)
		return normal_summary()

	handles = []
	fallback_rows = []
	merged_updates = {}
	worker = 1
	set_normal_active_companions(active_companions)

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
	set_normal_active_companions(active_companions)
	sweep_selected_rows(maintain_normal, start_row, worker_count * 2)
	merge_normal_summary(merged_updates, normal_summary())

	worker = 0
	while worker < len(handles):
		merge_normal_summary(merged_updates, wait_for(handles[worker]))
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		reset_normal_updates()
		set_normal_active_companions(active_companions)
		sweep_selected_rows(maintain_normal, fallback_rows[worker], worker_count * 2)
		merge_normal_summary(merged_updates, normal_summary())
		worker += 1

	return {
		"normal_companion_updates": merged_updates,
	}


def run_normal_sweep():
	merged_updates = {}
	merge_normal_summary(merged_updates, run_normal_row_group(0))
	merge_normal_summary(merged_updates, run_normal_row_group(1))
	STATE["normal_row_companions"] = merged_updates


def enter_normal_phase():
	enter_normal_world()


def normal_main():
	enter_normal_phase()

	while True:
		run_normal_sweep()
		quick_print(get_tick_count(), "normal", "companions", active_normal_companion_count())


if should_auto_run():
	normal_main()
