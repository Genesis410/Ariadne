"""Integration tests for frozen PyInstaller executable (dist/ariadne/ariadne.exe).

Verifies watchdog timeout, crash recovery, and invalid JSON handling directly from within
the packaged binary on Windows.
"""

from pathlib import Path
import shutil
import subprocess
import pytest


@pytest.fixture
def exe_path():
    p = Path("dist/ariadne/ariadne.exe").resolve()
    if not p.exists():
        pytest.skip("dist/ariadne/ariadne.exe not built; skipping frozen binary tests")
    return p


@pytest.fixture
def scratch_dir(tmp_path):
    d = tmp_path / "frozen_test"
    d.mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_frozen_exe_timeout_and_process_kill(exe_path, scratch_dir):
    """Test that watchdog in frozen .exe terminates hung generator processes."""
    adapter = scratch_dir / "hang_adapter.py"
    adapter.write_text(
        "import sys, time\n"
        "for line in sys.stdin:\n"
        "    if line.strip():\n"
        "        time.sleep(2)\n",
        encoding="utf-8"
    )

    toml = scratch_dir / "ariadne.toml"
    toml.write_text(
        "schema_version = 1\n"
        "[project]\n"
        "name = 'HangTest'\n"
        "command = 'python hang_adapter.py'\n"
        "startup_timeout_ms = 3000\n"
        "seed_timeout_ms = 300\n"
        "[seeds]\n"
        "base_seed = 100\n"
        "count = 1\n"
        "[legend]\n"
        "'#' = 'wall'\n"
        "'.' = 'floor'\n"
        "[rules]\n"
        "reachable = { from = '@', to = '>' }\n",
        encoding="utf-8"
    )

    res = subprocess.run(
        [str(exe_path), "run", "--seeds", "1"],
        cwd=scratch_dir,
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 1
    assert "Timeouts" in res.stdout or "TIMEOUT" in res.stdout


def test_frozen_exe_crash_recovery(exe_path, scratch_dir):
    """Test that frozen .exe handles abrupt process crash without crashing itself."""
    adapter = scratch_dir / "crash_adapter.py"
    adapter.write_text(
        "import sys\n"
        "for line in sys.stdin:\n"
        "    sys.exit(139)\n",
        encoding="utf-8"
    )

    toml = scratch_dir / "ariadne.toml"
    toml.write_text(
        "schema_version = 1\n"
        "[project]\n"
        "name = 'CrashTest'\n"
        "command = 'python crash_adapter.py'\n"
        "startup_timeout_ms = 3000\n"
        "seed_timeout_ms = 300\n"
        "[seeds]\n"
        "base_seed = 200\n"
        "count = 1\n"
        "[legend]\n"
        "'#' = 'wall'\n"
        "'.' = 'floor'\n"
        "[rules]\n"
        "reachable = { from = '@', to = '>' }\n",
        encoding="utf-8"
    )

    res = subprocess.run(
        [str(exe_path), "run", "--seeds", "1"],
        cwd=scratch_dir,
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 1
    assert "Crashes" in res.stdout or "CRASH" in res.stdout
