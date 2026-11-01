"""Theseus: Core topological and solvability rule checkers for WorldGrid."""

from collections import deque
from typing import List, Set, Tuple
from ariadne.core.models import WorldGrid


def get_neighbors(x: int, y: int, width: int, height: int) -> List[Tuple[int, int]]:
    """Return 4-directional cardinal neighbors within bounds."""
    neighbors = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            neighbors.append((nx, ny))
    return neighbors


def check_reachability(
    grid: WorldGrid,
    from_target: str = "@",
    to_target: str = ">"
) -> Tuple[bool, str, Set[Tuple[int, int]]]:
    """
    Check if a path exists from `from_target` to `to_target` via walkable tiles.
    Returns: (is_reachable, description, reachable_coordinates_set)
    """
    start_pos = grid.find_first(from_target)
    if not start_pos:
        return False, f"Start point '{from_target}' not found in grid", set()

    exit_pos = grid.find_first(to_target)
    if not exit_pos:
        return False, f"Exit target '{to_target}' not found in grid", set()

    queue: deque[Tuple[int, int]] = deque([start_pos])
    visited: Set[Tuple[int, int]] = {start_pos}

    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == exit_pos:
            return True, "Path exists between start and exit", visited

        for nx, ny in get_neighbors(cx, cy, grid.width, grid.height):
            if (nx, ny) not in visited:
                semantic = grid.get_semantic(nx, ny)
                # Walkable if not wall
                if semantic != "wall":
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return False, f"Exit '{to_target}' at {exit_pos} is unreachable from '{from_target}' at {start_pos}", visited


def check_connected_walkable(grid: WorldGrid) -> Tuple[bool, str, Set[Tuple[int, int]]]:
    """
    Verify that all walkable tiles (floor, start, exit, items) form a single connected component.
    """
    walkable_tiles: Set[Tuple[int, int]] = set()
    for y in range(grid.height):
        for x in range(grid.width):
            if grid.get_semantic(x, y) != "wall":
                walkable_tiles.add((x, y))

    if not walkable_tiles:
        return True, "No walkable tiles found", set()

    start_pos = next(iter(walkable_tiles))
    queue: deque[Tuple[int, int]] = deque([start_pos])
    visited: Set[Tuple[int, int]] = {start_pos}

    while queue:
        cx, cy = queue.popleft()
        for nx, ny in get_neighbors(cx, cy, grid.width, grid.height):
            if (nx, ny) in walkable_tiles and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))

    unreached = walkable_tiles - visited
    if unreached:
        return (
            False,
            f"Found {len(unreached)} disconnected walkable tiles (isolated rooms/pockets)",
            visited,
        )

    return True, "All walkable tiles are fully connected", visited


def check_key_before_door(
    grid: WorldGrid,
    from_target: str = "@",
    to_target: str = ">"
) -> Tuple[bool, str, Set[Tuple[int, int]]]:
    """
    Verify that all locked doors between start and exit have their matching keys reachable first.
    Semantics: 'key:<id>' unlocks 'door:<id>'.
    """
    start_pos = grid.find_first(from_target)
    if not start_pos:
        return False, f"Start point '{from_target}' not found", set()

    exit_pos = grid.find_first(to_target)
    if not exit_pos:
        return False, f"Exit target '{to_target}' not found", set()

    collected_keys: Set[str] = set()
    visited: Set[Tuple[int, int]] = set()

    # Iterative discovery loop: explore until no new keys can be collected
    changed = True
    while changed:
        changed = False
        queue: deque[Tuple[int, int]] = deque([start_pos])
        current_visited: Set[Tuple[int, int]] = {start_pos}

        while queue:
            cx, cy = queue.popleft()
            semantic = grid.get_semantic(cx, cy)

            # Check if this cell contains a key
            if semantic.startswith("key:"):
                key_id = semantic.split(":", 1)[1]
                if key_id not in collected_keys:
                    collected_keys.add(key_id)
                    changed = True  # Newly opened door might unlock more paths

            if (cx, cy) == exit_pos:
                return True, "Exit successfully reached with required keys", current_visited

            for nx, ny in get_neighbors(cx, cy, grid.width, grid.height):
                if (nx, ny) not in current_visited:
                    n_sem = grid.get_semantic(nx, ny)
                    if n_sem == "wall":
                        continue

                    # If door, check if matching key is collected
                    if n_sem.startswith("door:"):
                        door_id = n_sem.split(":", 1)[1]
                        if door_id not in collected_keys:
                            continue  # Door is locked

                    current_visited.add((nx, ny))
                    queue.append((nx, ny))

        visited = current_visited

    return (
        False,
        f"Exit '{to_target}' blocked by locked door or missing key (keys collected: {collected_keys or 'none'})",
        visited,
    )
