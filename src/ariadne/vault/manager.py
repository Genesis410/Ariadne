"""Seed Vault manager for persisting regression seeds in .ariadne/vault.jsonl."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from ariadne.core.models import SeedResult


class VaultManager:
    """Handles git-friendly JSON Lines regression storage."""

    def __init__(self, vault_path: Path | str = ".ariadne/vault.jsonl"):
        self.vault_path = Path(vault_path)

    def _ensure_dir(self) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)

    def load_entries(self) -> List[Dict[str, Any]]:
        """Load all vault records sorted deterministically by seed."""
        if not self.vault_path.exists():
            return []

        entries: List[Dict[str, Any]] = []
        with open(self.vault_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        entries.sort(key=lambda x: x.get("seed", 0))
        return entries

    def get_seeds(self) -> List[int]:
        """Get unique list of failing seeds recorded in vault."""
        return [e["seed"] for e in self.load_entries() if "seed" in e]

    def record_failure(self, result: SeedResult) -> None:
        """Record a newly discovered failing seed (deduplicated)."""
        self._ensure_dir()
        existing = self.load_entries()
        existing_signatures = {
            (e.get("seed"), e.get("error_type"), e.get("rule")) for e in existing
        }

        signature = (result.seed, result.status, result.violated_rule)
        if signature in existing_signatures:
            return  # Duplicate failure signature already recorded

        grid_hash = result.grid.compute_hash() if result.grid else None
        entry = {
            "seed": result.seed,
            "error_type": result.status,
            "rule": result.violated_rule,
            "grid_hash": grid_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        existing.append(entry)
        existing.sort(key=lambda x: x["seed"])

        with open(self.vault_path, "w", encoding="utf-8") as f:
            for item in existing:
                f.write(json.dumps(item) + "\n")

    def clear(self) -> None:
        """Clear all entries in the vault."""
        if self.vault_path.exists():
            self.vault_path.unlink()

    def prune_passed(self, passed_seeds: Set[int]) -> int:
        """Remove seeds that now successfully pass."""
        existing = self.load_entries()
        remaining = [e for e in existing if e.get("seed") not in passed_seeds]
        pruned_count = len(existing) - len(remaining)

        if pruned_count > 0:
            with open(self.vault_path, "w", encoding="utf-8") as f:
                for item in remaining:
                    f.write(json.dumps(item) + "\n")

        return pruned_count
