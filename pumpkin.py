from __builtins__ import *
from utils import *


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
