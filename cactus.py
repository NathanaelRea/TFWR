from __builtins__ import *
from utils import *

CACTUS_SWEEP_ROW_STEP = 1
CACTUS_ROW_SORT_STEP = 1
CACTUS_COLUMN_SORT_STEP = 1


def maintain_cactus():
	current = get_entity_type()

	if current == Entities.Cactus:
		if can_harvest():
			STATE["cactus_ready_count"] += 1
		return

	if current != None:
		harvest()

	plant_target(Entities.Cactus)


def cactus_summary():
	return {
		"cactus_ready_count": STATE["cactus_ready_count"],
	}


def merge_cactus_summary(summary):
	STATE["cactus_ready_count"] += summary["cactus_ready_count"]


def cactus_sweep_worker():
	reset_cycle_state()
	sweep_selected_rows(maintain_cactus, get_pos_y(), CACTUS_SWEEP_ROW_STEP)
	return cactus_summary()


def run_cactus_sweep():
	global CACTUS_SWEEP_ROW_STEP
	worker_count = drone_worker_count(get_world_size())
	reset_cycle_state()

	if worker_count <= 1:
		sweep_world(maintain_cactus)
		return

	handles = []
	fallback_rows = []
	worker = 1

	CACTUS_SWEEP_ROW_STEP = worker_count

	while worker < worker_count:
		goto(0, worker)
		handle = spawn_drone(cactus_sweep_worker)
		if handle == None:
			fallback_rows.append(worker)
		else:
			handles.append(handle)

		worker += 1

	sweep_selected_rows(maintain_cactus, 0, worker_count)

	worker = 0
	while worker < len(handles):
		merge_cactus_summary(wait_for(handles[worker]))
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		sweep_selected_rows(maintain_cactus, fallback_rows[worker], worker_count)
		worker += 1


def sort_cactus_row(row):
	size = get_world_size()
	if size < 2:
		return

	goto(0, row)

	while True:
		swapped = False
		x = 0

		while x + 1 < size:
			if measure() > measure(East):
				swap(East)
				swapped = True

			move(East)
			x += 1

		if not swapped:
			return

		swapped = False

		while x > 0:
			if measure(West) > measure():
				swap(West)
				swapped = True

			move(West)
			x -= 1

		if not swapped:
			return


def sort_cactus_rows(start_row, row_step):
	size = get_world_size()
	row = start_row

	while row < size:
		sort_cactus_row(row)
		row += row_step


def cactus_row_sort_worker():
	sort_cactus_rows(get_pos_y(), CACTUS_ROW_SORT_STEP)


def run_cactus_row_sort():
	global CACTUS_ROW_SORT_STEP
	worker_count = drone_worker_count(get_world_size())

	if worker_count <= 1:
		sort_cactus_rows(0, 1)
		return

	handles = []
	fallback_rows = []
	worker = 1

	CACTUS_ROW_SORT_STEP = worker_count

	while worker < worker_count:
		goto(0, worker)
		handle = spawn_drone(cactus_row_sort_worker)
		if handle == None:
			fallback_rows.append(worker)
		else:
			handles.append(handle)

		worker += 1

	sort_cactus_rows(0, worker_count)

	worker = 0
	while worker < len(handles):
		wait_for(handles[worker])
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		sort_cactus_rows(fallback_rows[worker], worker_count)
		worker += 1


def sort_cactus_column(column):
	size = get_world_size()
	if size < 2:
		return

	goto(column, 0)

	while True:
		swapped = False
		y = 0

		while y + 1 < size:
			if measure() > measure(North):
				swap(North)
				swapped = True

			move(North)
			y += 1

		if not swapped:
			return

		swapped = False

		while y > 0:
			if measure(South) > measure():
				swap(South)
				swapped = True

			move(South)
			y -= 1

		if not swapped:
			return


def sort_cactus_columns(start_column, column_step):
	size = get_world_size()
	column = start_column

	while column < size:
		sort_cactus_column(column)
		column += column_step


def cactus_column_sort_worker():
	sort_cactus_columns(get_pos_x(), CACTUS_COLUMN_SORT_STEP)


def run_cactus_column_sort():
	global CACTUS_COLUMN_SORT_STEP
	worker_count = drone_worker_count(get_world_size())

	if worker_count <= 1:
		sort_cactus_columns(0, 1)
		return

	handles = []
	fallback_columns = []
	worker = 1

	CACTUS_COLUMN_SORT_STEP = worker_count

	while worker < worker_count:
		goto(worker, 0)
		handle = spawn_drone(cactus_column_sort_worker)
		if handle == None:
			fallback_columns.append(worker)
		else:
			handles.append(handle)

		worker += 1

	sort_cactus_columns(0, worker_count)

	worker = 0
	while worker < len(handles):
		wait_for(handles[worker])
		worker += 1

	worker = 0
	while worker < len(fallback_columns):
		sort_cactus_columns(fallback_columns[worker], worker_count)
		worker += 1


def sort_cactus_world():
	run_cactus_row_sort()
	run_cactus_column_sort()


def cactus_main():
	enter_cactus_world(CACTUS_WORLD)

	while True:
		equip_phase_hat()
		run_cactus_sweep()

		if STATE["cactus_ready_count"] < cactus_area():
			quick_print("cactus", "grow", STATE["cactus_ready_count"], "/", cactus_area())
			continue

		sort_cactus_world()
		goto(0, 0)
		harvest()
		quick_print("cactus", "harvest", cactus_area())


if should_auto_run():
	cactus_main()
