"""Sample procedural dungeon generator with intentional rare softlock bug for Ariadne demo."""

import json
import random
import sys


def generate_dungeon(seed: int, width: int = 30, height: int = 15):
    rng = random.Random(seed)

    # Initialize with walls
    grid = [["#" for _ in range(width)] for _ in range(height)]

    # Dig out rooms
    room_w, room_h = 10, 8
    # Room 1 (Start)
    for y in range(2, 2 + room_h):
        for x in range(2, 2 + room_w):
            grid[y][x] = "."
    grid[5][5] = "@"  # Start

    # Room 2 (Exit)
    for y in range(3, 3 + room_h):
        for x in range(16, 16 + room_w):
            grid[y][x] = "."
    grid[6][20] = ">"  # Exit

    # Corridors: connect room 1 to room 2
    # INTENTIONAL BUG: When seed % 50 == 0, the corridor is blocked by a wall!
    is_buggy_seed = (seed % 50 == 0)
    corridor_y = 6
    for x in range(11, 17):
        if is_buggy_seed and x == 14:
            grid[corridor_y][x] = "#"  # Blocked path! Softlock!
        else:
            grid[corridor_y][x] = "."

    cells = ["".join(row) for row in grid]
    return {
        "width": width,
        "height": height,
        "cells": cells,
        "legend": {
            "#": "wall",
            ".": "floor",
            "@": "start",
            ">": "exit"
        }
    }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            seed = req.get("seed", 0)
            result = generate_dungeon(seed)
            print("ARIADNE:" + json.dumps(result), flush=True)
        except Exception as e:
            err = {"error": "GeneratorCrash", "message": str(e)}
            print("ARIADNE:" + json.dumps(err), flush=True)


if __name__ == "__main__":
    main()
