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
