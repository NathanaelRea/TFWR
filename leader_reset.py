# Fastest reset scaffold.
#
# Python-style control flow is assumed to be available from the start of the
# leaderboard run. The real gating is on farm actions and research unlocks, so
# the phases follow the confirmed unlock dependency layers for the reset route.

from __builtins__ import *


PHASE_0_QUEUE = [
    Unlocks.Plant,
]

PHASE_1_QUEUE = [
    Unlocks.Carrots,
    Unlocks.Trees,
    Unlocks.Watering,
]

PHASE_2_QUEUE = [
    Unlocks.Pumpkins,
    Unlocks.Sunflowers,
    Unlocks.Fertilizer,
]

PHASE_3_QUEUE = [
    Unlocks.Polyculture,
    Unlocks.Cactus,
    Unlocks.Mazes,
]

PHASE_4_QUEUE = [
    Unlocks.Dinosaurs,
    Unlocks.Megafarm,
]

PHASE_5_QUEUE = [
    Unlocks.Leaderboard,
]


def can_afford(target):
    cost = get_cost(target)
    if cost == None:
        return False

    for item in cost:
        if num_items(item) < cost[item]:
            return False

    return True


def buy_priority(shopping_list):
    for target in shopping_list:
        if can_afford(target):
            if unlock(target):
                quick_print("unlock", target, num_unlocked(target))
                return True
    return False


def buy_bootstrap_unlock():
    if num_unlocked(Unlocks.Speed) <= 0 and can_afford(Unlocks.Speed):
        if unlock(Unlocks.Speed):
            quick_print("unlock", Unlocks.Speed, num_unlocked(Unlocks.Speed))
            return True

    if num_unlocked(Unlocks.Grass) <= 0 and can_afford(Unlocks.Grass):
        if unlock(Unlocks.Grass):
            quick_print("unlock", Unlocks.Grass, num_unlocked(Unlocks.Grass))
            return True

    if get_world_size() <= 1 and can_afford(Unlocks.Expand):
        if unlock(Unlocks.Expand):
            quick_print("unlock", Unlocks.Expand, num_unlocked(Unlocks.Expand))
            return True

    return buy_priority(PHASE_0_QUEUE)


def buy_phase1_unlock():
    if num_unlocked(Unlocks.Expand) <= 1 and can_afford(Unlocks.Expand):
        if unlock(Unlocks.Expand):
            quick_print("unlock", Unlocks.Expand, num_unlocked(Unlocks.Expand))
            return True

    if num_unlocked(Unlocks.Speed) <= 1 and can_afford(Unlocks.Speed):
        if unlock(Unlocks.Speed):
            quick_print("unlock", Unlocks.Speed, num_unlocked(Unlocks.Speed))
            return True

    return buy_priority(PHASE_1_QUEUE)


def goto(x, y):
    size = get_world_size()
    current_x = get_pos_x()
    current_y = get_pos_y()

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


def set_ground_for(entity):
    if entity == Entities.Grass or entity == Entities.Bush or entity == Entities.Tree:
        while get_ground_type() != Grounds.Grassland:
            till()
        return

    while get_ground_type() != Grounds.Soil:
        till()


def farm_simple(crop, iterations):
    while iterations > 0:
        if not can_harvest():
            continue

        harvest()
        set_ground_for(crop)
        if crop != Entities.Grass:
            plant(crop)
        iterations -= 1


def farm_simple_strip(crop, iterations):
    while iterations > 0:
        if can_harvest():
            harvest()
            iterations -= 1

        if crop != Entities.Grass:
            set_ground_for(crop)
            plant(crop)

        if get_world_size() > 1:
            move(North)


def visit_tile(crop):
    entity = get_entity_type()

    if entity == Entities.Dead_Pumpkin:
        harvest()
    elif can_harvest():
        harvest()

    if crop == Entities.Grass:
        return

    set_ground_for(crop)

    if get_entity_type() != crop:
        plant(crop)


def farm_grid(crop):
    size = get_world_size()
    goto(0, 0)

    for y in range(size):
        if y % 2 == 0:
            for x in range(size):
                visit_tile(crop)
                if x < size - 1:
                    move(East)
        else:
            for x in range(size):
                visit_tile(crop)
                if x < size - 1:
                    move(West)

        if y < size - 1:
            move(North)


def buy_expands_until(target_size):
    while get_world_size() < target_size:
        if not can_afford(Unlocks.Expand):
            return False
        if not unlock(Unlocks.Expand):
            return False
    return True


def choose_simple_crop():
    if num_unlocked(Entities.Bush) > 0:
        return Entities.Bush
    return Entities.Grass


def choose_midgame_crop():
    if num_unlocked(Unlocks.Pumpkins) > 0:
        return Entities.Pumpkin
    if num_unlocked(Unlocks.Trees) > 0:
        return Entities.Tree
    if num_unlocked(Unlocks.Carrots) > 0:
        return Entities.Carrot
    return Entities.Bush


