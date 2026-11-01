"""Cross-platform determinism test for seed evaluation and hash consistency."""

from ariadne.cli.templates.sample_generator import generate_dungeon
from ariadne.core.models import WorldGrid
from ariadne.checker.rules import check_reachability


# Fixed golden SHA-256 hashes for cross-platform determinism verification.
# Linux, Windows, and macOS MUST produce these exact byte-for-byte hashes.
GOLDEN_GRID_HASHES = {
    42: "32a3d058171f21c57bce26ab21e3002acb554e780bdb4ea0580c2807c03da47e",
    50: "70aeec98486c46cf393938963abe107bdf4a68461c858be9561dd221471949df",
    1337: "32a3d058171f21c57bce26ab21e3002acb554e780bdb4ea0580c2807c03da47e",
    48213: "32a3d058171f21c57bce26ab21e3002acb554e780bdb4ea0580c2807c03da47e",
    99999: "32a3d058171f21c57bce26ab21e3002acb554e780bdb4ea0580c2807c03da47e",
}

GOLDEN_VERDICTS = {
    42: True,
    50: False,
    1337: True,
    48213: True,
    99999: True,
}


def test_seed_determinism_across_runs():
    """Verify that identical seeds produce identical grid hashes and verdicts across OS."""
    for s, expected_hash in GOLDEN_GRID_HASHES.items():
        raw = generate_dungeon(s)
        grid = WorldGrid.model_validate(raw)
        h = grid.compute_hash()
        is_reach, _, _ = check_reachability(grid)

        # Cross-OS golden constant check
        assert h == expected_hash, (
            f"Cross-OS determinism broken on seed {s}: "
            f"got {h}, expected golden {expected_hash}"
        )
        assert is_reach == GOLDEN_VERDICTS[s], (
            f"Verdict mismatch on seed {s}: got {is_reach}, expected {GOLDEN_VERDICTS[s]}"
        )
