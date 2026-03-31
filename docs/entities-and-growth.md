# Entities, Items, And Growth

This file collects the mechanics that most affect routing and farming efficiency.

## Growth Time Distribution

The recent `Plant_growth` page is the best numeric source for current growth timing.

| Entity | Min sec | Mean sec | Max sec |
| --- | ---: | ---: | ---: |
| Grass | 0.5 | 0.5 | 0.5 |
| Bush | 3.2 | 4.0 | 4.8 |
| Carrot | 4.8 | 6.0 | 7.2 |
| Tree | 5.6 | 7.0 | 8.4 |
| Pumpkin | 0.2 | 2.0 | 3.8 |
| Cactus | 1.0 | 1.0 | 1.0 |
| Sunflower | 5.6 | 7.0 | 8.4 |
| Dinosaur | 0.18 | 0.2 | 0.22 |

## Entity Summary

| Entity | Ground | Key mechanic |
| --- | --- | --- |
| `Grass` | `Grassland` grows automatically; can also exist on soil/grassland | harvested for `Hay` |
| `Bush` | grassland or soil | basic wood source |
| `Tree` | grassland or soil | more wood than bushes; grows slower when adjacent trees also grow |
| `Carrot` | soil | standard planted crop |
| `Pumpkin` | soil | adjacent mature pumpkins combine; harvest yield scales with pumpkin group size cubed |
| `Dead_Pumpkin` | soil | about 1 in 5 pumpkins die; `can_harvest()` stays `False` |
| `Sunflower` | soil | power crop with petal ranking rule |
| `Cactus` | soil | sorted-order harvest puzzle; `measure()` gives size |
| `Hedge` | maze tile | blocks movement |
| `Treasure` | maze target | harvest for maze gold |
| `Apple` | random target in dinosaur mode | `measure()` gives next apple position |
| `Dinosaur` | grassland or soil | bone farming through dinosaur hat/tail system |

## Item Summary

| Item | Use |
| --- | --- |
| `Hay` | grass resource and early unlock currency |
| `Wood` | bush/tree resource and major early-mid unlock currency |
| `Carrot` | carrot harvest; pumpkin and sunflower economy |
| `Pumpkin` | pumpkin harvest; cactus and fertilizer economy |
| `Cactus` | cactus harvest; dinosaur and maze upgrade economy |
| `Weird_Substance` | maze creation and related interactions |
| `Gold` | maze output; megafarm and leaderboard gate |
| `Bone` | dinosaur output; polyculture upgrades and leaderboard gate |
| `Water` | watering to accelerate growth |
| `Fertilizer` | instant growth reduction of 2 base seconds |
| `Power` | automatic speed doubling while available |

## Planting Cost Notes

Planting cost data is version-sensitive.

- Current workspace code should prefer `get_cost(Entities.X)` at runtime.
- The wiki still contains both current-style entity costs and older seed-cost pages.
- Useful confirmed examples:
  - `Sunflower` planting cost is `1 Carrot`.
  - current `Entity_Planting_Costs` page shows late-game examples such as `Carrot = 512 Hay + 512 Wood`, `Pumpkin = 512 Carrot`, `Cactus = 64 Pumpkin`, `Apple = 64 Cactus`.

For reset routing, avoid hard-coding plant costs unless they are measured in the target run.

## Watering

From the current wiki page:

- Water level is between `0` and `1`.
- Growth speed multiplier is `1 + water_level * 4`.
- So `0.25` water gives `2x`, `0.5` gives `3x`, `0.75` gives `4x`, and `1.0` gives `5x`.
- Water evaporation triggers every `0.8` to `1.2` seconds and removes `1%` of current water.
- Higher water levels are more expensive to maintain because evaporation is proportional to current water.

Practical route impact:

- Watering becomes attractive when the farm is large enough that waiting dominates.
- Re-watering mature plants is usually wasted action cost.
- Because evaporation is multiplicative, topping everything to `1.0` can be overkill outside dedicated high-throughput loops.

## Fertilizer

Confirmed from the wiki and local stubs:

- `use_item(Items.Fertilizer)` reduces remaining maturity by `2` base seconds.
- The current water multiplier applies to the fertilizer tick.
- After fertilizer is used, water on that tile becomes `0`.

Example from the wiki:

- A 7 second tree at water `0.5` grows at `3x`.
- One fertilizer use advances `2 * 3 = 6` seconds of base growth.
- The remaining `1` second then continues on dry ground unless re-watered.

## Polyculture

Current useful facts:

