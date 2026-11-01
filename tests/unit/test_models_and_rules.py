"""Unit tests for models, rules (Theseus), and bounding-box pruner (Atropos)."""

from ariadne.core.models import WorldGrid
from ariadne.checker.rules import (
    check_reachability,
    check_key_before_door,
)
from ariadne.shrinker.bounding_box import prune_to_minimal_failing_map


def test_world_grid_validation():
    grid = WorldGrid(
        width=5,
        height=3,
        cells=[
            "#####",
            "#@. >",
            "#####",
        ],
        legend={"#": "wall", ".": "floor", "@": "start", ">": "exit"}
    )
    assert grid.width == 5
    assert grid.height == 3
    assert grid.find_first("@") == (1, 1)
    assert grid.find_first(">") == (4, 1)
    assert len(grid.compute_hash()) == 64


def test_reachability_pass():
    grid = WorldGrid(
        width=6,
        height=3,
        cells=[
            "######",
            "#@...>",
            "######",
        ],
        legend={"#": "wall", ".": "floor", "@": "start", ">": "exit"}
    )
    is_reach, msg, visited = check_reachability(grid)
    assert is_reach is True
    assert (5, 1) in visited


def test_reachability_fail_and_prune():
    # Large 20x10 map with exit enclosed in wall
    cells = [
        "####################",
        "#@........#........#",
        "#.........#........#",
        "#.........#........#",
        "#.........#..#####.#",
        "#.........#..#>..#.#",
        "#.........#..#####.#",
        "#.........#........#",
        "#..................#",
        "####################",
    ]
    grid = WorldGrid(
        width=20,
        height=10,
        cells=cells,
        legend={"#": "wall", ".": "floor", "@": "start", ">": "exit"}
    )
    is_reach, msg, visited = check_reachability(grid)
    assert is_reach is False

    # Prune it
    pruned = prune_to_minimal_failing_map(
        grid,
        rule_name="reachable",
        failure_description=msg,
        check_fn=check_reachability,
    )
    assert pruned.subgrid.width <= grid.width
    assert pruned.subgrid.height <= grid.height
    # The pruned subgrid must also be unreachable
    sub_reach, _, _ = check_reachability(pruned.subgrid)
    assert sub_reach is False


def test_key_before_door_pass():
    cells = [
        "#######",
        "#@.k.D>",
        "#######",
    ]
    grid = WorldGrid(
        width=7,
        height=3,
        cells=cells,
        legend={"#": "wall", ".": "floor", "@": "start", ">": "exit", "k": "key:gold", "D": "door:gold"}
    )
    is_solvable, msg, visited = check_key_before_door(grid)
    assert is_solvable is True


def test_key_before_door_softlock():
    # Key is placed AFTER the locked door!
    cells = [
        "#######",
        "#@.D.k>",
        "#######",
    ]
    grid = WorldGrid(
        width=7,
        height=3,
        cells=cells,
        legend={"#": "wall", ".": "floor", "@": "start", ">": "exit", "k": "key:gold", "D": "door:gold"}
    )
    is_solvable, msg, visited = check_key_before_door(grid)
    assert is_solvable is False
    assert "blocked by locked door" in msg


def test_bounding_box_pruning_on_large_map():
    """Verify that an 80x50 map shrinks by >90% to isolate the failing component."""
    width = 80
    height = 50
    # Start with all solid walls
    grid_chars = [["#" for _ in range(width)] for _ in range(height)]

    # Room 1 (Start) at (x: 4..10, y: 4..8)
    for y in range(4, 9):
        for x in range(4, 11):
            grid_chars[y][x] = "."
    grid_chars[6][6] = "@"

    # Room 2 (Exit) at (x: 16..22, y: 5..9)
    for y in range(5, 10):
        for x in range(16, 23):
            grid_chars[y][x] = "."
    grid_chars[7][19] = ">"

    # The rest of the 80x50 map contains distant unrelated rooms
    for y in range(30, 45):
        for x in range(40, 75):
            grid_chars[y][x] = "."

    cells = ["".join(row) for row in grid_chars]
    grid = WorldGrid(
        width=width,
        height=height,
        cells=cells,
        legend={"#": "wall", ".": "floor", "@": "start", ">": "exit"}
    )

    is_reach, msg, visited = check_reachability(grid)
    assert is_reach is False

    pruned = prune_to_minimal_failing_map(
        grid,
        rule_name="reachable",
        failure_description=msg,
        check_fn=check_reachability,
    )

    # Subgrid must be massively smaller than 80x50
    original_area = 80 * 50
    pruned_area = pruned.subgrid.width * pruned.subgrid.height
    reduction = (original_area - pruned_area) / original_area

    # Must reduce map area by at least 90%
    assert reduction > 0.90, f"Expected >90% reduction, got {reduction*100:.1f}%"
    assert pruned.subgrid.width <= 25
    assert pruned.subgrid.height <= 15
    assert pruned.original_width == 80
    assert pruned.original_height == 50

    # Pruned subgrid must still reliably reproduce the failure
    sub_reach, _, _ = check_reachability(pruned.subgrid)
    assert sub_reach is False

    # Label must contain 0-indexed coordinates
    assert "Subgrid [x:" in pruned.label
    assert "from original 80x50 (0-indexed)" in pruned.label
