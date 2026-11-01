"""Persistent subprocess IPC communicator with tagged line protocol and Windows tree-kill."""

import json
import queue
import shlex
import subprocess
import sys
import threading
import time
from typing import Optional
from ariadne.core.errors import (
    GeneratorCrashError,
    GeneratorTimeoutError,
    InvalidJSONError,
)
from ariadne.core.models import WorldGrid


def kill_process_tree(proc: subprocess.Popen) -> None:
    """Terminate the process and all of its child processes."""
    if proc.poll() is not None:
        return

    pid = proc.pid
    if sys.platform == "win32":
        try:
            # /F = forcefully terminate, /T = terminate process tree
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass

    try:
        proc.kill()
        proc.wait(timeout=0.5)
    except Exception:
        pass


def _stdout_reader(stdout, out_queue: queue.Queue) -> None:
    """Daemon thread reading lines from stdout pipe into queue."""
    try:
        for line in iter(stdout.readline, ""):
            out_queue.put(line)
    except Exception:
        pass
    finally:
        try:
            stdout.close()
        except Exception:
            pass


class GeneratorProcess:
    """Manages persistent subprocess communication over stdin/stdout with queue-based timeout."""

    def __init__(self, command: str, startup_timeout_ms: int = 5000):
        self.command = command
        self.startup_timeout_ms = startup_timeout_ms
        self.process: Optional[subprocess.Popen] = None
        self._line_queue: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._spawn()

    def _spawn(self) -> None:
        """Start or restart the generator subprocess."""
        if self.process:
            kill_process_tree(self.process)
            self.process = None

        self._line_queue = queue.Queue()
        args = shlex.split(self.command, posix=True)
        self.process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,  # Line buffered
        )

        assert self.process.stdout is not None
        self._reader_thread = threading.Thread(
            target=_stdout_reader,
            args=(self.process.stdout, self._line_queue),
            daemon=True,
        )
        self._reader_thread.start()

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def restart(self) -> None:
        """Force restart the process."""
        self._spawn()

    def close(self) -> None:
        """Close pipes and terminate process tree."""
        if self.process:
            kill_process_tree(self.process)
            self.process = None

    def evaluate_seed_once(self, seed: int, timeout_ms: int) -> WorldGrid:
        """Send one seed to process and wait for ARIADNE: response line with timeout."""
        if not self.is_alive():
            self._spawn()

        assert self.process is not None
        assert self.process.stdin is not None

        # Send JSON line
        request_line = json.dumps({"seed": seed}) + "\n"
        try:
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            exit_code = self.process.poll() or 1
            stderr_text = self.process.stderr.read() if self.process.stderr else ""
            self._spawn()
            raise GeneratorCrashError(seed, exit_code, stderr_text) from e

        timeout_sec = timeout_ms / 1000.0
        start_t = time.monotonic()

        while True:
            remaining = timeout_sec - (time.monotonic() - start_t)
            if remaining <= 0:
                kill_process_tree(self.process)
                self.process = None
                raise GeneratorTimeoutError(seed, timeout_ms)

            # Check if process terminated prematurely
            if self.process.poll() is not None and self._line_queue.empty():
                exit_code = self.process.returncode
                stderr_text = self.process.stderr.read() if self.process.stderr else ""
                self.process = None
                raise GeneratorCrashError(seed, exit_code, stderr_text)

            try:
                line = self._line_queue.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                continue

            line = line.strip()
            # Ignore engine logs, banners, etc. Only parse lines starting with ARIADNE:
            if line.startswith("ARIADNE:"):
                payload_str = line[len("ARIADNE:"):].strip()
                try:
                    data = json.loads(payload_str)
                except Exception as e:
                    raise InvalidJSONError(seed, line, str(e)) from e

                if "error" in data:
                    raise GeneratorCrashError(seed, 1, data.get("message", "Internal generator error"))

                try:
                    return WorldGrid.model_validate(data)
                except Exception as e:
                    raise InvalidJSONError(seed, payload_str, f"Schema validation error: {e}") from e

    def evaluate_seed(self, seed: int, timeout_ms: int) -> WorldGrid:
        """
        Evaluate seed with retry confirmation.
        If initial attempt times out, retry once with 2x timeout before raising error.
        """
        try:
            return self.evaluate_seed_once(seed, timeout_ms)
        except GeneratorTimeoutError:
            # Retry confirmation pass with relaxed timeout
            self.restart()
            return self.evaluate_seed_once(seed, timeout_ms * 2)
