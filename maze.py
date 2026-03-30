from __builtins__ import *
from utils import *


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
    goto(0, 0)

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


def next_maze_direction(visited, target_x, target_y):
    x = get_pos_x()
    y = get_pos_y()
    directions = ordered_maze_directions(x, y, target_x, target_y)
    index = 0

    while index < len(directions):
        direction = directions[index]
        if can_move(direction):
            next_x, next_y = maze_neighbor(x, y, direction)
            if (next_x, next_y) not in visited:
                return direction
        index += 1

    return None


def solve_current_maze():
    treasure = measure()
    if treasure == None:
        return False

    target_x, target_y = treasure
    visited = set()
    backtrack = []
    visited.add((get_pos_x(), get_pos_y()))

    while True:
        if get_pos_x() == target_x and get_pos_y() == target_y:
            return True

        direction = next_maze_direction(visited, target_x, target_y)
        if direction != None:
            move(direction)
            backtrack.append(maze_opposite(direction))
            visited.add((get_pos_x(), get_pos_y()))
            continue

        if len(backtrack) <= 0:
            return False

        move(backtrack.pop())


def run_maze_cycle():
    if not ensure_maze():
        return False
    if not solve_current_maze():
        return False
    if get_entity_type() != Entities.Treasure:
        return False
    if not can_harvest():
        return False

    harvest()
    return True
