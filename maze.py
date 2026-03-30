from __builtins__ import *
from utils import *

MAZE_DRONE_DIRECTION = None
MAZE_DRONE_TARGET = None
MAZE_DRONE_VISITED = None


def maze_substance_cost():
    return get_world_size() * 2 ** (num_unlocked(Unlocks.Mazes) - 1)


def needs_maze_phase():
    return (
        num_unlocked(Unlocks.Mazes) > 0
        and num_items(Items.Weird_Substance) >= maze_substance_cost()
    )


def is_active_maze():
    current = get_entity_type()

    if current == Entities.Hedge or current == Entities.Treasure:
        return True

    return current == None and measure() != None


def ensure_maze():
    if is_active_maze():
        return True

    current = get_entity_type()
    if current != Entities.Bush:
        if current != None:
            harvest()
        plant_target(Entities.Bush)

    return use_item(Items.Weird_Substance, maze_substance_cost())


def maze_opposite(direction):
    if direction == North:
        return South
    if direction == South:
        return North
    if direction == East:
        return West
    return East


def maze_neighbor(x, y, direction):
    if direction == North:
        return x, y + 1
    if direction == South:
        return x, y - 1
    if direction == East:
        return x + 1, y
    return x - 1, y


def append_direction(directions, direction):
    if direction not in directions:
        directions.append(direction)


def ordered_maze_directions(x, y, target_x, target_y):
    directions = []

    if target_x > x:
        append_direction(directions, East)
    elif target_x < x:
        append_direction(directions, West)

    if target_y > y:
        append_direction(directions, North)
    elif target_y < y:
        append_direction(directions, South)

    append_direction(directions, North)
    append_direction(directions, East)
    append_direction(directions, South)
    append_direction(directions, West)
    return directions


def maze_available_directions(visited, target_x, target_y):
    directions = []
    x = get_pos_x()
    y = get_pos_y()
    ordered = ordered_maze_directions(x, y, target_x, target_y)
    index = 0

    while index < len(ordered):
        direction = ordered[index]
        if can_move(direction) and direction not in directions:
            next_x, next_y = maze_neighbor(x, y, direction)
            if (next_x, next_y) not in visited:
                directions.append(direction)
        index += 1

    return directions


def copy_visited(visited):
    copied = set()

    for loc in visited:
        copied.add(loc)

    return copied


def maze_branch_worker():
    target_x, target_y = MAZE_DRONE_TARGET
    return solve_maze_branch(MAZE_DRONE_DIRECTION, target_x, target_y, MAZE_DRONE_VISITED)


def solve_maze_branch(direction, target_x, target_y, visited):
    if not is_active_maze():
        return False

    x = get_pos_x()
    y = get_pos_y()
    next_x, next_y = maze_neighbor(x, y, direction)

    if (next_x, next_y) in visited:
        return False
    if not move(direction):
        return False
    if not is_active_maze():
        return False

    visited.add((get_pos_x(), get_pos_y()))
    if solve_maze_position(target_x, target_y, visited):
        return True

    move(maze_opposite(direction))
    return False


def solve_maze_position(target_x, target_y, visited):
    global MAZE_DRONE_DIRECTION
    global MAZE_DRONE_TARGET
    global MAZE_DRONE_VISITED

    if not is_active_maze():
        return False

    if get_pos_x() == target_x and get_pos_y() == target_y:
        if get_entity_type() != Entities.Treasure:
            return False
        if not can_harvest():
            return False

        harvest()
        return True

    directions = maze_available_directions(visited, target_x, target_y)
    if len(directions) <= 0:
        return False

    handles = []
    fallback_directions = []
    index = 1

    while index < len(directions):
        MAZE_DRONE_DIRECTION = directions[index]
        MAZE_DRONE_TARGET = (target_x, target_y)
        MAZE_DRONE_VISITED = copy_visited(visited)

        handle = spawn_drone(maze_branch_worker)
        if handle == None:
            fallback_directions.append(directions[index])
        else:
            handles.append(handle)

        index += 1

    solved = solve_maze_branch(directions[0], target_x, target_y, visited)

    index = 0
    while index < len(handles):
        if wait_for(handles[index]):
            solved = True
        index += 1

    if solved:
        return True

    index = 0
    while index < len(fallback_directions):
        if solve_maze_branch(fallback_directions[index], target_x, target_y, visited):
            return True
        index += 1

    return False


def solve_current_maze():
    treasure = measure()
    if treasure == None:
        return False

    target_x, target_y = treasure
    visited = set()
    visited.add((get_pos_x(), get_pos_y()))
    return solve_maze_position(target_x, target_y, visited)


def run_maze_cycle():
    if not ensure_maze():
        return False
    return solve_current_maze()


def maze_main():
    enter_maze_world(MAZE_WORLD)

    while True:
        equip_phase_hat()

        if run_maze_cycle():
            quick_print("maze", "harvest")
        else:
            quick_print("maze", "skip")


if should_auto_run():
    maze_main()
