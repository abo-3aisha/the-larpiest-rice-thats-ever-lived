#!/usr/bin/env python3
# Reads cava raw frames (16bit LE) from stdin and renders a 3-row bar equalizer
# into an already-drawn terminal layout (rows 7..9). Never clears the screen.
import sys

BARS = int(sys.argv[1]) if len(sys.argv) > 1 else 28
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
FRAME = BARS * 2

ROW_COLOR = {0: "\033[38;5;105m", 1: "\033[38;5;213m", 2: "\033[38;5;224m"}
ROW_CELL = {0: "▁", 1: "▄", 2: "█"}

_sm = [0.0] * BARS
_idle_t = 0
import math as _m

def bars_from(data):
    vals = []
    for i in range(BARS):
        low = data[i * 2]
        hi = data[i * 2 + 1]
        vals.append((low + (hi << 8)) / 65536.0)
    for i, v in enumerate(vals):
        _sm[i] = 0.55 * _sm[i] + 0.45 * v
    return list(_sm)

def draw(vals):
    global _idle_t
    peak = max(vals)
    if peak < 0.02:
        _idle_t += 1
        for i in range(BARS):
            vals[i] = max(0.0, min(1.0, _m.sin(_idle_t * 0.45 + i * 0.55) * 0.35 + 0.35))
    else:
        _idle_t = 0
    rendered = []
    for r in range(ROWS):
        line = ""
        for v in vals:
            level = int(v * ROWS + 0.5)
            if level > ROWS:
                level = ROWS
            line += (ROW_CELL[r] if level > r else " ") * 2
        rendered.append(f"\033[{7 + r};1H\033[K" + ROW_COLOR[r] + line + "\033[0m")
    sys.stdout.write("".join(rendered))
    sys.stdout.flush()

try:
    while True:
        chunk = sys.stdin.buffer.read(FRAME)
        if len(chunk) < FRAME:
            break
        draw(bars_from(chunk))
except (BrokenPipeError, KeyboardInterrupt):
    pass