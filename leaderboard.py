from __builtins__ import *

LEADERBOARD_NAME = "sunflower"
LEADERBOARD_SPEEDUP = 10000


def run_selected_leaderboard():
	if LEADERBOARD_NAME == "sunflower":
		quick_print("leaderboard", "start", LEADERBOARD_NAME)
		leaderboard_run(
			Leaderboards.Sunflowers,
			"leader_sunflower",
			LEADERBOARD_SPEEDUP,
		)
		return

	quick_print("leaderboard", "invalid", LEADERBOARD_NAME)


run_selected_leaderboard()
