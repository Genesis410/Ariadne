"""Integration tests for watchdog timeout, crash recovery, and circuit breaker."""

import pytest
from ariadne.core.config import AriadneConfig, ProjectConfig, RulesConfig
from ariadne.core.errors import CircuitBreakerError
from ariadne.runner.engine import LabyrinthosRunner
from ariadne.vault.manager import VaultManager


def test_watchdog_timeout_recovery(tmp_path):
    # Dummy script that sleeps indefinitely on seed 42
    script_path = tmp_path / "hang_gen.py"
    script_path.write_text("""import sys, time, json
for line in sys.stdin:
    req = json.loads(line)
    if req.get("seed") == 42:
        time.sleep(10)
    else:
        print('ARIADNE:{"width": 3, "height": 3, "cells": ["###", "#@>", "###"], "legend": {"#": "wall", "@": "start", ">": "exit"}}', flush=True)
""")

    config = AriadneConfig(
        project=ProjectConfig(
            name="HangTest",
            command=f'python "{script_path}"',
            seed_timeout_ms=100,  # Fast 100ms timeout
        ),
        rules=RulesConfig(),
    )
    vault = VaultManager(tmp_path / "vault.jsonl")
    runner = LabyrinthosRunner(config, vault_manager=vault)

    try:
        # Seed 42 should timeout
        res_timeout = runner.test_single_seed(42)
        assert res_timeout.status == "timeout"
        assert "timed out" in res_timeout.error_message.lower()

        # Generator should recover on next seed
        res_ok = runner.test_single_seed(43)
        assert res_ok.status == "pass"
    finally:
        runner.close()


def test_circuit_breaker_trips(tmp_path):
    # Dummy script that crashes immediately on every seed
    script_path = tmp_path / "crash_gen.py"
    script_path.write_text("""import sys
for line in sys.stdin:
    sys.exit(1)
""")

    config = AriadneConfig(
        project=ProjectConfig(
            name="CrashTest",
            command=f'python "{script_path}"',
            seed_timeout_ms=100,
        ),
        rules=RulesConfig(),
    )
    vault = VaultManager(tmp_path / "vault.jsonl")
    runner = LabyrinthosRunner(config, vault_manager=vault)

    try:
        # Running 25 failing seeds should trip circuit breaker at 20
        with pytest.raises(CircuitBreakerError) as exc_info:
            runner.run_suite(seeds=list(range(25)), replay_vault=False)
        assert "Circuit breaker tripped" in str(exc_info.value)
    finally:
        runner.close()
