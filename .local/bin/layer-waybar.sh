#!/usr/bin/env bash
# waybar "workspaces" strip (custom, mirrors hyprland/workspaces look):
#   - every numbered workspace stays visible, exactly as before
#   - only the ACTIVE slot changes: while Discord is the focused app (or the
#     Discord layer/special workspace is visible) it shows the Discord icon
#     instead of that workspace's number; everything else is untouched.
exec 2>/dev/null

python3 - <<'PY'
import json, subprocess

def hy(cmd):
    try:
        return json.loads(subprocess.check_output(["hyprctl", "-j", cmd], text=True))
    except Exception:
        return None

wss = hy("workspaces") or []
active = hy("activeworkspace") or {}
active_id = active.get("id")
active_name = str(active.get("name", ""))

focused = ""
try:
    focused = str(hy("activewindow").get("class", ""))
except Exception:
    pass
focused = focused.lower()

layer_up = active_name.startswith("special:")   # Discord layer (special:DISCORD) visible
icon_here = layer_up or focused == "discord"

nums = sorted([w for w in wss if w.get("id", -1) >= 0], key=lambda w: w["id"])

FG = "#a6a9b0"      # normal number colors (matches style.css #workspaces button)
BG_A = "#fea97b"    # active chip
FG_A = "#111113"
GLYPH = "\uf1ff"    # fa-discord

parts = []
for w in nums:
    wid = w["id"]
    act = (wid == active_id)
    label = str(wid)
    if act and icon_here:
        label = GLYPH
        parts.append('<span foreground="%(fg)s" background="%(bg)s"> %(t)s </span>'
                     % {"fg": FG_A, "bg": BG_A, "t": label})
    elif act:
        parts.append('<span foreground="%(fg)s" background="%(bg)s"> %(t)s </span>'
                     % {"fg": FG_A, "bg": BG_A, "t": label})
    else:
        parts.append('<span foreground="%(fg)s"> %(t)s </span>'
                     % {"fg": FG, "t": label})

if layer_up and not any(True for w in nums if w["id"] == active_id):
    parts.insert(0,
        '<span foreground="%(fg)s" background="%(bg)s"> %(t)s </span>'
        % {"fg": FG_A, "bg": BG_A, "t": GLYPH})

if not parts:
    if icon_here:
        parts.append('<span foreground="%s" background="%s"> %s </span>' % (FG_A, BG_A, GLYPH))
    else:
        parts.append("")

print(json.dumps({"text": "".join(parts), "class": "layer" if icon_here else ""}))
PY