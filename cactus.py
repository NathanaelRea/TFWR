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
    phase = 0

    while phase < size:
        x = phase % 2
        goto(x, row)

        while x + 1 < size:
            if measure() > measure(East):
                swap(East)
            x += 2

            if x + 1 < size:
                move(East)
                move(East)

        phase += 1


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
    phase = 0

    while phase < size:
        y = phase % 2
        goto(column, y)

        while y + 1 < size:
            if measure() > measure(North):
                swap(North)
            y += 2

            if y + 1 < size:
                move(North)
                move(North)

        phase += 1


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


def cactus_world_sorted():
    size = get_world_size()
    previous_row = []
    y = 0

    while y < size:
        goto(0, y)
        current_row = []
        previous_value = None
        x = 0

        while x < size:
            if get_entity_type() != Entities.Cactus or not can_harvest():
                return False

            value = measure()

            if previous_value != None and previous_value > value:
                return False

            if y > 0 and previous_row[x] > value:
                return False

            current_row.append(value)
            previous_value = value

            if x < size - 1:
                move(East)

            x += 1

        previous_row = current_row
        y += 1

    return True


def sort_cactus_world():
    attempts = 0

    while attempts < 2:
        run_cactus_row_sort()
        run_cactus_column_sort()

        if cactus_world_sorted():
            return True

        attempts += 1

    return False


def cactus_main():
    enter_normal_world()

    while True:
        equip_phase_hat()
        run_cactus_sweep()

        if STATE["cactus_ready_count"] < cactus_area():
            quick_print("cactus", "grow", STATE["cactus_ready_count"], "/", cactus_area())
            continue

        cactus_sorted = sort_cactus_world()
        goto(0, 0)

        if cactus_sorted and get_entity_type() == Entities.Cactus and can_harvest():
            harvest()
            quick_print("cactus", "harvest", cactus_area())
        else:
            quick_print("cactus", "sort", STATE["cactus_ready_count"], "/", cactus_area())


if should_auto_run():
    cactus_main()
