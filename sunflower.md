## Sunflower Mechanics

- Sunflowers can be planted on soil like carrots or pumpkins.
- Harvesting a grown sunflower yields `Items.Power`.
- If there are at least `10` sunflowers on the farm and you harvest one with the largest petal count currently on the farm, that harvest gives `8x` power.
- If you harvest a sunflower while another sunflower with more petals still exists, the next sunflower harvest also loses the `8x` bonus.
- `measure()` returns the petal count of the sunflower under the drone even before it is fully grown.
- Sunflowers have between `7` and `15` petals inclusive.
- Multiple sunflowers can share the maximum petal count, and any of those qualify for the bonus.

## Script Strategy

- Keep the farm fully planted with sunflowers.
- Measure every sunflower during sweeps so the script knows the current maximum petal count without waiting for full growth.
- The default sunflower phase harvests only the current max-petal flowers.
- The leaderboard sunflower entry harvests multiple petal tiers to increase raw power throughput when many powered drones are active.
- Those leaderboard harvests still run in descending petal order so the highest ready flowers are taken first, but lower tiers can still miss the `8x` bonus when a higher-petal sunflower is still growing elsewhere on the farm.
- That tradeoff is intentional for the leaderboard run: it sacrifices some bonus efficiency to avoid running a large multi-drone farm at a net power loss.
- Avoid watering mature sunflowers, and avoid spending the last shared water items across multiple drones at once.
