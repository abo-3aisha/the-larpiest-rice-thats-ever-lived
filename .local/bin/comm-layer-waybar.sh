#!/usr/bin/env python3
"""waybar module (one-shot, waybar re-runs it every second via interval:1):
Discord icon while the communication drawer (SUPER+K) is VISIBLE.
Ground truth = the Discord/equibop/vesktop client on special:communication
being `mapped` (windows unmap when the drawer hides, and activeworkspace does
NOT report the special ws on this Hyprland)."""
import json
import os
import subprocess

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