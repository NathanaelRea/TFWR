from __builtins__ import *
from utils import *

PUMPKIN_DRONE_START_ROW = 0
PUMPKIN_DRONE_ROW_STEP = 1


def maintain_pumpkin():
    x = get_pos_x()
    y = get_pos_y()

    while True:
        current = get_entity_type()

        if current == Entities.Pumpkin:
            if can_harvest():
                STATE["pumpkin_ready_count"] += 1
                STATE["pumpkin_harvest_target"] = (x, y)
                return

            if not STATE["pumpkin_use_fertilizer"]:
                return
            if num_items(Items.Fertilizer) <= PUMPKIN_FERTILIZER_BUFFER:
                return

            use_item(Items.Fertilizer)
            continue

        if current == Entities.Dead_Pumpkin:
            STATE["pumpkin_dead_repairs"] += 1
            plant_target(Entities.Pumpkin)

            if not STATE["pumpkin_use_fertilizer"]:
                return
            if num_items(Items.Fertilizer) <= PUMPKIN_FERTILIZER_BUFFER:
                return

            use_item(Items.Fertilizer)
            continue

        if current != None:
            harvest()

        plant_target(Entities.Pumpkin)
        return


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


def pumpkin_main():
    enter_pumpkin_world()

    while True:
        equip_phase_hat()
        run_pumpkin_sweep()

        if harvest_mega_pumpkin():
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


if should_auto_run():
    pumpkin_main()
