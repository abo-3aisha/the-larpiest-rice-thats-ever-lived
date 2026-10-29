#!/usr/bin/env python3
"""waybar module (one-shot, waybar re-runs it every second via interval:1):
Discord icon while the communication drawer (SUPER+K) is VISIBLE.
Ground truth = the Discord/equibop/vesktop client on special:communication
being `mapped` (windows unmap when the drawer hides, and activeworkspace does
NOT report the special ws on this Hyprland).
X11 twin: Discord mapped on desktop Sx (bspwm) or _NET_WM_DESKTOP == special-ish."""
import json
import os
import subprocess
import sys

IS_X11 = (not os.environ.get("WAYLAND_DISPLAY")) and os.environ.get("DISPLAY")

if IS_X11:
    # bspwm: desktop named Sx
    shown = False
    try:
        out = subprocess.run(
            ["bspc", "query", "-T", "-d", "Sx"],
            capture_output=True, text=True, timeout=3,
        ).stdout
        dsk = json.loads(out)
        for n in dsk.get("clients", []) + dsk.get("monitors", []):
            pass
        # clients live under nodes; simpler: query nodes on Sx
        nodes = subprocess.run(
            ["bspc", "query", "-N", "-n", "Sx.local"],
            capture_output=True, text=True, timeout=3,
        ).stdout.split()
        if nodes:
            # check class of first node
            info = subprocess.run(
                ["bspc", "query", "-T", "-n", nodes[0]],
                capture_output=True, text=True, timeout=3,
            ).stdout
            cls = (json.loads(info).get("node", {}) or {}).get("className", "").lower()
            if any(x in cls for x in ("discord", "equibop", "vesktop")):
                shown = True
    except Exception:
        shown = False
    if shown:
        print('{"text":"\\uf1ff","class":"active","tooltip":"Discord"}')
    else:
        print('{"text":"","class":""}')
    sys.exit(0)

try:
    out = subprocess.run(
        ["hyprctl", "-j", "clients"],
        capture_output=True, text=True, timeout=3,
        env=os.environ,
    ).stdout
    clients = json.loads(out)
except Exception:
    clients = None

shown = False
if isinstance(clients, list):
    for w in clients:
        if not w.get("mapped", False):
            continue
        ws = (w.get("workspace") or {}).get("name", "")
        cls = str(w.get("class", "")).lower()
        if ws == "special:communication" and (
            "discord" in cls or "equibop" in cls or "vesktop" in cls
        ):
            shown = True
            break

if shown:
    print('{"text":"\\uf1ff","class":"active","tooltip":"Discord"}')
else:
    print('{"text":"","class":""}')