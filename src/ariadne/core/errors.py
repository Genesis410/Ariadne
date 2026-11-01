"""Explicit error taxonomy for Ariadne."""

class AriadneError(Exception):
    """Base exception for all Ariadne errors."""
    pass

class ConfigError(AriadneError):
    """Configuration syntax or schema validation error."""
    pass

class RunnerError(AriadneError):
    """Base class for generator runner errors."""
    pass

class GeneratorTimeoutError(RunnerError):
    """Generator process hung or exceeded execution timeout."""
    def __init__(self, seed: int, timeout_ms: int):
        self.seed = seed
        self.timeout_ms = timeout_ms
        super().__init__(f"Generator timed out on seed {seed} after {timeout_ms}ms")

class GeneratorCrashError(RunnerError):
    """Generator process exited with a non-zero code or crashed."""
    def __init__(self, seed: int, exit_code: int, stderr: str = ""):
        self.seed = seed
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"Generator crashed on seed {seed} (exit code {exit_code}): {stderr.strip()}")

class InvalidJSONError(RunnerError):
    """Generator emitted unparseable or schema-violating JSON."""
    def __init__(self, seed: int, raw_line: str, details: str = ""):
        self.seed = seed
        self.raw_line = raw_line
        self.details = details
        super().__init__(f"Invalid JSON emitted for seed {seed}: {details}")

class CircuitBreakerError(RunnerError):
    """Runner halted because consecutive failures exceeded safety threshold."""
    def __init__(self, consecutive_failures: int):
        self.consecutive_failures = consecutive_failures
        super().__init__(f"Circuit breaker tripped: {consecutive_failures} consecutive generator crashes/timeouts")
