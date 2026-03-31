# Progression And Unlocks

This is the progression reference most relevant to `leader_reset.py`.

## Confirmed Dependency Order

This dependency chain matches the old root `README.md` and the current reset scaffold.

```text
speed
grass

expand: speed
plant: speed

carrots: plant

trees: carrots
watering: carrots

pumpkins: trees
sunflowers: watering
fertilizer: watering

polyculture: pumpkins
cactus: pumpkins
mazes: fertilizer

dinosaurs: cactus
megafarm: mazes

leaderboard: bones + gold endgame gate
```

## Reset Phase Map

These are the actual code gates used by `leader_reset.py`.

| Phase | Exit condition |
| --- | --- |
| 0 | `Unlocks.Plant` unlocked |
| 1 | `Carrots`, `Trees`, `Watering` unlocked and farm size `> 1` |
| 2 | `Pumpkins`, `Sunflowers`, `Fertilizer` unlocked and farm size `>= 6` |
| 3 | `Polyculture`, `Cactus`, `Mazes` unlocked and farm size `>= 12` |
| 4 | `Dinosaurs`, `Megafarm` unlocked and farm size `>= 20` |
| 5 | `Unlocks.Leaderboard` unlocked |

## Core Unlock Costs

Recent wiki `Unlocks_Data` values, grouped for route planning.

### Language And Utility Unlocks

| Unlock | Cost |
| --- | --- |
| `Loops` | `5 Hay` |
| `Plant` | `50 Hay` |
| `Senses` | `100 Hay` |
| `Operators` | `150 Hay`, `10 Wood` |
| `Variables` | `35 Carrot` |
| `Functions` | `40 Carrot` |
| `Lists` | `500 Carrot` |
| `Dictionaries` | `2500 Pumpkin` |
| `Costs` | `2500 Pumpkin` |
| `Timing` | `1000 Pumpkin` |
| `Utilities` | `1000 Pumpkin` |
| `Debug` | `50 Hay`, `50 Wood` |
| `Debug_2` | `500 Gold` |
| `Auto_Unlock` | `5000 Pumpkin` |
| `Simulation` | `5000 Gold` |

### Reset-Critical Progression Unlocks

| Unlock | Levels / costs |
| --- | --- |
| `Speed` | `20 Hay`; `20 Wood`; `50 Wood + 50 Carrot`; `500 Carrot`; `1000 Carrot` |
| `Grass` | `100 Hay`; `300 Hay`; `500 Wood`; `2500 Wood`; `12500 Wood`; `62500 Wood`; `312000 Wood`; `1560000 Wood`; `7810000 Wood`; `39100000 Wood` |
| `Expand` | `30 Hay`; `20 Wood`; `30 Wood + 20 Carrot`; `100 Wood + 50 Carrot`; `1000 Pumpkin`; `8000 Pumpkin`; `64000 Pumpkin`; `512000 Pumpkin`; `4100000 Pumpkin` |
| `Carrots` | `50 Wood`; `250 Wood`; `1250 Wood`; `6250 Wood`; `31200 Wood`; `156000 Wood`; `781000 Wood`; `3910000 Wood`; `19500000 Wood`; `97700000 Wood` |
| `Trees` | `50 Wood + 70 Carrot`; `300 Hay`; `1200 Hay`; `4800 Hay`; `19200 Hay`; `76800 Hay`; `307000 Hay`; `1230000 Hay`; `4920000 Hay`; `19700000 Hay` |
| `Watering` | `50 Wood`; `200 Wood`; `800 Wood`; `3200 Wood`; `12800 Wood`; `51200 Wood`; `205000 Wood`; `819000 Wood`; `3280000 Wood` |
| `Pumpkins` | `500 Wood + 200 Carrot`; `1000 Carrot`; `4000 Carrot`; `16000 Carrot`; `64000 Carrot`; `256000 Carrot`; `1020000 Carrot`; `4100000 Carrot`; `16400000 Carrot`; `65500000 Carrot` |
| `Sunflowers` | `500 Carrot` |
| `Fertilizer` | `500 Wood`; `1500 Wood`; `9000 Wood`; `54000 Wood` |
| `Polyculture` | `3000 Pumpkin`; `10000 Bone`; `50000 Bone`; `250000 Bone`; `1250000 Bone` |
| `Cactus` | `5000 Pumpkin`; `20000 Pumpkin`; `120000 Pumpkin`; `720000 Pumpkin`; `4320000 Pumpkin`; `25900000 Pumpkin` |
| `Mazes` | `1000 Weird_Substance`; `12000 Cactus`; `72000 Cactus`; `432000 Cactus`; `2590000 Cactus`; `15600000 Cactus` |
| `Dinosaurs` | `2000 Cactus`; `12000 Cactus`; `72000 Cactus`; `432000 Cactus`; `2590000 Cactus`; `15600000 Cactus` |
| `Megafarm` | `2000 Gold`; `8000 Gold`; `32000 Gold`; `128000 Gold`; `512000 Gold` |
| `Leaderboard` | `2000000 Bone`; `1000000 Gold` |

## Current Save Status

Confirmed from `save.json`.

| Unlock | Current save state |
| --- | --- |
| `Speed` | maxed to `5` |
| `Grass` | maxed to `10` |
| `Expand` | maxed to `9` |
| `Plant` | unlocked |
| `Carrots` | maxed to `10` |
| `Trees` | maxed to `10` |
| `Watering` | maxed to `9` |
| `Pumpkins` | maxed to `10` |
| `Sunflowers` | unlocked |
| `Fertilizer` | maxed to `4` |
| `Polyculture` | maxed to `5` |
| `Cactus` | maxed to `6` |
| `Mazes` | maxed to `6` |
| `Dinosaurs` | maxed to `6` |
| `Megafarm` | maxed to `5` |
| `Leaderboard` | unlocked |
| `Timing`, `Utilities`, `Costs`, `Auto_Unlock`, `Simulation` | unlocked |

## Route Notes For `leader_reset.py`

- The scaffold intentionally buys only the first `Speed` and first `Expand` before `Plant`.
- `Expand` is not just movement: it also clears the field, so buying it at the wrong time destroys farm state.
- The dominant endgame gate is not research order, but reaching `2,000,000 Bone` and `1,000,000 Gold`.
- `Polyculture`, `Cactus`, `Mazes`, `Dinosaurs`, and `Megafarm` are where the algorithmic work matters most. The current reset script still has placeholders there.

## Important Semantics Caveat

Wiki and stub wording around `num_unlocked()` are not perfectly consistent for upgradeable unlocks. In practice, this repo already uses `num_unlocked(Unlocks.X)` as the current level/count signal, so route logic should follow that convention and avoid hard-coding an alternate interpretation.

## Sources

- https://thefarmerwasreplaced.wiki.gg/wiki/Unlocks
- https://thefarmerwasreplaced.wiki.gg/wiki/Unlocks_Data
- local `leader_reset.py`
- original reset notes moved from the old root `README.md`
- local `save.json`
