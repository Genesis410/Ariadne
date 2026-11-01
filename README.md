# ARIADNE 🧵

> **Automated verification & Minimal Failing Map pruner for procedural game worlds.**  
> *Catch the 0.05% softlock bug before your Steam players do.*

[![CI](https://github.com/Genesis410/Ariadne/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Genesis410/Ariadne/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)]()
[![OS](https://img.shields.io/badge/OS-Windows%20%7C%20Linux-blue.svg)]()
[![Engines](https://img.shields.io/badge/engines-Godot%20%7C%20Unity%20%7C%20Python%20%7C%20Rust%20%7C%20C%2B%2B-purple.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## The Problem

In Greek mythology, Ariadne gave Theseus a thread to navigate the Minotaur's Labyrinth and escape alive.

In modern game development, procedural level generators (roguelikes, dungeon crawlers) often ship with rare, game-breaking bugs:
- Pockets of the level unreachable from the player spawn
- Critical keys locked behind the very doors they are supposed to open
- Generators hanging in infinite loops on edge-case seeds

Manual playtesting **cannot catch a bug that occurs in 1 out of 2,000 seeds**. When that 0.05% bug hits a player on floor 7 of a run, it becomes a negative Steam review.

---

## How Ariadne Solves It

Ariadne tests **thousands of seeds per minute** using a black-box streaming protocol, checks topological invariants, and produces a **Minimal Failing Map** (the smallest cropped subgrid proving the bug) that you can immediately paste into Discord or a GitHub issue.

```text
┌────────────────────────── Counterexample Details ───────────────────────────┐
│ SEED FAILURE DETECTED                                                       │
│ - Seed ID        : 1350                                                     │
│ - Rule Violated  : reachable                                                │
│ - Explanation    : Exit '>' at (x=20, y=6) is unreachable from '@' at (x=5, │
│ y=5)                                                                        │
│ - Crop Region    : Subgrid [x:1..21, y:1..10] (21x10) from original 30x15   │
│ (0-indexed)                                                                 │
│ - Coordinates    : 0-indexed, (x=col, y=row), (0,0) at top-left             │
│ - Sliced Edges   : Outside boundary verified as solid wall                  │
│ - Chokepoint Hint : Opening wall '#' at (x=14, y=6) [subgrid: (13, 5)]      │
│ bridges '@' to '>'                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
┌─ Minimal Failing Map (21x10) [x:1..21, y:1..10] ─┐
│ #####################                            │
│ #..........##########                            │
│ #..........####.....#                            │
│ #..........####.....#                            │
│ #...@......####.....#                            │
│ #............!.....>#                            │
│ #..........####.....#                            │
│ #..........####.....#                            │
│ #..........####.....#                            │
│ #####################                            │
└──────────────────────────────────────────────────┘
  Legend: @ Start, > Exit, ! Chokepoint Wall (turning into floor restores path)

Regression seed saved to .ariadne/vault.jsonl
Status: FAILED (Exit Code 1)
```

---

## Key Features

- 🔌 **Black-Box Streaming Protocol**: Works with **Godot 4, Unity, Rust, C++, and Python**. Ariadne talks over `stdin`/`stdout` JSON Lines (`ARIADNE:{...}`), completely isolated from engine boot banners.
- ✂️ **Minimal Failing Map (Bounding-Box Pruner)**: Crops the failing map to the smallest bounding box where the bug still reproduces (with outside-as-wall verification) without mutating interior topology.
- 🏰 **Built-in Invariant Rules**:
  - `reachable(from, to)` — BFS path reachability.
  - `connected_walkable` — Guarantees all floors form a single connected component.
  - `key_before_door` — Solvability check ensuring colored keys are reachable before matching locked doors.
- 📦 **Seed Vault (`.ariadne/vault.jsonl`)**: Git-friendly regression tracking. Failing seeds are automatically replayed in CI before running random seeds.
- ⚡ **Resilience Watchdog**: 500ms per-seed timeout with confirmation retry, automatic process tree termination (`taskkill /T /F` on Windows / POSIX kill), and a 20-crash circuit breaker.

---

## Quickstart

### 1. Installation

**Option A: Standalone Binary (Windows x64 - No Python Required)**
1. Download and extract `ariadne-v*-windows-x64.zip` from [GitHub Releases](https://github.com/Genesis410/Ariadne/releases).
2. **Note on CLI Usage**: Ariadne is a terminal/CLI tool, not a GUI desktop app. Do **not** double-click `ariadne.exe` directly in File Explorer (the terminal will close immediately).
3. **How to Run**:
   - Open the extracted folder in File Explorer.
   - Click the address bar at the top, type `cmd`, and press **Enter** (or right-click empty space and choose **Open in Terminal**).
   - Run commands:
     ```cmd
     .\ariadne.exe --help
     ```
4. Verify integrity with `checksums.txt`.
   *(Note: Binary is built transparently via GitHub Actions without a paid code-signing certificate; click "More info -> Run anyway" if Windows SmartScreen prompts on first run).*
5. *(Optional)* Add the extracted directory to your system `PATH` to run `ariadne` from any directory.

**Option B: Via Python Pip (Windows & Linux)**
```bash
git clone https://github.com/Genesis410/Ariadne.git
cd Ariadne
pip install -e .
```

### 2. Initialize in your Game Project

```bash
ariadne init --template godot4    # For Godot 4 games
# OR
ariadne init --template python    # For Python games
```

This creates:
- `ariadne.toml` — The test configuration file.
- `ariadne_adapter.*` — A starter adapter with a sample generator containing an intentional 2% bug to see Ariadne in action immediately!

### 3. Run the Evaluation

```bash
ariadne run --seeds 100
```

### 4. Manage the Seed Vault

```bash
# List all recorded regression seeds
ariadne vault list

# Clear the vault
ariadne vault clear --yes
```

---

## Configuration (`ariadne.toml`)

```toml
schema_version = 1

[project]
name = "MyRoguelike"
command = "godot_console.exe --headless -s ariadne_adapter.gd"
startup_timeout_ms = 5000
seed_timeout_ms = 500

[seeds]
base_seed = 1337
count = 1000

[legend]
"#" = "wall"
"." = "floor"
"@" = "start"
">" = "exit"
"k" = "key:gold"
"D" = "door:gold"

[rules]
reachable = { from = "@", to = ">" }
connected_walkable = true
key_before_door = true
```

---

## CI / GitHub Actions Integration

Ariadne returns strict exit codes:
- `0`: All seeds passed.
- `1`: Seed failure detected (property violation, timeout, or crash).
- `2`: Configuration or runner execution error.

Add this step to `.github/workflows/ci.yml`:

```yaml
- name: Verify Procedural Levels
  run: |
    pip install ariadne-procgen
    ariadne run --seeds 5000
```

---

## Testing

Run the test suite:

```bash
pytest -v
```

All 8 unit and integration tests verify reachability, key-door solvers, bounding-box shrinking, watchdog process timeouts, and CLI workflows.

---

## License

MIT © [Genesis410](https://github.com/Genesis410)
