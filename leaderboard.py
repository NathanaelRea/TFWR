from __builtins__ import *

LEADERBOARDS = {
    "sunflower": (Leaderboards.Sunflowers, "leader_sunflower"),
    "reset": (Leaderboards.Fastest_Reset, "leader_reset"),
}
LEADERBOARD_SPEEDUP = 32


this_run_game, this_run_name = LEADERBOARDS["reset"]

leaderboard_run(
    this_run_game,
    this_run_name,
    LEADERBOARD_SPEEDUP,
)
