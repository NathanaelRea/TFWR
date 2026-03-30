from __builtins__ import *

SUNFLOWER_WORLD = 0
MAZE_WORLD = 1
PUMPKIN_WORLD = 2
NORMAL_WORLD = 3
DINO_WORLD = 4
CACTUS_WORLD = 5

NORMAL_WORLD_SWEEPS = 2
MAZE_RUNS_PER_PHASE = 10
PUMPKIN_FERTILIZER_BUFFER = 300
SOIL_WATER_LOW = 0.5
SOIL_WATER_TARGET = 0.9

PHASE_SOIL_WATERING = {
    NORMAL_WORLD: (SOIL_WATER_LOW, SOIL_WATER_TARGET),
    PUMPKIN_WORLD: (SOIL_WATER_LOW, SOIL_WATER_TARGET),
    SUNFLOWER_WORLD: (SOIL_WATER_LOW, SOIL_WATER_TARGET),
}

STATE = {
    "entrypoint": None,
    "maze_runs_remaining": 0,
    "normal_row_companions": {},
    "pumpkin_dead_repairs": 0,
    "pumpkin_ready_count": 0,
    "pumpkin_harvest_target": None,
    "sunflower_ready_count": 0,
    "sunflower_targets": {},
    "sunflower_max_petals": None,
    "sunflower_count": 0,
    "sunflower_verify_mode": False,
    "world_mode": NORMAL_WORLD,
    "next_world_mode": NORMAL_WORLD,
    "normal_sweeps_remaining": 0,
    "pumpkin_use_fertilizer": False,
    "pumpkin_verify_mode": False,
    "cactus_ready_count": 0,
}


def pumpkin_area():
    size = get_world_size()
    return size * size


def pumpkin_carrot_budget():
    return pumpkin_area() * 2


def can_run_pumpkin_phase():
    return num_items(Items.Carrot) >= pumpkin_carrot_budget()


def cactus_area():
    size = get_world_size()
    return size * size


def set_entrypoint(name):
    STATE["entrypoint"] = name


def should_auto_run():
    return STATE["entrypoint"] == None


def goto(x, y):
    size = get_world_size()
    current_x = get_pos_x()
    east_steps = (x - current_x + size) % size
    west_steps = (current_x - x + size) % size

    if east_steps <= west_steps:
        while east_steps > 0:
            move(East)
            east_steps -= 1
    else:
        while west_steps > 0:
            move(West)
            west_steps -= 1

    current_y = get_pos_y()
    north_steps = (y - current_y + size) % size
    south_steps = (current_y - y + size) % size

    if north_steps <= south_steps:
        while north_steps > 0:
            move(North)
            north_steps -= 1
    else:
        while south_steps > 0:
            move(South)
            south_steps -= 1


def set_ground(target_ground):
    while get_ground_type() != target_ground:
        till()


def prepare_ground(entity):
    if entity == Entities.Grass or entity == Entities.Tree:
        set_ground(Grounds.Grassland)
        return

    if (
        entity == Entities.Pumpkin
        or entity == Entities.Carrot
        or entity == Entities.Cactus
        or entity == Entities.Sunflower
    ):
        set_ground(Grounds.Soil)


def plant_target(entity):
    prepare_ground(entity)
    if entity != Entities.Grass:
        plant(entity)


def phase_soil_watering_profile():
    if STATE["world_mode"] not in PHASE_SOIL_WATERING:
        return None
    return PHASE_SOIL_WATERING[STATE["world_mode"]]


def maintain_soil_water():
    profile = phase_soil_watering_profile()
    if profile == None:
        return False
    if num_unlocked(Unlocks.Watering) <= 0:
        return False
    if num_items(Items.Water) <= 0:
        return False
    if get_ground_type() != Grounds.Soil:
        return False

    trigger_level, target_level = profile
    current_water = get_water()
    if current_water >= trigger_level:
        return False

    while current_water < target_level and num_items(Items.Water) > 0:
        if not use_item(Items.Water):
            return True
        current_water = get_water()

    return True


def sweep_world(visit_tile):
    size = get_world_size()
    sweep_rows(visit_tile, size)


def sweep_selected_rows(visit_tile, start_row, row_step):
    size = get_world_size()
    y = start_row

    while y < size:
        goto(0, y)
        x = 0

        while x < size:
            visit_tile()
            if x < size - 1:
                move(East)
            x += 1

        y += row_step


