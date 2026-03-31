# Sunflowers

This file merges the existing local sunflower notes with current wiki references.

## Safe Core Rules

Across sources, these points are consistent:

- Sunflowers grow on soil.
- `measure()` reads sunflower petals.
- Harvesting a sunflower yields `Power`.
- Harvesting a non-maximum-petal sunflower is bad and can wipe or invalidate the rest of the sunflower field.
- Power doubles drone speed while it lasts.

## Local Workspace Strategy Notes

These came from the existing `sunflower.md` and are the assumptions the local scripts are already built around:

- keep the farm fully planted with sunflowers,
- measure every sunflower during sweeps,
- harvest current max-petal flowers first,
- leaderboard sunflower logic may intentionally harvest multiple petal tiers,
- avoid watering mature sunflowers,
- avoid spending the last shared water stock across multiple drones at once.

## Source Conflicts

There is a real documentation mismatch here:

- old/current wiki `Sunflowers` page:
  - harvest yields power equal to `sqrt(number_of_sunflowers_on_farm)`,
  - harvesting a non-max-petal flower destroys all sunflowers,
  - power is consumed at about `1` per `30` actions.
- local `sunflower.md`:
  - petal range is `7` to `15`,
  - with at least `10` sunflowers, harvesting a maximum-petal flower gives an `8x` bonus,
  - harvesting below the current maximum can spoil the next bonus opportunity.
- local `__builtins__.py`:
  - harvesting a maximum-petal sunflower with at least `10` sunflowers gives a `5x` bonus.

## Best Working Assumption For This Repo

Because the sources disagree on the exact multiplier, the safest repo-local rule is:

- never hard-code sunflower bonus math into route-critical logic unless you verify it in-game for the exact version you are running,
- do preserve the ordering rule: highest-petal-first remains correct under every source,
- do keep measuring petals before maturity, because that gives planning information cheaply.

## Why It Matters For `leader_reset.py`

- Sunflowers are the earliest source of `Power`.
- `Power` doubles movement and action throughput, so even modest sunflower infrastructure can change break-even points for expanding, watering, or doing longer sweeps.
- The current reset scaffold unlocks sunflowers in phase 2 but does not yet exploit sunflower-specific routing.

## Sources

- local `sunflower.md`
- local `__builtins__.py`
- https://thefarmerwasreplaced.wiki.gg/wiki/Sunflowers
- https://thefarmerwasreplaced.wiki.gg/wiki/Entities
- https://thefarmerwasreplaced.wiki.gg/wiki/Plant_growth