def farm_with_companions():
    # Placeholder: the real version should build a full companion layout in
    # memory and then execute it in a single sweep.
    farm_grid(choose_midgame_crop())


def solve_snake(region):
    # Placeholder for the dinosaur/bone phase. The real implementation should
    # precompute a Hamiltonian-style sweep for the region and minimize turns.
    return False


def solve_maze(region):
    # Placeholder for the maze/gold phase. The real implementation should
    # measure the treasure, solve the hedge layout in memory, and only then
    # execute movement.
    return False


def drone_dispatch():
    # Placeholder for stripe-based worker assignment once Megafarm is online.
    # For now, only spawn helpers when the unlock exists and keep them on the
    # same safe fallback routine.
    if num_unlocked(Unlocks.Megafarm) <= 0:
        return

    handles = []

    while num_drones() < max_drones():
        handle = spawn_drone(drone_fallback_worker)
        if handle == None:
            return
        handles.append(handle)

    for handle in handles:
        wait_for(handle)


def drone_fallback_worker():
    farm_grid(choose_midgame_crop())


def current_phase():
    if num_unlocked(Unlocks.Plant) <= 0:
        return 0
    if (
        num_unlocked(Unlocks.Expand) <= 1
        or num_unlocked(Unlocks.Speed) <= 1
        or num_unlocked(Unlocks.Carrots) <= 0
        or num_unlocked(Unlocks.Trees) <= 0
        or num_unlocked(Unlocks.Watering) <= 0
        or get_world_size() <= 1
    ):
        return 1
    if (
        num_unlocked(Unlocks.Pumpkins) <= 0
        or num_unlocked(Unlocks.Sunflowers) <= 0
        or num_unlocked(Unlocks.Fertilizer) <= 0
        or get_world_size() < 6
    ):
        return 2
    if (
        num_unlocked(Unlocks.Polyculture) <= 0
        or num_unlocked(Unlocks.Cactus) <= 0
        or num_unlocked(Unlocks.Mazes) <= 0
        or get_world_size() < 12
    ):
        return 3
    if (
        num_unlocked(Unlocks.Dinosaurs) <= 0
        or num_unlocked(Unlocks.Megafarm) <= 0
        or get_world_size() < 20
    ):
        return 4
    if num_unlocked(Unlocks.Leaderboard) <= 0:
        return 5
    return 6


def phase0_bootstrap():
    # Real reset runs start with harvest but not plant, so this phase must stay
    # harvest-only until `Unlocks.Plant` is affordable.
    while num_unlocked(Unlocks.Plant) <= 0:
        if buy_bootstrap_unlock():
            continue

        if can_harvest():
            harvest()

        if get_world_size() > 1:
            move(North)


def phase1_basic_farming():
    if buy_phase1_unlock():
        return

    if num_unlocked(Unlocks.Expand) <= 1:
        farm_simple_strip(choose_simple_crop(), 24)
        return

    farm_grid(choose_simple_crop())


def phase2_adaptive_farming():
    buy_expands_until(6)
    buy_priority(PHASE_2_QUEUE)

    if num_unlocked(Unlocks.Carrots) > 0:
        farm_grid(Entities.Carrot)
    else:
        farm_grid(Entities.Bush)


def phase3_intermediate():
    buy_expands_until(12)
    buy_priority(PHASE_3_QUEUE)

    if num_unlocked(Unlocks.Polyculture) > 0:
        farm_with_companions()
    else:
        farm_grid(choose_midgame_crop())


def phase4_algorithm_crops():
    buy_expands_until(20)
    buy_priority(PHASE_4_QUEUE)

    if num_unlocked(Unlocks.Megafarm) > 0:
        drone_dispatch()
        return

    if num_unlocked(Unlocks.Mazes) > 0:
        if solve_maze(None):
            return

    if num_unlocked(Unlocks.Dinosaurs) > 0:
        if solve_snake(None):
            return

    if num_unlocked(Unlocks.Cactus) > 0:
        farm_grid(Entities.Cactus)
        return

    farm_grid(choose_midgame_crop())


def phase5_endgame_rush():
    if buy_priority(PHASE_5_QUEUE):
        return

    if num_unlocked(Unlocks.Mazes) > 0 and solve_maze(None):
        return

    if num_unlocked(Unlocks.Dinosaurs) > 0 and solve_snake(None):
        return

    if num_unlocked(Unlocks.Cactus) > 0:
        farm_grid(Entities.Cactus)
        return

    farm_grid(choose_midgame_crop())


def run_reset():
    while num_unlocked(Unlocks.Leaderboard) <= 0:
        phase = current_phase()
        quick_print("phase", phase, "size", get_world_size())

        if phase == 0:
            phase0_bootstrap()
        elif phase == 1:
            phase1_basic_farming()
        elif phase == 2:
            phase2_adaptive_farming()
        elif phase == 3:
            phase3_intermediate()
        elif phase == 4:
            phase4_algorithm_crops()
        else:
            phase5_endgame_rush()


run_reset()