- `Grass`, `Bush`, `Tree`, and `Carrot` can receive a companion bonus.
- `get_companion()` reveals the wanted companion plant and its target tile.
- Companion type is one of `Grass`, `Bush`, `Tree`, or `Carrot`, but never the plant's own type.
- The companion position is within 3 moves of the plant, excluding the plant's own tile.
- The wiki says yield is `10x` at unlock level 1 and doubles on later upgrades.
- The current local stub returns a tuple form: `(entity, (x, y))`, not the older list form shown by some wiki pages.

Practical route impact:

- For cactus/maze/dino endgame, polyculture is mostly a supporting economy multiplier.
- If you use it, compute companion placements in memory first. Do not repeatedly probe and reshuffle tiles one by one on-field.

## Pumpkins

Useful confirmed behavior:

- Pumpkins grow on soil.
- They merge with neighboring mature pumpkins.
- Harvest output scales with mega-pumpkin size cubed.
- About `1 in 5` die and become `Dead_Pumpkin`.
- `Dead_Pumpkin` never passes `can_harvest()`.

Practical route impact:

- Always clear dead pumpkins before assuming a tile is productive.
- The cubic reward means contiguous mature groups are worth preserving.

## Cactus

Current high-signal rules:

- Cactus size is measurable with `measure()`.
- Cacti come in 10 sizes.
- Harvesting checks sorted order and rewards `n^2` cactus when `n` cacti are harvested in valid sorted relation.
- The local stub describes recursive adjacent sorted harvests.
- Older/current wiki pages phrase it slightly differently, but both agree that sorted arrangement is the core mechanic.

Practical route impact:

- Measure the whole field once.
- Compute the target arrangement in memory.
- Execute the swap plan with minimal movement.
- Avoid bubble-sorting on the field or repeatedly re-measuring the same tiles.

## Mazes

Recent wiki page summary:

- Use `Items.Weird_Substance` on a bush to grow a hedge maze.
- Without maze upgrades, using `n` substance creates an `n x n` maze.
- Each maze upgrade doubles treasure payout and also doubles the substance needed.
- Full-field maze recipe:
  - `plant(Entities.Bush)`
  - `n_substance = get_world_size() * 2 ** (num_unlocked(Unlocks.Mazes) - 1)`
  - `use_item(Items.Weird_Substance, n_substance)`
- Treasure gold equals maze area before upgrade multiplier.
- `get_entity_type()` is `Entities.Treasure` only on the treasure tile.
- `measure()` on treasure returns the next treasure position if the maze is reused.
- Reusing mazes can create loops and does not increase total gold efficiency relative to fresh mazes; it is mainly an extra challenge.
- A single maze can be solved at most `300` times total.

Practical route impact:

- For a leaderboard reset route, a fresh maze is simpler than maze reuse.
- A `1x1` maze is trivial but low yield.
- Wall-following works on loopless mazes and keeps state small.

## Dinosaurs

Recent wiki page summary:

- Dinosaur farming uses `change_hat(Hats.Dinosaur_Hat)`.
- Apples are bought and placed automatically if resources allow.
- Moving away from an apple grows the tail by one tile and attempts to place a new apple.
- Tail tiles block movement except the final segment vacates during the move.
- If the whole farm is filled, movement fails and the snake is effectively maxed out.
- `measure()` on an apple returns the next apple position.
- Unequipping the dinosaur hat harvests the tail for `tail_length ** 2` bones.
- Dinosaur hat starts with `move()` costing `400` ticks, then each apple reduces move cost by `3%`, rounded down.

Practical route impact:

- This is a planning problem, not a reactive one.
- Reset routes should aim for deterministic sweeps or Hamiltonian-style fills, especially once world size is known.

## Source Conflicts Worth Remembering

- `Sunflower` average growth is `5` in some older docs and `7.0` mean in the newer `Plant_growth` page.
- Some pages still describe seed items like `Items.Carrot_Seed` or `Items.Water_Tank`; the current save and local stub use direct entity/item names like `Entities.Carrot` and `Items.Water`.
- If a route depends on an exact plant cost or multiplier, prefer `get_cost()` or a direct in-game probe instead of trusting an older snippet.

## Sources

- https://thefarmerwasreplaced.wiki.gg/wiki/Plant_growth
- https://thefarmerwasreplaced.wiki.gg/wiki/Entities
- https://thefarmerwasreplaced.wiki.gg/wiki/Items
- https://thefarmerwasreplaced.wiki.gg/wiki/Watering
- https://thefarmerwasreplaced.wiki.gg/wiki/Fertilizer
- https://thefarmerwasreplaced.wiki.gg/wiki/Polyculture
- https://thefarmerwasreplaced.wiki.gg/wiki/Mazes
- https://thefarmerwasreplaced.wiki.gg/wiki/Dinosaurs
- https://thefarmerwasreplaced.wiki.gg/wiki/Entity_Planting_Costs
- local `__builtins__.py`

