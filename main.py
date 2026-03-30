from __builtins__ import *

MAZE_WORLD = 0
PUMPKIN_WORLD = 1
NORMAL_WORLD = 2

NORMAL_WORLD_SWEEPS = 2
PUMPKIN_FERTILIZER_BUFFER = 300

companions = {}
normal_crops = {}
pumpkin_dead_repairs = 0
pumpkin_ready_count = 0
pumpkin_harvest_target = None
world_mode = PUMPKIN_WORLD
normal_sweeps_remaining = 0
pumpkin_use_fertilizer = False
cactus_ready_count = 0


def pumpkin_area():
    size = get_world_size()
    return size * size


def cactus_area():
    size = get_world_size()
    return size * size


def choose_random_normal_crop():
    roll = random()

    if roll < 0.2:
        return Entities.Grass
    if roll < 0.55:
        return Entities.Carrot
    if roll < 0.75:
        return Entities.Tree
    if roll < 0.9:
        return Entities.Sunflower
    return Entities.Cactus


def normal_crop_for(x, y):
    loc = (x, y)

    if loc in companions:
        return companions[loc]

    if loc not in normal_crops:
        normal_crops[loc] = choose_random_normal_crop()

    return normal_crops[loc]


def reroll_normal_crop(x, y):
    normal_crops[(x, y)] = choose_random_normal_crop()


def planned_crop(x, y):
    if world_mode == PUMPKIN_WORLD:
        return Entities.Pumpkin
    return normal_crop_for(x, y)


def goto(x, y):
    while get_pos_x() < x:
        move(East)
    while get_pos_x() > x:
        move(West)
    while get_pos_y() < y:
        move(North)
    while get_pos_y() > y:
        move(South)


def set_ground(target_ground):
    while get_ground_type() != target_ground:
        till()


def prepare_ground(entity):
    if entity == Entities.Grass or entity == Entities.Tree:
        set_ground(Grounds.Grassland)
    elif (
        entity == Entities.Pumpkin
        or entity == Entities.Carrot
        or entity == Entities.Cactus
        or entity == Entities.Sunflower
    ):
        set_ground(Grounds.Soil)


def remember_companion():
    global companions

    companion = get_companion()
    if companion != None:
        crop, loc = companion
        companions[loc] = crop


def plant_target(entity):
    prepare_ground(entity)
    if entity != Entities.Grass:
        plant(entity)
    remember_companion()


def maintain_pumpkin():
    global pumpkin_dead_repairs
    global pumpkin_ready_count
    global pumpkin_harvest_target

    x = get_pos_x()
    y = get_pos_y()
    while True:
        current = get_entity_type()

        if current == Entities.Pumpkin:
            if can_harvest():
                pumpkin_ready_count += 1
                pumpkin_harvest_target = (x, y)
                remember_companion()
                return
            remember_companion()
            if not pumpkin_use_fertilizer:
                return
            if num_items(Items.Fertilizer) <= PUMPKIN_FERTILIZER_BUFFER:
                return
            use_item(Items.Fertilizer)
            continue

        if current == Entities.Dead_Pumpkin:
            pumpkin_dead_repairs += 1
            plant_target(Entities.Pumpkin)
            if not pumpkin_use_fertilizer:
                return
            if num_items(Items.Fertilizer) <= PUMPKIN_FERTILIZER_BUFFER:
                return
            use_item(Items.Fertilizer)
            continue

        if current != None:
            harvest()

        plant_target(Entities.Pumpkin)
        return


def install_normal_crop():
    target = normal_crop_for(get_pos_x(), get_pos_y())
    plant_target(target)


def maintain_normal():
    current = get_entity_type()
    global cactus_ready_count

    if current == Entities.Cactus:
        if can_harvest():
            cactus_ready_count += 1
        return

    if current != None:
        harvest()

    plant_target(Entities.Cactus)


def visit_tile():
    if world_mode == PUMPKIN_WORLD:
        maintain_pumpkin()
    else:
        maintain_normal()


def sweep_world():
    size = get_world_size()
    moving_east = True
    goto(0, 0)

    for y in range(size):
        for x in range(size):
            visit_tile()
            if x < size - 1:
                if moving_east:
                    move(East)
                else:
                    move(West)
        if y < size - 1:
            move(North)
            moving_east = not moving_east


def switch_to_pumpkin_world():
    global world_mode
    global normal_sweeps_remaining
    global pumpkin_use_fertilizer

    world_mode = PUMPKIN_WORLD
    normal_sweeps_remaining = 0
    pumpkin_use_fertilizer = False


def switch_to_normal_world():
    global world_mode
    global normal_crops
    global normal_sweeps_remaining
    global pumpkin_use_fertilizer

    world_mode = NORMAL_WORLD
    normal_crops = {}
    normal_sweeps_remaining = NORMAL_WORLD_SWEEPS
    pumpkin_use_fertilizer = False


def harvest_mega_pumpkin():
    if pumpkin_harvest_target == None:
        return False
    if pumpkin_ready_count != pumpkin_area():
        return False

    x, y = pumpkin_harvest_target
    goto(x, y)
    if get_entity_type() == Entities.Pumpkin and can_harvest():
        harvest()
        switch_to_normal_world()
        return True

    return False


def finish_normal_sweep():
    global normal_sweeps_remaining

    if world_mode != NORMAL_WORLD:
        return

    normal_sweeps_remaining -= 1
    if normal_sweeps_remaining <= 0:
        switch_to_pumpkin_world()


def reset_cycle_state():
    global companions
    global pumpkin_dead_repairs
    global pumpkin_ready_count
    global pumpkin_harvest_target

    companions = {}
    pumpkin_dead_repairs = 0
    pumpkin_ready_count = 0
    pumpkin_harvest_target = None


def mode_name():
    if world_mode == PUMPKIN_WORLD:
        return "pumpkin"
    return "normal"


def pumpkin_phase_name():
    if pumpkin_use_fertilizer:
        return "boost"
    return "seed"


def main():
    global pumpkin_use_fertilizer

    while True:
        change_hat(Hats.Pumpkin_Hat)
        reset_cycle_state()
        sweep_world()

        if world_mode == PUMPKIN_WORLD:
            harvest_mega_pumpkin()
            quick_print(
                mode_name(),
                pumpkin_phase_name(),
                pumpkin_ready_count,
                "/",
                pumpkin_area(),
                "repairs",
                pumpkin_dead_repairs,
            )
            if world_mode == PUMPKIN_WORLD and not pumpkin_use_fertilizer:
                pumpkin_use_fertilizer = True
        else:
            finish_normal_sweep()
            quick_print(mode_name(), "sweeps", normal_sweeps_remaining)


main()
