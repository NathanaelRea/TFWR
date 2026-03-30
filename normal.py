from __builtins__ import *
from utils import *

NORMAL_DRONE_START_ROW = 0
NORMAL_DRONE_ROW_STEP = 1
NORMAL_ACTIVE_COMPANIONS = {}
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
	global NORMAL_ROW_COMPANIONS
	global NORMAL_ROW_Y

	NORMAL_COMPANION_UPDATES = {}
	NORMAL_ROW_COMPANIONS = {}
	NORMAL_ROW_Y = -1


def set_normal_active_companions(companions):
	global NORMAL_ACTIVE_COMPANIONS
	NORMAL_ACTIVE_COMPANIONS = companions


def normal_row_companions(row_parity):
	if row_parity == 0:
		return STATE["normal_even_row_companions"]
	return STATE["normal_odd_row_companions"]


def set_normal_row_companions(row_parity, companions):
	if row_parity == 0:
		STATE["normal_even_row_companions"] = companions
		return

	STATE["normal_odd_row_companions"] = companions


def merge_normal_summary(merged_updates, summary):
	for target_key in summary["normal_companion_updates"]:
		merged_updates[target_key] = summary["normal_companion_updates"][target_key]


def normal_summary():
	return {
		"normal_companion_updates": NORMAL_COMPANION_UPDATES,
	}


def prepare_normal_row():
	global NORMAL_ROW_COMPANIONS
	global NORMAL_ROW_Y

	y = get_pos_y()
	if NORMAL_ROW_Y == y:
		return

	NORMAL_ROW_Y = y
	NORMAL_ROW_COMPANIONS = {}


def normal_target_entity():
	prepare_normal_row()
	x = get_pos_x()
	y = get_pos_y()
	key = normal_key(x, y)

	if key in NORMAL_ROW_COMPANIONS:
		return NORMAL_ROW_COMPANIONS[key]

	if key in NORMAL_ACTIVE_COMPANIONS:
		return NORMAL_ACTIVE_COMPANIONS[key]

	return default_normal_entity(x, y)


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

	if target_y == y:
		NORMAL_ROW_COMPANIONS[target_key] = companion_entity
		return

	NORMAL_COMPANION_UPDATES[target_key] = companion_entity


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
	return (
		len(STATE["normal_even_row_companions"])
		+ len(STATE["normal_odd_row_companions"])
	)


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
	active_companions = normal_row_companions(start_row)
	target_row_parity = (start_row + 1) % 2
	worker_count = drone_worker_count(normal_row_count(start_row))

	if worker_count <= 1:
		reset_normal_updates()
		set_normal_active_companions(active_companions)
		sweep_selected_rows(maintain_normal, start_row, 2)
		set_normal_row_companions(target_row_parity, normal_summary()["normal_companion_updates"])
		return

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

	set_normal_row_companions(target_row_parity, merged_updates)


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
