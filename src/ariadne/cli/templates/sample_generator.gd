extends SceneTree

# Ariadne Godot 4 Headless Adapter Template
# Run with: godot_console.exe --headless -s ariadne_adapter.gd

func _init():
    var stdin = FileAccess.open("res://dummy", FileAccess.READ) # Standard stdin access in GDScript
    # In Godot 4 headless, read lines from stdin:
    while true:
        var line = OS.read_string_from_stdin(1024)
        if line.is_empty():
            OS.delay_msec(10)
            continue

        var json = JSON.new()
        var parse_err = json.parse(line.strip_edges())
        if parse_err != OK:
            continue

        var req = json.data
        var seed_val = req.get("seed", 0)
        var result = generate_level(seed_val)

        # Tagged line output:
        print("ARIADNE:" + JSON.stringify(result))

func generate_level(seed_val: int) -> Dictionary:
    var width = 30
    var height = 15
    var cells = []

    # Initialize grid
    for y in range(height):
        var row = ""
        for x in range(width):
            if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                row += "#"
            elif x == 5 and y == 5:
                row += "@" # Start
            elif x == 25 and y == 10:
                row += ">" # Exit
            elif seed_val % 50 == 0 and x == 15:
                row += "#" # Intentional bug: dividing wall softlock
            else:
                row += "."
        cells.append(row)

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
