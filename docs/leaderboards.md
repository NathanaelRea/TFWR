# Leaderboards

This file replaces the old root `leaderboard.md` with current workspace-oriented notes.

## Run Semantics

Confirmed by the local stub and the wiki leaderboard description:

- start runs with `leaderboard_run(leaderboard, filename, speedup)`,
- the program must terminate on its own,
- the run only counts if the success condition is true when execution ends,
- runs are averaged over at least 2 hours of simulated time to reduce variance.

## Current Categories In The Local Stub

Use these target values as the current workspace reference.

| Category | Enum | Target |
| --- | --- | --- |
| Fastest Reset | `Leaderboards.Fastest_Reset` | unlock `Unlocks.Leaderboard` |
| Cactus | `Leaderboards.Cactus` | `33,554,432` cactus |
| Cactus Single | `Leaderboards.Cactus_Single` | `131,072` cactus on single drone `8x8` |
| Carrots | `Leaderboards.Carrots` | `2,000,000,000` carrots |
| Carrots Single | `Leaderboards.Carrots_Single` | `100,000,000` carrots on single drone `8x8` |
| Dinosaur | `Leaderboards.Dinosaur` | `33,488,928` bones |
| Hay | `Leaderboards.Hay` | `2,000,000` hay |
| Hay Single | `Leaderboards.Hay_Single` | `10,000,000` hay on single drone `8x8` |
| Maze | `Leaderboards.Maze` | `9,863,168` gold |
| Maze Single | `Leaderboards.Maze_Single` | `616,448` gold on single drone `8x8` |
| Pumpkins | `Leaderboards.Pumpkins` | `2,000,000` pumpkins |
| Pumpkins Single | `Leaderboards.Pumpkins_Single` | `1,000,000` pumpkins on single drone `8x8` |
| Sunflowers | `Leaderboards.Sunflowers` | `10,000` power |
| Sunflowers Single | `Leaderboards.Sunflowers_Single` | `10,000` power on single drone `8x8` |
| Wood | `Leaderboards.Wood` | `10,000,000,000` wood |
| Wood Single | `Leaderboards.Wood_Single` | `500,000,000` wood on single drone `8x8` |

## Fastest Reset

For this repo, the working success condition is:

```python
num_unlocked(Unlocks.Leaderboard) > 0
```

That matches both the local leaderboard notes and the actual purpose of `leader_reset.py`.

## Old Wiki Page Caveat

The public wiki `Leaderboard` page appears stale in several places:

- it still mentions a `Polyculture` leaderboard that is not present in the local stub,
- it lists much smaller resource thresholds like `100000`,
- it lists old dinosaur targets like `98010`,
- its "equivalent simulation" snippets do not match the current local leaderboard enums.

For current route work, do not treat that page as authoritative.

## Practical Notes

- If a run reaches the target but never exits, it does not finish.
- If a category uses fixed start conditions, optimize for the scenario the leaderboard provides, not for this save's live inventory.
- For Fastest Reset specifically, all the value is in early unlock order, expansion timing, and placeholder replacement for cactus/maze/dino/megafarm phases.

## Sources

- original local leaderboard notes moved from the old root `leaderboard.md`
- local `__builtins__.py`
- https://thefarmerwasreplaced.wiki.gg/wiki/Leaderboard
