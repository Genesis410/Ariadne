"""Atropos: Minimal Failing Map shrinker via rectangular Bounding-Box Pruning."""

from typing import Callable, Optional, Set, Tuple
from ariadne.core.models import PrunedSubgrid, WorldGrid


def extract_subgrid(
    original: WorldGrid,
    x_min: int,
    y_min: int,
    x_max: int,
    y_max: int,
    outside_as_wall: bool = True
) -> WorldGrid:
    """
    Extract rectangular subgrid [x_min, x_max] x [y_min, y_max].
    If outside_as_wall is True, the outermost perimeter boundary of the subgrid is replaced with '#'
    unless that tile was the original start or exit.
    """
    sub_width = x_max - x_min + 1
    sub_height = y_max - y_min + 1
    rows = []

    for y in range(y_min, y_max + 1):
        row_chars = []
        for x in range(x_min, x_max + 1):
            char = original.get(x, y)
            if outside_as_wall:
                # If on border of subgrid and not in original border, wall it off
                is_sub_border = (x == x_min or x == x_max or y == y_min or y == y_max)
                sem = original.get_semantic(x, y)
                if is_sub_border and sem not in ("start", "exit", "key", "door"):
                    char = "#"
            row_chars.append(char)
        rows.append("".join(row_chars))

    return WorldGrid(
        width=sub_width,
        height=sub_height,
        cells=rows,
        legend=original.legend.copy()
    )


def prune_to_minimal_failing_map(
    grid: WorldGrid,
    rule_name: str,
    failure_description: str,
    check_fn: Callable[[WorldGrid], Tuple[bool, str, Set[Tuple[int, int]]]],
    start_char: str = "@",
    target_char: str = ">"
) -> PrunedSubgrid:
    """
    Prune a failing grid down to the smallest rectangular bounding box that still fails the rule.
    """
    # 1. Identify critical coordinates: start, target, and reachable tiles
    start_pos = grid.find_first(start_char)
    target_pos = grid.find_first(target_char)

    _, _, visited_tiles = check_fn(grid)

    critical_points = set(visited_tiles)
    if start_pos:
        critical_points.add(start_pos)
    if target_pos:
        critical_points.add(target_pos)

    if not critical_points:
        # Fallback to full grid if no points identified
        return PrunedSubgrid(
            x_min=0,
            y_min=0,
            x_max=grid.width - 1,
            y_max=grid.height - 1,
            original_width=grid.width,
            original_height=grid.height,
            subgrid=grid,
            rule_violated=rule_name,
            failure_description=failure_description
        )

    # 2. Initial bounding box around critical points + 1 padding ring for perimeter walls
    x_coords = [p[0] for p in critical_points]
    y_coords = [p[1] for p in critical_points]

    x_min = max(0, min(x_coords) - 1)
    y_min = max(0, min(y_coords) - 1)
    x_max = min(grid.width - 1, max(x_coords) + 1)
    y_max = min(grid.height - 1, max(y_coords) + 1)

    # 3. Iterative verification: Ensure subgrid still fails the rule
    # If the cropped subgrid passes (e.g. wall cutoff broke the proof), expand outwards
    ring = 0
    max_expand = max(grid.width, grid.height)

    while ring < max_expand:
        cur_x_min = max(0, x_min - ring)
        cur_y_min = max(0, y_min - ring)
        cur_x_max = min(grid.width - 1, x_max + ring)
        cur_y_max = min(grid.height - 1, y_max + ring)

        subgrid = extract_subgrid(grid, cur_x_min, cur_y_min, cur_x_max, cur_y_max, outside_as_wall=True)
        is_pass, reason, _ = check_fn(subgrid)

        if not is_pass:
            # Successfully reproduced the failure on the smaller subgrid!
            return PrunedSubgrid(
                x_min=cur_x_min,
                y_min=cur_y_min,
                x_max=cur_x_max,
                y_max=cur_y_max,
                original_width=grid.width,
                original_height=grid.height,
                subgrid=subgrid,
                rule_violated=rule_name,
                failure_description=failure_description
            )
        ring += 1

    # Fallback if expansion reached full size
    return PrunedSubgrid(
        x_min=0,
        y_min=0,
        x_max=grid.width - 1,
        y_max=grid.height - 1,
        original_width=grid.width,
        original_height=grid.height,
        subgrid=grid,
        rule_violated=rule_name,
        failure_description=failure_description
    )
