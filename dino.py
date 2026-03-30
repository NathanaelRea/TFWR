from __builtins__ import *
from utils import *

DINO_DIRECTIONS = [North, East, South, West]
DINO_CYCLE_SIZE = None
DINO_CYCLE_INDEX = {}
DINO_INITIAL_APPLE_WAIT = 64
DINO_PHASE_GREEDY = 0
DINO_PHASE_HAMILTON = 1
DINO_PHASE_LAWN = 2


def dino_tail_target():
	size = get_world_size()
	return size * size - 1


def apple_cactus_cost():
	cost = get_cost(Entities.Apple)
	if cost == None:
		return None
	if Items.Cactus not in cost:
		return None
	return cost[Items.Cactus]


def dino_cactus_budget():
	apple_cost = apple_cactus_cost()
	if apple_cost == None:
		return None
	return dino_tail_target() * apple_cost


def dino_bone_goal():
	cost = get_cost(Unlocks.Dinosaurs)
	if cost == None:
		return 0
	if Items.Bone not in cost:
		return 0
	return cost[Items.Bone]


def needs_dino_phase():
	if num_unlocked(Unlocks.Dinosaurs) <= 0:
		return False

	if get_world_size() % 2 != 0:
		return False

	bone_goal = dino_bone_goal()
	if bone_goal <= 0:
		return False

	if num_items(Items.Bone) >= bone_goal:
		return False

	cactus_budget = dino_cactus_budget()
	if cactus_budget == None:
		return False

	return num_items(Items.Cactus) >= cactus_budget


def dino_head():
	return (get_pos_x(), get_pos_y())


def dino_neighbor(pos, direction):
	x, y = pos

	if direction == North:
		return (x, y + 1)
	if direction == South:
		return (x, y - 1)
	if direction == East:
		return (x + 1, y)
	return (x - 1, y)


def dino_in_bounds(pos):
	size = get_world_size()
	x, y = pos
	return x >= 0 and x < size and y >= 0 and y < size


def dino_cycle_direction_at(x, y, size):
	if x == 0 and y > 0:
		return South

	if y == 0:
		if x < size - 1:
			return East
		return North

	if x % 2 == 1:
		if y < size - 1:
			return North
		return West

	if y > 1:
		return South
	return West


def ensure_dino_cycle():
	global DINO_CYCLE_SIZE
	global DINO_CYCLE_INDEX
	size = get_world_size()

	if DINO_CYCLE_SIZE == size:
		return

	DINO_CYCLE_SIZE = size
	DINO_CYCLE_INDEX = {}

	x = 0
	y = 0
	index = 0

	while True:
		DINO_CYCLE_INDEX[(x, y)] = index
		index += 1

		direction = dino_cycle_direction_at(x, y, size)
		x, y = dino_neighbor((x, y), direction)

		if x == 0 and y == 0:
			return


def dino_cycle_distance(start_index, end_index):
	size = get_world_size()
	length = size * size
	return (end_index - start_index + length) % length


def dino_tail_front(tail, tail_start):
	if tail_start >= len(tail):
		return None
	return tail[tail_start]


def dino_tail_length(tail, tail_start):
	return len(tail) - tail_start


def dino_greedy_limit():
	return get_world_size()


def dino_lawn_limit():
	size = get_world_size()
	area = size * size
	limit = area - size * 2
	if limit < 0:
		return 0
	return limit


def dino_phase(tail, tail_start):
	tail_length = dino_tail_length(tail, tail_start)

	if tail_length < dino_greedy_limit():
		return DINO_PHASE_GREEDY

	if tail_length >= dino_lawn_limit():
		return DINO_PHASE_LAWN

	return DINO_PHASE_HAMILTON


def dino_is_occupied(occupied, pos):
	return pos in occupied and occupied[pos] > 0


def dino_mark_occupied(occupied, pos):
	if pos in occupied:
		occupied[pos] += 1
	else:
		occupied[pos] = 1


def dino_unmark_occupied(occupied, pos):
	if pos in occupied and occupied[pos] > 0:
		occupied[pos] -= 1


def dino_trim_tail(tail, tail_start):
	if tail_start <= 0:
		return tail, tail_start

	if tail_start * 2 < len(tail):
		return tail, tail_start

	trimmed = []
	index = tail_start

	while index < len(tail):
		trimmed.append(tail[index])
		index += 1

	return trimmed, 0


def dino_shortcut_allowed(target_pos, tail, tail_start, growing):
	ensure_dino_cycle()

	tail_front = dino_tail_front(tail, tail_start)
	if tail_front == None:
		return True

	head_index = DINO_CYCLE_INDEX[dino_head()]
	target_index = DINO_CYCLE_INDEX[target_pos]
	tail_index = DINO_CYCLE_INDEX[tail_front]
	limit = dino_cycle_distance(head_index, tail_index)

	if growing:
		limit -= 1

	if limit <= 1:
		return False

	distance = dino_cycle_distance(head_index, target_index)
	return distance > 0 and distance < limit


