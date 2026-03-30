# Leaderboards

Call `leaderboard_run(leaderboard, filename, speedup)` to start a leaderboard simulation with fixed starting conditions.

Important run rules:

- A leaderboard run only succeeds if its success condition is `True` when the simulation ends.
- The simulation does not end automatically when the goal is reached.
- Your program must terminate on its own after reaching the goal.
- Runs are averaged over at least 2 hours of simulated time to reduce variance.

## Authoritative Categories

| Category | Leaderboard Name | Success Condition | Notes |
| --- | --- | --- | --- |
| Fastest Reset | `Leaderboards.Fastest_Reset` | `num_unlocked(Unlocks.Leaderboard) > 0` | Unlock `Unlocks.Leaderboard` as fast as possible. |
| Maze | `Leaderboards.Maze` | `num_items(Items.Gold) >= 9863168` | Start with everything unlocked and farm gold. |
| Dinosaur | `Leaderboards.Dinosaur` | `num_items(Items.llBone) >= 33488928` | Start with everything unlocked and farm bones. |
| Cactus | `Leaderboards.Cactus` | `num_items(Items.Cactus) >= 33554432` | Farm cactus as fast as possible. |
| Sunflowers | `Leaderboards.Sunflowers` | `num_items(Items.Power) >= 100000` | Farm power. This uses `Items.Power`, not `Items.Sunflower`. |
| Pumpkins | `Leaderboards.Pumpkins` | `num_items(Items.Pumpkin) >= 200000000` | Farm pumpkins as fast as possible. |
| Wood | `Leaderboards.Wood` | `num_items(Items.Wood) >= 10000000000` | Farm wood as fast as possible. |
| Carrots | `Leaderboards.Carrots` | `num_items(Items.Carrot) >= 2000000000` | Farm carrots as fast as possible. |
| Hay | `Leaderboards.Hay` | `num_items(Items.Hay) >= 2000000000` | Farm hay as fast as possible. |

## Notes

- The target `filename` should point to a script that exits once the success condition is met.
- Reaching the target without terminating the program does not finish the run.
- This file only includes conditions confirmed from the authoritative leaderboard documentation provided for this save.
