from __builtins__ import *
from utils import *


def maintain_cactus():
    current = get_entity_type()

    if current == Entities.Cactus:
        if can_harvest():
            STATE["cactus_ready_count"] += 1
            STATE["cactus_sizes"][(get_pos_x(), get_pos_y())] = measure()
        return

    if current != None:
        harvest()

    plant_target(Entities.Cactus)


def empty_cactus_grid():
    size = get_world_size()
    grid = []
    y = 0

    while y < size:
        row = []
        x = 0

        while x < size:
            row.append(None)
            x += 1

        grid.append(row)
        y += 1

    return grid


def current_cactus_grid():
    grid = empty_cactus_grid()

    for loc in STATE["cactus_sizes"]:
        x, y = loc
        grid[y][x] = STATE["cactus_sizes"][loc]

    return grid


def target_cactus_grid(grid):
    counts = []
    value = 0

    while value < 10:
        counts.append(0)
        value += 1

    size = get_world_size()
    y = 0

    while y < size:
        x = 0

        while x < size:
            counts[grid[y][x]] += 1
            x += 1

        y += 1

    target = empty_cactus_grid()
    next_size = 0
    y = 0

    while y < size:
        x = 0

        while x < size:
            while counts[next_size] <= 0:
                next_size += 1

            target[y][x] = next_size
            counts[next_size] -= 1
            x += 1

        y += 1

    return target


def find_cactus_source(grid, target_x, target_y, target_size):
    size = get_world_size()
    best_x = None
    best_y = None
    best_distance = None
    y = target_y

    while y < size:
        x = 0
        if y == target_y:
            x = target_x

        while x < size:
            if grid[y][x] == target_size:
                distance = abs(x - target_x) + abs(y - target_y)
                if best_distance == None or distance < best_distance:
                    best_x = x
                    best_y = y
                    best_distance = distance
            x += 1

        y += 1

    return best_x, best_y


def swap_cactus_grid(grid, x, y, other_x, other_y):
    value = grid[y][x]
    grid[y][x] = grid[other_y][other_x]
    grid[other_y][other_x] = value


def move_cactus_horizontal(grid, x, y, target_x):
    while x < target_x:
        swap(East)
        swap_cactus_grid(grid, x, y, x + 1, y)
        move(East)
        x += 1

    while x > target_x:
        swap(West)
        swap_cactus_grid(grid, x, y, x - 1, y)
        move(West)
        x -= 1

    return x


def move_cactus_vertical(grid, x, y, target_y):
    while y < target_y:
        swap(North)
        swap_cactus_grid(grid, x, y, x, y + 1)
        move(North)
        y += 1

    while y > target_y:
        swap(South)
        swap_cactus_grid(grid, x, y, x, y - 1)
        move(South)
        y -= 1

    return y


def place_cactus(grid, target_x, target_y, source_x, source_y):
    x = source_x
    y = source_y

    goto(x, y)

    if y > target_y:
        x = move_cactus_horizontal(grid, x, y, target_x)
        move_cactus_vertical(grid, x, y, target_y)
        return

    x = move_cactus_horizontal(grid, x, y, target_x)
    move_cactus_vertical(grid, x, y, target_y)


def sort_cactus_world():
    grid = current_cactus_grid()
    target = target_cactus_grid(grid)
    size = get_world_size()
    y = 0

    while y < size:
        x = 0

        while x < size:
            if grid[y][x] != target[y][x]:
                source_x, source_y = find_cactus_source(grid, x, y, target[y][x])
                place_cactus(grid, x, y, source_x, source_y)
            x += 1

        y += 1
