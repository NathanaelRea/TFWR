from __builtins__ import *

elapsed = simulate(
	"phase9_simulate_worker",
	{Unlocks.Plant: 1, Unlocks.Carrots: 1},
	{Items.Hay: 1, Items.Wood: 1},
	{},
	11,
	4,
)
quick_print("elapsed", elapsed)
