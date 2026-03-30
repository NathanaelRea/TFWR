from __builtins__ import *
from utils import *


def sunflower_rows():
    return get_world_size()


def sunflower_area():
    return sunflower_rows() * get_world_size()


def is_sunflower_tile(x, y):
    return y < sunflower_rows()


def power_threshold():
    return sunflower_area() * 2


def needs_sunflower_phase():
    return num_items(Items.Power) < power_threshold()


def note_sunflower():
    petals = measure()
    STATE["sunflower_count"] += 1
    if not can_harvest():
        return

    STATE["sunflower_ready_count"] += 1
    if STATE["sunflower_max_petals"] == None or petals > STATE["sunflower_max_petals"]:
        STATE["sunflower_max_petals"] = petals

    if petals not in STATE["sunflower_targets"]:
        STATE["sunflower_targets"][petals] = []

    STATE["sunflower_targets"][petals].append((get_pos_x(), get_pos_y()))


def maintain_sunflower():
    current = get_entity_type()
    x = get_pos_x()
    y = get_pos_y()

    if not is_sunflower_tile(x, y):
        return

    if current == Entities.Sunflower:
        note_sunflower()
        return

    if current != None and current != Entities.Dead_Pumpkin:
        harvest()

    plant_target(Entities.Sunflower)
    note_sunflower()


def harvest_ordered_sunflowers():
    if STATE["sunflower_count"] != sunflower_area():
        return 0
    if STATE["sunflower_ready_count"] != sunflower_area():
        return 0
    if STATE["sunflower_max_petals"] == None:
        return 0

    petals = STATE["sunflower_max_petals"]
    harvested = 0

    while petals >= 0:
        if petals in STATE["sunflower_targets"]:
            positions = STATE["sunflower_targets"][petals]
            index = 0

            while index < len(positions):
                x, y = positions[index]
                goto(x, y)

                if get_entity_type() == Entities.Sunflower and can_harvest():
                    if measure() == petals:
                        harvest()
                        harvested += 1

                index += 1

        petals -= 1

    return harvested
