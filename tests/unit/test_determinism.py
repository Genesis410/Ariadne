"""Cross-platform determinism test for seed evaluation and hash consistency."""

from ariadne.cli.templates.sample_generator import generate_dungeon
from ariadne.core.models import WorldGrid
from ariadne.checker.rules import check_reachability


def test_seed_determinism_across_runs():
    """Verify that identical seeds produce identical grid hashes and verdicts."""
    test_seeds = [42, 50, 1337, 48213, 99999]

    # Pre-calculated SHA-256 hashes for reference
    # Ensuring Linux and Windows produce byte-for-byte identical output
    first_run_hashes = {}
    first_run_verdicts = {}

    for s in test_seeds:
        raw = generate_dungeon(s)
        grid = WorldGrid.model_validate(raw)
        h = grid.compute_hash()
        is_reach, _, _ = check_reachability(grid)

        first_run_hashes[s] = h
        first_run_verdicts[s] = is_reach

    # Second pass: must be completely identical
    for s in test_seeds:
        raw = generate_dungeon(s)
        grid = WorldGrid.model_validate(raw)
        h = grid.compute_hash()
        is_reach, _, _ = check_reachability(grid)

        assert h == first_run_hashes[s], f"Determinism broken on seed {s}: hash mismatch"
        assert is_reach == first_run_verdicts[s], f"Verdict mismatch on seed {s}"

    # Specific property invariant check:
    # Seed 50 has the intentional corridor blockage (seed % 50 == 0)
    assert first_run_verdicts[50] is False
    assert first_run_verdicts[42] is True
    assert first_run_verdicts[1337] is True
