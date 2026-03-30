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

    if STATE["sunflower_max_petals"] == None or petals > STATE["sunflower_max_petals"]:
        STATE["sunflower_max_petals"] = petals
        STATE["sunflower_ready_target"] = (get_pos_x(), get_pos_y())
        return

    if petals == STATE["sunflower_max_petals"] and STATE["sunflower_ready_target"] == None:
        STATE["sunflower_ready_target"] = (get_pos_x(), get_pos_y())


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


def harvest_best_sunflower():
    if STATE["sunflower_count"] != sunflower_area():
        return False
    if STATE["sunflower_ready_target"] == None:
        return False

    x, y = STATE["sunflower_ready_target"]
    goto(x, y)

    if get_entity_type() != Entities.Sunflower:
        return False
    if measure() != STATE["sunflower_max_petals"]:
        return False

    harvest()
    return True
