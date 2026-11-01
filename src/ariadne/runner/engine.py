"""Labyrinthos: Batch runner orchestration and rule verification engine."""

import time
from typing import Callable, List, Optional
from ariadne.checker.rules import (
    check_connected_walkable,
    check_key_before_door,
    check_reachability,
)
from ariadne.core.config import AriadneConfig
from ariadne.core.errors import (
    CircuitBreakerError,
    GeneratorCrashError,
    GeneratorTimeoutError,
    InvalidJSONError,
)
from ariadne.core.models import RunSummary, SeedResult, WorldGrid
from ariadne.runner.ipc import GeneratorProcess
from ariadne.shrinker.bounding_box import prune_to_minimal_failing_map
from ariadne.vault.manager import VaultManager

CONSECUTIVE_CRASH_LIMIT = 20


class LabyrinthosRunner:
    """Orchestrates seed generation, watchdog supervision, and property evaluation."""

    def __init__(self, config: AriadneConfig, vault_manager: Optional[VaultManager] = None):
        self.config = config
        self.vault = vault_manager or VaultManager()
        self.process = GeneratorProcess(
            command=config.project.command,
            startup_timeout_ms=config.project.startup_timeout_ms,
        )

    def close(self) -> None:
        self.process.close()

    def evaluate_rules(self, grid: WorldGrid) -> tuple[bool, Optional[str], Optional[str], Optional[Callable]]:
        """
        Evaluate active rules on a WorldGrid.
        Returns: (is_passed, violated_rule_name, failure_message, check_function)
        """
        # 1. Reachability rule
        if self.config.rules.reachable:
            r_cfg = self.config.rules.reachable
            check_fn = lambda g: check_reachability(g, from_target=r_cfg.from_point, to_target=r_cfg.to_point)
            is_reach, msg, _ = check_fn(grid)
            if not is_reach:
                return False, "reachable", msg, check_fn

        # 2. Connected walkable
        if self.config.rules.connected_walkable:
            is_conn, msg, _ = check_connected_walkable(grid)
            if not is_conn:
                return False, "connected_walkable", msg, check_connected_walkable

        # 3. Key before door
        if self.config.rules.key_before_door:
            is_solvable, msg, _ = check_key_before_door(grid)
            if not is_solvable:
                return False, "key_before_door", msg, check_key_before_door

        return True, None, None, None

    def test_single_seed(self, seed: int) -> SeedResult:
        """Run one seed through generator and active checkers."""
        start_t = time.monotonic()
        timeout_ms = self.config.project.seed_timeout_ms

        try:
            grid = self.process.evaluate_seed(seed, timeout_ms=timeout_ms)
            is_pass, rule_name, fail_msg, check_fn = self.evaluate_rules(grid)

            duration_ms = (time.monotonic() - start_t) * 1000.0

            if is_pass:
                return SeedResult(seed=seed, status="pass", duration_ms=duration_ms, grid=grid)

            # Property violation detected: Prune to Minimal Failing Map
            pruned = None
            if check_fn:
                pruned = prune_to_minimal_failing_map(
                    grid=grid,
                    rule_name=rule_name or "unknown",
                    failure_description=fail_msg or "",
                    check_fn=check_fn,
                )

            res = SeedResult(
                seed=seed,
                status="property_violation",
                duration_ms=duration_ms,
                error_message=fail_msg,
                violated_rule=rule_name,
                grid=grid,
                pruned_map=pruned,
            )
            self.vault.record_failure(res)
            return res

        except GeneratorTimeoutError as e:
            duration_ms = (time.monotonic() - start_t) * 1000.0
            res = SeedResult(seed=seed, status="timeout", duration_ms=duration_ms, error_message=str(e))
            self.vault.record_failure(res)
            return res
        except GeneratorCrashError as e:
            duration_ms = (time.monotonic() - start_t) * 1000.0
            res = SeedResult(seed=seed, status="crash", duration_ms=duration_ms, error_message=str(e))
            self.vault.record_failure(res)
            return res
        except InvalidJSONError as e:
            duration_ms = (time.monotonic() - start_t) * 1000.0
            res = SeedResult(seed=seed, status="invalid_json", duration_ms=duration_ms, error_message=str(e))
            self.vault.record_failure(res)
            return res

    def run_suite(
        self,
        seeds: List[int],
        replay_vault: bool = True,
        on_progress: Optional[Callable[[int, int, SeedResult], None]] = None,
    ) -> RunSummary:
        """Execute full evaluation suite."""
        summary = RunSummary()
        start_suite = time.monotonic()
        consecutive_crashes = 0

        # Phase 1: Replay Seed Vault (Fail-Fast)
        if replay_vault:
            vault_seeds = self.vault.get_seeds()
            for v_seed in vault_seeds:
                summary.vault_replayed += 1
                res = self.test_single_seed(v_seed)
                if not res.is_success:
                    summary.vault_regressions += 1
                    summary.failures.append(res)
                    # If vault regression fails, fail fast in CI
                    summary.total_seeds = 1
                    summary.failed_seeds = 1
                    summary.duration_seconds = time.monotonic() - start_suite
                    return summary

        # Phase 2: Batch seed execution
        total_seeds_count = len(seeds)
        for idx, seed in enumerate(seeds):
            summary.total_seeds += 1
            res = self.test_single_seed(seed)

            if res.is_success:
                summary.passed_seeds += 1
                consecutive_crashes = 0
            else:
                summary.failed_seeds += 1
                summary.failures.append(res)
                if res.status == "timeout":
                    summary.timeouts += 1
                    consecutive_crashes += 1
                elif res.status == "crash":
                    summary.crashes += 1
                    consecutive_crashes += 1
                elif res.status == "invalid_json":
                    summary.invalid_jsons += 1
                elif res.status == "property_violation":
                    summary.property_violations += 1
                    consecutive_crashes = 0

                # Check circuit breaker
                if consecutive_crashes >= CONSECUTIVE_CRASH_LIMIT:
                    self.close()
                    raise CircuitBreakerError(consecutive_crashes)

            if on_progress:
                on_progress(idx + 1, total_seeds_count, res)

        summary.duration_seconds = time.monotonic() - start_suite
        return summary