def sweep_rows(visit_tile, row_count):
    size = get_world_size()
    moving_east = True
    goto(0, 0)

    for y in range(row_count):
        for x in range(size):
            visit_tile()
            if x < size - 1:
                if moving_east:
                    move(East)
                else:
                    move(West)
        if y < row_count - 1:
            move(North)
            moving_east = not moving_east


def enter_pumpkin_world():
    STATE["world_mode"] = PUMPKIN_WORLD
    STATE["next_world_mode"] = PUMPKIN_WORLD
    STATE["maze_runs_remaining"] = 0
    STATE["normal_sweeps_remaining"] = 0
    STATE["pumpkin_use_fertilizer"] = False
    STATE["pumpkin_verify_mode"] = False
    STATE["sunflower_verify_mode"] = False


def switch_to_sunflower_world(target_world):
    STATE["world_mode"] = SUNFLOWER_WORLD
    STATE["next_world_mode"] = target_world
    STATE["maze_runs_remaining"] = 0
    STATE["normal_sweeps_remaining"] = 0
    STATE["pumpkin_use_fertilizer"] = False
    STATE["pumpkin_verify_mode"] = False
    STATE["sunflower_verify_mode"] = False


def enter_maze_world(target_world):
    STATE["world_mode"] = MAZE_WORLD
    STATE["next_world_mode"] = target_world
    STATE["maze_runs_remaining"] = MAZE_RUNS_PER_PHASE
    STATE["normal_sweeps_remaining"] = 0
    STATE["pumpkin_use_fertilizer"] = False
    STATE["pumpkin_verify_mode"] = False
    STATE["sunflower_verify_mode"] = False


def enter_normal_world():
    STATE["world_mode"] = NORMAL_WORLD
    STATE["next_world_mode"] = NORMAL_WORLD
    STATE["maze_runs_remaining"] = 0
    STATE["normal_row_companions"] = {}
    STATE["normal_sweeps_remaining"] = NORMAL_WORLD_SWEEPS
    STATE["pumpkin_use_fertilizer"] = False
    STATE["pumpkin_verify_mode"] = False
    STATE["sunflower_verify_mode"] = False


def enter_dino_world(target_world):
    STATE["world_mode"] = DINO_WORLD
    STATE["next_world_mode"] = target_world
    STATE["maze_runs_remaining"] = 0
    STATE["normal_sweeps_remaining"] = 0
    STATE["pumpkin_use_fertilizer"] = False
    STATE["pumpkin_verify_mode"] = False
    STATE["sunflower_verify_mode"] = False


def enter_cactus_world(target_world):
    STATE["world_mode"] = CACTUS_WORLD
    STATE["next_world_mode"] = target_world
    STATE["maze_runs_remaining"] = 0
    STATE["normal_sweeps_remaining"] = 0
    STATE["pumpkin_use_fertilizer"] = False
    STATE["pumpkin_verify_mode"] = False
    STATE["sunflower_verify_mode"] = False


def mega_farm_enabled():
    return num_unlocked(Unlocks.Megafarm) > 0 and max_drones() > 1


def drone_worker_count(task_count):
    if task_count <= 1:
        return 1

    if not mega_farm_enabled():
        return 1

    workers = max_drones()
    if workers < task_count:
        return workers

    return task_count


def reset_cycle_state():
    STATE["cactus_ready_count"] = 0
    STATE["pumpkin_dead_repairs"] = 0
    STATE["pumpkin_ready_count"] = 0
    STATE["pumpkin_harvest_target"] = None
    STATE["sunflower_ready_count"] = 0
    STATE["sunflower_targets"] = {}
    STATE["sunflower_max_petals"] = None
    STATE["sunflower_count"] = 0


def pumpkin_phase_name():
    if STATE["pumpkin_verify_mode"]:
        return "verify"
    if STATE["pumpkin_use_fertilizer"]:
        return "boost"
    return "seed"


def sunflower_phase_name():
    if STATE["sunflower_verify_mode"]:
        return "verify"
    return "seed"


def equip_phase_hat():
    if STATE["world_mode"] == SUNFLOWER_WORLD:
        change_hat(Hats.Sunflower_Hat)
        return

    if STATE["world_mode"] == MAZE_WORLD:
        change_hat(Hats.Gold_Hat)
        return

    if STATE["world_mode"] == PUMPKIN_WORLD:
        change_hat(Hats.Pumpkin_Hat)
        return

    if STATE["world_mode"] == CACTUS_WORLD:
        change_hat(Hats.Cactus_Hat)
        return

    if STATE["world_mode"] == DINO_WORLD:
        change_hat(Hats.Dinosaur_Hat)
        return

    change_hat(Hats.Cactus_Hat)
