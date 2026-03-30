from __builtins__ import *
from utils import *

PUMPKIN_DRONE_START_ROW = 0
PUMPKIN_DRONE_ROW_STEP = 1


def can_boost_pumpkin():
	if not STATE["pumpkin_use_fertilizer"]:
		return False
	return num_items(Items.Fertilizer) > PUMPKIN_FERTILIZER_BUFFER


def wait_for_pumpkin_growth():
	while True:
		current = get_entity_type()
		if current == Entities.Dead_Pumpkin:
			return current
		if current != Entities.Pumpkin:
			return current
		if can_harvest():
			return current


def note_ready_pumpkin(x, y):
	STATE["pumpkin_ready_count"] += 1
	STATE["pumpkin_harvest_target"] = (x, y)


def verify_pumpkin_tile(x, y):
	while True:
		current = get_entity_type()

		if current == Entities.Pumpkin:
			if can_harvest():
				note_ready_pumpkin(x, y)
				return

			if can_boost_pumpkin():
				use_item(Items.Fertilizer)
				maintain_soil_water()
				continue

			maintain_soil_water()
			wait_for_pumpkin_growth()
			continue

		if current == Entities.Dead_Pumpkin:
			STATE["pumpkin_dead_repairs"] += 1
			plant_target(Entities.Pumpkin)
			continue

		if current != None:
			harvest()

		plant_target(Entities.Pumpkin)


def maintain_pumpkin():
	x = get_pos_x()
	y = get_pos_y()

	if STATE["pumpkin_verify_mode"]:
		verify_pumpkin_tile(x, y)
		return

	current = get_entity_type()

	if current == Entities.Pumpkin:
		if can_harvest():
			note_ready_pumpkin(x, y)
			return

		if can_boost_pumpkin():
			use_item(Items.Fertilizer)
		maintain_soil_water()
		return

	if current == Entities.Dead_Pumpkin:
		verify_pumpkin_tile(x, y)
		return

	if current != None:
		harvest()

	plant_target(Entities.Pumpkin)
	maintain_soil_water()


def pumpkin_summary():
	return {
		"pumpkin_dead_repairs": STATE["pumpkin_dead_repairs"],
		"pumpkin_ready_count": STATE["pumpkin_ready_count"],
		"pumpkin_harvest_target": STATE["pumpkin_harvest_target"],
	}


def merge_pumpkin_summary(summary):
	STATE["pumpkin_dead_repairs"] += summary["pumpkin_dead_repairs"]
	STATE["pumpkin_ready_count"] += summary["pumpkin_ready_count"]

	if summary["pumpkin_harvest_target"] != None:
		STATE["pumpkin_harvest_target"] = summary["pumpkin_harvest_target"]


def pumpkin_sweep_worker():
	reset_cycle_state()
	sweep_selected_rows(maintain_pumpkin, PUMPKIN_DRONE_START_ROW, PUMPKIN_DRONE_ROW_STEP)
	return pumpkin_summary()


def replant_pumpkin_tile():
	current = get_entity_type()

	if current == Entities.Pumpkin:
		maintain_soil_water()
		return

	if current != None and current != Entities.Dead_Pumpkin:
		harvest()

	plant_target(Entities.Pumpkin)
	maintain_soil_water()


def pumpkin_replant_worker():
	sweep_selected_rows(replant_pumpkin_tile, PUMPKIN_DRONE_START_ROW, PUMPKIN_DRONE_ROW_STEP)


def run_pumpkin_replant_sweep():
	global PUMPKIN_DRONE_START_ROW
	global PUMPKIN_DRONE_ROW_STEP
	worker_count = drone_worker_count(get_world_size())

	if worker_count <= 1:
		sweep_world(replant_pumpkin_tile)
		return

	handles = []
	fallback_rows = []
	worker = 1

	while worker < worker_count:
		PUMPKIN_DRONE_START_ROW = worker
		PUMPKIN_DRONE_ROW_STEP = worker_count

		handle = spawn_drone(pumpkin_replant_worker)
		if handle == None:
			fallback_rows.append(worker)
		else:
			handles.append(handle)

		worker += 1

	sweep_selected_rows(replant_pumpkin_tile, 0, worker_count)

	worker = 0
	while worker < len(handles):
		wait_for(handles[worker])
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		sweep_selected_rows(replant_pumpkin_tile, fallback_rows[worker], worker_count)
		worker += 1


def run_pumpkin_sweep():
	global PUMPKIN_DRONE_START_ROW
	global PUMPKIN_DRONE_ROW_STEP
	worker_count = drone_worker_count(get_world_size())
	reset_cycle_state()

	if worker_count <= 1:
		sweep_world(maintain_pumpkin)
		return

	handles = []
	fallback_rows = []
	worker = 1

	while worker < worker_count:
		PUMPKIN_DRONE_START_ROW = worker
		PUMPKIN_DRONE_ROW_STEP = worker_count

		handle = spawn_drone(pumpkin_sweep_worker)
		if handle == None:
			fallback_rows.append(worker)
		else:
			handles.append(handle)

		worker += 1

	sweep_selected_rows(maintain_pumpkin, 0, worker_count)

	worker = 0
	while worker < len(handles):
		merge_pumpkin_summary(wait_for(handles[worker]))
		worker += 1

	worker = 0
	while worker < len(fallback_rows):
		sweep_selected_rows(maintain_pumpkin, fallback_rows[worker], worker_count)
		worker += 1


def harvest_mega_pumpkin():
	if STATE["pumpkin_harvest_target"] == None:
		return False
	if STATE["pumpkin_ready_count"] != pumpkin_area():
		return False

	x, y = STATE["pumpkin_harvest_target"]
	goto(x, y)

	if get_entity_type() != Entities.Pumpkin:
		return False
	if not can_harvest():
		return False

	harvest()
	return True


def restart_pumpkin_cycle():
	run_pumpkin_replant_sweep()
	reset_cycle_state()
	STATE["pumpkin_use_fertilizer"] = False
	STATE["pumpkin_verify_mode"] = False


def pumpkin_main():
	enter_pumpkin_world()

	while True:
		equip_phase_hat()
		run_pumpkin_sweep()

		if harvest_mega_pumpkin():
			restart_pumpkin_cycle()
			quick_print("pumpkin", "harvest", pumpkin_area())
		else:
			quick_print(
				"pumpkin",
				pumpkin_phase_name(),
				STATE["pumpkin_ready_count"],
				"/",
				pumpkin_area(),
				"repairs",
				STATE["pumpkin_dead_repairs"],
			)
			if not STATE["pumpkin_use_fertilizer"]:
				STATE["pumpkin_use_fertilizer"] = True
			elif not STATE["pumpkin_verify_mode"]:
				STATE["pumpkin_verify_mode"] = True


if should_auto_run():
	pumpkin_main()
