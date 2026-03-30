from __builtins__ import *
from utils import *
from sunflower import *
from pumpkin import *
from cactus import *


def visit_tile():
    if STATE["world_mode"] == SUNFLOWER_WORLD:
        maintain_sunflower()
        return

    if STATE["world_mode"] == PUMPKIN_WORLD:
        maintain_pumpkin()
        return

    maintain_cactus()


def queue_world(target_world):
    if needs_sunflower_phase():
        switch_to_sunflower_world(target_world)
        return

    if target_world == PUMPKIN_WORLD:
        enter_pumpkin_world()
        return

    enter_normal_world()


def finish_sunflower_phase():
    if STATE["next_world_mode"] == PUMPKIN_WORLD:
        enter_pumpkin_world()
        return

    enter_normal_world()


def finish_normal_sweep():
    if STATE["world_mode"] != NORMAL_WORLD:
        return

    STATE["normal_sweeps_remaining"] -= 1
    if STATE["normal_sweeps_remaining"] <= 0:
        queue_world(PUMPKIN_WORLD)


def main():
    queue_world(NORMAL_WORLD)

    while True:
        equip_phase_hat()
        reset_cycle_state()
        sweep_world(visit_tile)

        if STATE["world_mode"] == SUNFLOWER_WORLD:
            if harvest_best_sunflower():
                quick_print("sunflower", "harvest", STATE["sunflower_max_petals"])
                finish_sunflower_phase()
            else:
                quick_print(
                    "sunflower",
                    STATE["sunflower_count"],
                    "/",
                    sunflower_area(),
                    STATE["sunflower_max_petals"],
                )
            continue

        if STATE["world_mode"] == PUMPKIN_WORLD:
            if harvest_mega_pumpkin():
                quick_print("pumpkin", "harvest", pumpkin_area())
                queue_world(NORMAL_WORLD)
            else:
                quick_print(
                    "pumpkin",
                    pumpkin_phase_name(),
                    STATE["pumpkin_ready_count"],
                    "/",
                    pumpkin_area(),
                    "repairs",
                    STATE["pumpkin_dead_repairs"],
                )
                if not STATE["pumpkin_use_fertilizer"]:
                    STATE["pumpkin_use_fertilizer"] = True
            continue

        if STATE["cactus_ready_count"] < cactus_area():
            quick_print("cactus", "grow", STATE["cactus_ready_count"], "/", cactus_area())
            continue

        sort_cactus_world()
        goto(0, 0)

        if get_entity_type() == Entities.Cactus and can_harvest():
            harvest()
            quick_print("cactus", "harvest", cactus_area())
            queue_world(PUMPKIN_WORLD)
        else:
            quick_print("cactus", "sort", STATE["cactus_ready_count"], "/", cactus_area())


main()
