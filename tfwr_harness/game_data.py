"""Shared game-ish data for the TFWR harness.

These tables are the current single source of truth for the harness builtin
shim. They intentionally cover only the enum-like names and costs needed by the
current plan phases. Future phases can refine these values as parity data
improves without spreading ad-hoc literals across the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass


class ValueNamespace:
    """Simple attribute namespace that exposes TFWR-like constant values."""

    def __init__(self, prefix: str, names: list[str]) -> None:
        self._prefix = prefix
        self._names = tuple(names)
        for name in names:
            setattr(self, name, f"{prefix}.{name}")

    def values(self) -> tuple[str, ...]:
        return tuple(getattr(self, name) for name in self._names)


@dataclass(slots=True, frozen=True)
class EntitySpec:
    """Static planting and growth metadata used by the current runtime."""

    allowed_grounds: frozenset[str]
    required_growth: float | None
    base_cost: dict[str, float]
    cost_unlock: str | None = None
    harvestable_when_mature: bool = True


DEFAULT_HAT = "Hats.Straw_Hat"

Items = ValueNamespace(
    "Items",
    [
        "Hay",
        "Wood",
        "Carrot",
        "Pumpkin",
        "Cactus",
        "Water",
        "Fertilizer",
        "Weird_Substance",
        "Power",
        "Gold",
        "Bone",
        "Piggy",
    ],
)

Entities = ValueNamespace(
    "Entities",
    [
        "Grass",
        "Bush",
        "Tree",
        "Carrot",
        "Pumpkin",
        "Dead_Pumpkin",
        "Sunflower",
        "Cactus",
        "Hedge",
        "Treasure",
        "Apple",
        "Dinosaur",
    ],
)

Grounds = ValueNamespace(
    "Grounds",
    [
        "Grassland",
        "Soil",
    ],
)

Unlocks = ValueNamespace(
    "Unlocks",
    [
        "Auto_Unlock",
        "Cactus",
        "Carrots",
        "Costs",
        "Debug",
        "Debug_2",
        "Dictionaries",
        "Dinosaurs",
        "Expand",
        "Fertilizer",
        "Functions",
        "Grass",
        "Hats",
        "Import",
        "Leaderboard",
        "Lists",
        "Loops",
        "Mazes",
        "Megafarm",
        "Operators",
        "Plant",
        "Polyculture",
        "Pumpkins",
        "Senses",
        "Simulation",
        "Speed",
        "Sunflowers",
        "The_Farmers_Remains",
        "Timing",
        "Top_Hat",
        "Trees",
        "Utilities",
        "Variables",
        "Watering",
    ],
)

Hats = ValueNamespace(
    "Hats",
    [
        "Straw_Hat",
        "Sunflower_Hat",
        "Golden_Sunflower_Hat",
        "Carrot_Hat",
        "Pumpkin_Hat",
        "Cactus_Hat",
        "Tree_Hat",
        "Dinosaur_Hat",
        "Top_Hat",
        "The_Farmers_Remains",
    ],
)

Leaderboards = ValueNamespace(
    "Leaderboards",
    [
        "Fastest_Reset",
        "Hay",
        "Wood",
        "Carrots",
        "Pumpkins",
        "Sunflowers",
        "Cactus",
        "Maze",
        "Dinosaur",
    ],
)

North = "North"
East = "East"
South = "South"
West = "West"

DIRECTION_DELTAS = {
    North: (0, 1),
    East: (1, 0),
    South: (0, -1),
    West: (-1, 0),
}

EXPAND_WORLD_SIZES = {
    0: 1,
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 8,
    7: 12,
    8: 16,
    9: 20,
}

ENTITY_SPECS = {
    Entities.Grass: EntitySpec(
        allowed_grounds=frozenset({Grounds.Grassland, Grounds.Soil}),
        required_growth=0.5,
        base_cost={},
        harvestable_when_mature=True,
    ),
    Entities.Bush: EntitySpec(
        allowed_grounds=frozenset({Grounds.Grassland, Grounds.Soil}),
        required_growth=4.0,
        base_cost={},
        harvestable_when_mature=True,
    ),
    Entities.Tree: EntitySpec(
        allowed_grounds=frozenset({Grounds.Grassland, Grounds.Soil}),
        required_growth=7.0,
        base_cost={Items.Hay: 1.0},
        harvestable_when_mature=True,
    ),
    Entities.Carrot: EntitySpec(
        allowed_grounds=frozenset({Grounds.Soil}),
        required_growth=6.0,
        base_cost={Items.Hay: 1.0, Items.Wood: 1.0},
        cost_unlock=Unlocks.Carrots,
        harvestable_when_mature=True,
    ),
    Entities.Pumpkin: EntitySpec(
        allowed_grounds=frozenset({Grounds.Soil}),
        required_growth=2.0,
        base_cost={Items.Carrot: 1.0},
        cost_unlock=Unlocks.Pumpkins,
        harvestable_when_mature=True,
    ),
    Entities.Dead_Pumpkin: EntitySpec(
        allowed_grounds=frozenset({Grounds.Soil}),
        required_growth=None,
        base_cost={},
        cost_unlock=Unlocks.Pumpkins,
        harvestable_when_mature=False,
    ),
    Entities.Sunflower: EntitySpec(
        allowed_grounds=frozenset({Grounds.Soil}),
        required_growth=7.0,
        base_cost={Items.Carrot: 1.0},
        cost_unlock=Unlocks.Sunflowers,
        harvestable_when_mature=True,
    ),
    Entities.Cactus: EntitySpec(
        allowed_grounds=frozenset({Grounds.Soil}),
        required_growth=1.0,
        base_cost={Items.Pumpkin: 2.0},
        cost_unlock=Unlocks.Cactus,
        harvestable_when_mature=True,
    ),
    Entities.Hedge: EntitySpec(
        allowed_grounds=frozenset({Grounds.Grassland, Grounds.Soil}),
        required_growth=None,
        base_cost={},
        cost_unlock=Unlocks.Mazes,
        harvestable_when_mature=False,
    ),
    Entities.Treasure: EntitySpec(
        allowed_grounds=frozenset({Grounds.Grassland, Grounds.Soil}),
        required_growth=None,
        base_cost={},
        cost_unlock=Unlocks.Mazes,
        harvestable_when_mature=True,
    ),
    Entities.Apple: EntitySpec(
        allowed_grounds=frozenset({Grounds.Grassland, Grounds.Soil}),
        required_growth=None,
        base_cost={Items.Cactus: 2.0},
        cost_unlock=Unlocks.Dinosaurs,
        harvestable_when_mature=False,
    ),
    Entities.Dinosaur: EntitySpec(
        allowed_grounds=frozenset({Grounds.Grassland, Grounds.Soil}),
        required_growth=0.2,
        base_cost={},
        cost_unlock=Unlocks.Dinosaurs,
        harvestable_when_mature=True,
    ),
}

UNLOCK_COSTS = {
    Unlocks.Loops: [{Items.Hay: 5.0}],
    Unlocks.Plant: [{Items.Hay: 50.0}],
    Unlocks.Senses: [{Items.Hay: 100.0}],
    Unlocks.Operators: [{Items.Hay: 150.0, Items.Wood: 10.0}],
    Unlocks.Variables: [{Items.Carrot: 35.0}],
    Unlocks.Functions: [{Items.Carrot: 40.0}],
    Unlocks.Lists: [{Items.Carrot: 500.0}],
    Unlocks.Dictionaries: [{Items.Pumpkin: 2500.0}],
    Unlocks.Costs: [{Items.Pumpkin: 2500.0}],
    Unlocks.Timing: [{Items.Pumpkin: 1000.0}],
    Unlocks.Utilities: [{Items.Pumpkin: 1000.0}],
    Unlocks.Debug: [{Items.Hay: 50.0, Items.Wood: 50.0}],
    Unlocks.Debug_2: [{Items.Gold: 500.0}],
    Unlocks.Auto_Unlock: [{Items.Pumpkin: 5000.0}],
    Unlocks.Simulation: [{Items.Gold: 5000.0}],
    Unlocks.Speed: [
        {Items.Hay: 20.0},
        {Items.Wood: 20.0},
        {Items.Wood: 50.0, Items.Carrot: 50.0},
        {Items.Carrot: 500.0},
        {Items.Carrot: 1000.0},
    ],
    Unlocks.Grass: [
        {Items.Hay: 100.0},
        {Items.Hay: 300.0},
        {Items.Wood: 500.0},
        {Items.Wood: 2500.0},
        {Items.Wood: 12500.0},
        {Items.Wood: 62500.0},
        {Items.Wood: 312000.0},
        {Items.Wood: 1560000.0},
        {Items.Wood: 7810000.0},
        {Items.Wood: 39100000.0},
    ],
    Unlocks.Expand: [
        {Items.Hay: 30.0},
        {Items.Wood: 20.0},
        {Items.Wood: 30.0, Items.Carrot: 20.0},
        {Items.Wood: 100.0, Items.Carrot: 50.0},
        {Items.Pumpkin: 1000.0},
        {Items.Pumpkin: 8000.0},
        {Items.Pumpkin: 64000.0},
        {Items.Pumpkin: 512000.0},
        {Items.Pumpkin: 4100000.0},
    ],
    Unlocks.Carrots: [
        {Items.Wood: 50.0},
        {Items.Wood: 250.0},
        {Items.Wood: 1250.0},
        {Items.Wood: 6250.0},
        {Items.Wood: 31200.0},
        {Items.Wood: 156000.0},
        {Items.Wood: 781000.0},
        {Items.Wood: 3910000.0},
        {Items.Wood: 19500000.0},
        {Items.Wood: 97700000.0},
    ],
    Unlocks.Trees: [
        {Items.Wood: 50.0, Items.Carrot: 70.0},
        {Items.Hay: 300.0},
        {Items.Hay: 1200.0},
        {Items.Hay: 4800.0},
        {Items.Hay: 19200.0},
        {Items.Hay: 76800.0},
        {Items.Hay: 307000.0},
        {Items.Hay: 1230000.0},
        {Items.Hay: 4920000.0},
        {Items.Hay: 19700000.0},
    ],
    Unlocks.Watering: [
        {Items.Wood: 50.0},
        {Items.Wood: 200.0},
        {Items.Wood: 800.0},
        {Items.Wood: 3200.0},
        {Items.Wood: 12800.0},
        {Items.Wood: 51200.0},
        {Items.Wood: 205000.0},
        {Items.Wood: 819000.0},
        {Items.Wood: 3280000.0},
    ],
    Unlocks.Pumpkins: [
        {Items.Wood: 500.0, Items.Carrot: 200.0},
        {Items.Carrot: 1000.0},
        {Items.Carrot: 4000.0},
        {Items.Carrot: 16000.0},
        {Items.Carrot: 64000.0},
        {Items.Carrot: 256000.0},
        {Items.Carrot: 1020000.0},
        {Items.Carrot: 4100000.0},
        {Items.Carrot: 16400000.0},
        {Items.Carrot: 65500000.0},
    ],
    Unlocks.Sunflowers: [{Items.Carrot: 500.0}],
    Unlocks.Fertilizer: [
        {Items.Wood: 500.0},
        {Items.Wood: 1500.0},
        {Items.Wood: 9000.0},
        {Items.Wood: 54000.0},
    ],
    Unlocks.Polyculture: [
        {Items.Pumpkin: 3000.0},
        {Items.Bone: 10000.0},
        {Items.Bone: 50000.0},
        {Items.Bone: 250000.0},
        {Items.Bone: 1250000.0},
    ],
    Unlocks.Cactus: [
        {Items.Pumpkin: 5000.0},
        {Items.Pumpkin: 20000.0},
        {Items.Pumpkin: 120000.0},
        {Items.Pumpkin: 720000.0},
        {Items.Pumpkin: 4320000.0},
        {Items.Pumpkin: 25900000.0},
    ],
    Unlocks.Mazes: [
        {Items.Weird_Substance: 1000.0},
        {Items.Cactus: 12000.0},
        {Items.Cactus: 72000.0},
        {Items.Cactus: 432000.0},
        {Items.Cactus: 2590000.0},
        {Items.Cactus: 15600000.0},
    ],
    Unlocks.Dinosaurs: [
        {Items.Cactus: 2000.0},
        {Items.Cactus: 12000.0},
        {Items.Cactus: 72000.0},
        {Items.Cactus: 432000.0},
        {Items.Cactus: 2590000.0},
        {Items.Cactus: 15600000.0},
    ],
    Unlocks.Megafarm: [
        {Items.Gold: 2000.0},
        {Items.Gold: 8000.0},
        {Items.Gold: 32000.0},
        {Items.Gold: 128000.0},
        {Items.Gold: 512000.0},
    ],
    Unlocks.Leaderboard: [
        {Items.Bone: 2000000.0},
        {Items.Gold: 1000000.0},
    ],
}

THING_UNLOCK_REQUIREMENTS = {
    Entities.Bush: Unlocks.Plant,
    Entities.Tree: Unlocks.Trees,
    Entities.Carrot: Unlocks.Carrots,
    Entities.Pumpkin: Unlocks.Pumpkins,
    Entities.Dead_Pumpkin: Unlocks.Pumpkins,
    Entities.Sunflower: Unlocks.Sunflowers,
    Entities.Cactus: Unlocks.Cactus,
    Entities.Hedge: Unlocks.Mazes,
    Entities.Treasure: Unlocks.Mazes,
    Entities.Apple: Unlocks.Dinosaurs,
    Entities.Dinosaur: Unlocks.Dinosaurs,
    Grounds.Soil: Unlocks.Carrots,
    Items.Water: Unlocks.Watering,
    Items.Fertilizer: Unlocks.Fertilizer,
    Items.Weird_Substance: Unlocks.Mazes,
    Hats.Sunflower_Hat: Unlocks.Hats,
    Hats.Golden_Sunflower_Hat: Unlocks.Hats,
    Hats.Carrot_Hat: Unlocks.Hats,
    Hats.Pumpkin_Hat: Unlocks.Hats,
    Hats.Cactus_Hat: Unlocks.Hats,
    Hats.Tree_Hat: Unlocks.Hats,
    Hats.Dinosaur_Hat: Unlocks.The_Farmers_Remains,
    Hats.Top_Hat: Unlocks.Top_Hat,
    Hats.The_Farmers_Remains: Unlocks.The_Farmers_Remains,
}

ALWAYS_UNLOCKED_THINGS = {
    Grounds.Grassland,
    Entities.Grass,
    Hats.Straw_Hat,
}

MOVEMENT_BLOCKING_ENTITIES = {
    Entities.Hedge,
}