def dino_can_step_on(pos, tail, tail_start, occupied, growing):
	if not dino_is_occupied(occupied, pos):
		return True

	if growing:
		return False

	tail_front = dino_tail_front(tail, tail_start)
	if tail_front == None:
		return False

	return pos == tail_front


def dino_distance_to_apple(pos, apple_pos):
	if apple_pos == None:
		return None

	return abs(pos[0] - apple_pos[0]) + abs(pos[1] - apple_pos[1])


def wait_for_initial_apple():
	wait_ticks = 0

	while wait_ticks < DINO_INITIAL_APPLE_WAIT:
		if get_entity_type() == Entities.Apple:
			return True

		wait_ticks += 1

	return get_entity_type() == Entities.Apple


def choose_dino_direction(tail, tail_start, occupied, apple_pos):
	ensure_dino_cycle()
	head = dino_head()
	growing = get_entity_type() == Entities.Apple
	cycle_direction = dino_cycle_direction_at(head[0], head[1], get_world_size())
	phase = dino_phase(tail, tail_start)
	legal = []

	for direction in DINO_DIRECTIONS:
		next_pos = dino_neighbor(head, direction)

		if not dino_in_bounds(next_pos):
			continue

		if not dino_can_step_on(next_pos, tail, tail_start, occupied, growing):
			continue

		legal.append(direction)

	if len(legal) <= 0:
		return None

	if phase == DINO_PHASE_LAWN:
		if cycle_direction in legal:
			return cycle_direction
		return legal[0]

	if apple_pos == None:
		if cycle_direction in legal:
			return cycle_direction
		return legal[0]

	if phase == DINO_PHASE_GREEDY:
		best_direction = None
		best_apple_distance = None
		best_cycle_distance = None
		index = 0

		while index < len(legal):
			direction = legal[index]
			next_pos = dino_neighbor(head, direction)
			apple_distance = dino_distance_to_apple(next_pos, apple_pos)
			cycle_distance = dino_cycle_distance(
				DINO_CYCLE_INDEX[next_pos],
				DINO_CYCLE_INDEX[apple_pos],
			)

			if (
				best_direction == None
				or apple_distance < best_apple_distance
				or (apple_distance == best_apple_distance and cycle_distance < best_cycle_distance)
			):
				best_direction = direction
				best_apple_distance = apple_distance
				best_cycle_distance = cycle_distance

			index += 1

		return best_direction

	best_direction = None
	best_cycle_distance = None
	index = 0

	while index < len(legal):
		direction = legal[index]
		next_pos = dino_neighbor(head, direction)

		if direction != cycle_direction and not dino_shortcut_allowed(next_pos, tail, tail_start, growing):
			index += 1
			continue

		# The cycle constraint already guarantees a safe route to the apple.
		cycle_distance = dino_cycle_distance(
			DINO_CYCLE_INDEX[next_pos],
			DINO_CYCLE_INDEX[apple_pos],
		)

		if best_direction == None or cycle_distance < best_cycle_distance:
			best_direction = direction
			best_cycle_distance = cycle_distance

		index += 1

	if best_direction != None:
		return best_direction

	if cycle_direction in legal:
		return cycle_direction

	return legal[0]


def run_dino_cycle():
	if get_world_size() % 2 != 0:
		return 0

	cactus_budget = dino_cactus_budget()
	if cactus_budget == None:
		return 0
	if num_items(Items.Cactus) < cactus_budget:
		return 0

	start_bones = num_items(Items.Bone)
	tail = []
	tail_start = 0
	occupied = {}

	# An empty board gives apples the best chance to keep spawning as the tail grows.
	clear()
	change_hat(Hats.Dinosaur_Hat)

	if not wait_for_initial_apple():
		change_hat(Hats.Cactus_Hat)
		return 0

	apple_pos = None
	if get_entity_type() == Entities.Apple:
		apple_pos = dino_head()

	while True:
		if apple_pos != None and dino_head() == apple_pos and get_entity_type() != Entities.Apple:
			apple_pos = None

		on_apple = get_entity_type() == Entities.Apple

		target_apple = apple_pos
		if on_apple:
			target_apple = measure()

		direction = choose_dino_direction(tail, tail_start, occupied, target_apple)
		if direction == None:
			break

		head = dino_head()
		if not move(direction):
			break

		if on_apple:
			tail.append(head)
			dino_mark_occupied(occupied, head)
			apple_pos = target_apple
		else:
			tail_front = dino_tail_front(tail, tail_start)
			if tail_front != None:
				dino_unmark_occupied(occupied, tail_front)
				tail_start += 1

			tail.append(head)
			dino_mark_occupied(occupied, head)

		tail, tail_start = dino_trim_tail(tail, tail_start)

	change_hat(Hats.Cactus_Hat)
	return num_items(Items.Bone) - start_bones


def dino_main():
	enter_dino_world(DINO_WORLD)

	while True:
		harvested = run_dino_cycle()
		quick_print("dino", "harvest", harvested, "bones", num_items(Items.Bone))


if should_auto_run():
	dino_main()
