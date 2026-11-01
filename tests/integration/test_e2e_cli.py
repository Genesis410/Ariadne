"""End-to-End integration tests for Ariadne CLI workflow."""

import json
from pathlib import Path
import subprocess
import sys


def test_e2e_full_workflow(tmp_path: Path):
    # 1. Run ariadne init
    res_init = subprocess.run(
        [sys.executable, "-m", "ariadne", "init", "--template", "python"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res_init.returncode == 0
    assert (tmp_path / "ariadne.toml").exists()
    assert (tmp_path / "ariadne_adapter.py").exists()

    # 2. Run ariadne run with 60 seeds (seed 50 will fail intentionally)
    res_run = subprocess.run(
        [sys.executable, "-m", "ariadne", "run", "--seeds", "60", "--base-seed", "1"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # Exit code must be 1 because seed 50 has softlock
    assert res_run.returncode == 1
    assert "Minimal Failing Map" in res_run.stdout
    assert "SEED FAILURE DETECTED" in res_run.stdout
    assert "Solvability" in res_run.stdout

    # 3. Check Seed Vault
    vault_file = tmp_path / ".ariadne" / "vault.jsonl"
    assert vault_file.exists()
    lines = vault_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    record = json.loads(lines[0])
    assert record["seed"] == 50
    assert record["error_type"] == "property_violation"

    # 4. Check vault list command
    res_vault = subprocess.run(
        [sys.executable, "-m", "ariadne", "vault", "list"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res_vault.returncode == 0
    assert "50" in res_vault.stdout

    # 5. Check vault clear command
    res_clear = subprocess.run(
        [sys.executable, "-m", "ariadne", "vault", "clear", "--yes"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res_clear.returncode == 0
    assert not vault_file.exists()
