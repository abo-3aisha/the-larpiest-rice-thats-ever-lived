#!/usr/bin/env python3
import argparse
import colorsys
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

FORCE_DARK = True  # keep the UI dark even on light wallpapers (user prefers dark)

HOME = str(Path.home())
HYPR_DIR = Path(HOME) / ".config" / "hypr"
HYPREPAPER = HYPR_DIR / "hyprpaper.conf"
OUT_LUA = HYPR_DIR / "theme.lua"
OUT_WAYBAR_CSS = Path(HOME) / ".config" / "waybar" / "style.css"
INCLUDE_WAYBAR_CUSTOM = Path(HOME) / ".config" / "waybar" / "style.custom.css"
OUT_SWAYNC_CSS = Path(HOME) / ".config" / "swaync" / "style.css"
OUT_WOFI_CSS = Path(HOME) / ".config" / "wofi" / "style.css"
FOOT_INI = Path(HOME) / ".config" / "foot" / "foot.ini"
FISH_COLORS = Path(HOME) / ".cache" / "wal" / "fish-colors.fish"
FASTFETCH = Path(HOME) / ".config" / "fastfetch" / "config.jsonc"
CAVA = Path(HOME) / ".config" / "cava" / "config"
WAL_CACHE = Path(HOME) / ".cache" / "wal" / "colors.json"

# Every color a user-facing app shows comes from ONE theme dict built by
# build_palette(). These constants can never appear in any output — if they
# ever do, the engine fails loudly (that was the old blue-revival bug).
FORBIDDEN = ("7aa2f7", "6068c8", "7A2F7", "6068C8")

FALLBACK_BG_DARK = (0x17, 0x17, 0x1A)
FALLBACK_BG_LIGHT = (0xF4, 0xF3, 0xF1)


def to_hex(rgb):
    return "%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def luma(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def hsl(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l


def blend(c1, c2, w1):
    w2 = 1 - w1
    return tuple(c1[i] * w1 + c2[i] * w2 for i in range(3))


def lighten(rgb, target=0.55):
    """Lift a dark accent toward the target lightness in HSL space WITHOUT
    touching saturation — dark red stays maroon instead of washing to pink,
    dark green stays green instead of going gray/white."""
    h, s, l = hsl(rgb)
    l2 = l + (target - l) * 0.85
    r, g, b = colorsys.hls_to_rgb(h, l2, s)
    return tuple(min(255, max(0, int(round(c * 255)))) for c in (r, g, b))


def contrast_text(rgb, dark=(0x11, 0x11, 0x13), light=(0xEF, 0xF1, 0xF4)):
    return dark if luma(rgb) > 0.6 else light


def current_wallpaper():
    # Wayland-native: ask hyprctl what wallpaper is ACTUALLY loaded (catches
    # `hyprctl hyprpaper` switches that never touch hyprpaper.conf).
    if shutil.which("hyprctl"):
        try:
            out = subprocess.run(
                ["hyprctl", "hyprpaper", "listactive"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            for line in out.splitlines():
                line = line.strip()
                if not line or "=" not in line or "," not in line:
                    continue
                path = line.split(",", 1)[1].strip().strip("'\"")
                if path not in ("none", "None", "", "-") and os.path.exists(path):
                    return path
        except Exception:
            pass
    if not HYPREPAPER.exists():
        return None
    text = HYPREPAPER.read_text(errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("wallpaper") and "=" not in line:
            continue
        if "wallpaper" not in line:
            continue
        parts = line.split("=", 1)
        if len(parts) != 2:
            continue
        value = parts[1].strip().strip("'\"")
        pieces = value.split(",", 1)
        path = pieces[1].strip() if len(pieces) > 1 else pieces[0].strip()
        if path in ("none", "None", "", "-"):
            continue
        return os.path.expanduser(path)
    return None


def decode_image(path):
    try:
        from PIL import Image

        img = Image.open(path).convert("RGB")
        img.thumbnail((96, 96))
        return list(img.getdata())
    except Exception:
        pass
    if shutil.which("ffmpeg"):
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=48:27",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, timeout=30,
        ).stdout
        return [(raw[i], raw[i + 1], raw[i + 2])
                for i in range(0, len(raw), 3) if i + 2 < len(raw)]
    return []


def cluster(pixels, n=6):
    buckets = [list(pixels)]
    while len(buckets) < n:
        spreads = []
        for b in buckets:
            ranges = [max(p[i] for p in b) - min(p[i] for p in b) for i in range(3)]
            spreads.append(max(ranges))
        idx = spreads.index(max(spreads))
        b = buckets[idx]
        if len(b) < 2:
            break
        channel = max(range(3), key=lambda i: max(p[i] for p in b) - min(p[i] for p in b))
        s = sorted(b, key=lambda p: p[channel])
        mid = len(s) // 2
        buckets[idx] = s[:mid]
        buckets.append(s[mid:])
    clusters = []
    for b in buckets:
        if not b:
            continue
        avg = tuple(sum(p[i] for p in b) // len(b) for i in range(3))
        clusters.append((len(b), avg))
    clusters.sort(reverse=True)
    total = sum(c for c, _ in clusters)
    return [(c / total, rgb) for c, rgb in clusters]


def vivid_accent(pixels):
    """DEPRECATED — kept for reference; real selection now goes through
    accent_from_wal / accent_from_clusters (hue-sensitive, never blue)."""
    hist = {}
    for rgb in pixels:
        h, s, l = hsl(rgb)
        if s >= 0.45 and 0.3 <= l <= 0.72:
            q = tuple(v & 0xF8 for v in rgb)
            hist[q] = hist.get(q, 0) + 1
    return None, []


def accent_from_pixels(pixels):
    """The accent comes from the REAL pixels, not wal's sometimes-boring averages.
    Because colorsys.hls saturations run LOWER than HSV for mid/dark tones, we
    search in tiers (0.30 → 0.22 → 0.15); a real photo-green/purple always finds
    a colored bucket, while truly achromatic (white/black/gray/silver) images stay
    white #dfdfdf. NEVER a stray blue."""
    buckets = {}
    for rgb in pixels:
        h, s, l = hsl(rgb)
        if 0.08 <= l <= 0.96:
            b = int(h * 8) % 8
            buckets.setdefault(b, []).append((s, l, rgb))
    for thr in (0.30, 0.22, 0.15):
        eligible = {b: (n, mx) for b, v in buckets.items()
                    if (n := len(v)) and (mx := max(x[0] for x in v)) >= thr}
        if not eligible:
            continue
        # Dominant vivid hue = biggest (count x saturation), so dark-but-flooding
        # tones don't win over a smaller vivid zone, and vice versa.
        dom_b = max(eligible, key=lambda b: eligible[b][0] * eligible[b][1])
        dom = buckets[dom_b]
        cands = [x for x in dom if x[0] >= thr]
        accent = max(cands, key=lambda x: x[0] * 0.5 + 0.5 * (1 - abs(x[1] - 0.55)))[2]
        accent2 = None
        for b, v in buckets.items():
            if b == dom_b:
                continue
            cand = max(v, key=lambda x: x[0])
            if accent2 is None or cand[0] > accent2[0]:
                accent2 = cand
        accent2 = accent2[2] if accent2 else accent
        if luma(accent) < 0.22:
            accent = lighten(accent)
        return accent, accent2
    return (0xDF, 0xDF, 0xDF), (0xDF, 0xDF, 0xDF)


def accent_from_clusters(clusters):
    """SAME hue-sensitive rule used by the wal path: pick the MOST SATURATED
    cluster (green wallpaper -> green, red -> red); if everything is
    achromatic (white/BW wallpaper) -> light neutral, NEVER a stray blue."""
    cand = sorted(((hsl(rgb)[1], hsl(rgb)[2], rgb) for _, rgb in clusters), reverse=True)
    sat, lum, accent = cand[0]
    if sat < 0.25:
        accent = (0xDF, 0xDF, 0xDF)
        accent2 = accent
    else:
        accent2 = cand[1][2]
        if luma(accent) < 0.18:
            accent = blend(accent, (0xEF, 0xF1, 0xF4), 0.55)
    return accent, accent2


def build_palette_from_pixels(pixels):
    clusters = cluster(pixels)
    mean_l = sum(w * luma(rgb) for w, rgb in clusters)
    mode = "dark" if (FORCE_DARK or mean_l < 0.5) else "light"

    accent, accent2 = accent_from_pixels(pixels)

    neutrals = sorted((c for c in clusters if hsl(c[1])[1] < 0.16), reverse=True)

    if mode == "dark":
        usable = [c for c in neutrals if 0.02 < luma(c[1]) < 0.28]
        bg = (usable[0][1] if usable else FALLBACK_BG_DARK)
        surface = blend(bg, (0xFF, 0xFF, 0xFF), 0.92)
        fg = (0xEF, 0xF1, 0xF4)
        fg_dim = (0xA6, 0xA9, 0xB0)
    else:
        usable = [c for c in neutrals if 0.7 < luma(c[1]) < 0.97]
        bg = (usable[0][1] if usable else FALLBACK_BG_LIGHT)
        surface = blend(bg, (0x00, 0x00, 0x00), 0.92)
        fg = (0x1D, 0x1D, 0x1F)
        fg_dim = (0x66, 0x66, 0x6B)

    on_accent = contrast_text(accent)
    border_active = accent
    border_inactive = blend(accent, bg, 0.35)
    shadow = blend(accent, (0x00, 0x00, 0x00), 0.25)

    return {
        "mode": mode,
        "bg": to_hex(bg),
        "surface": to_hex(surface),
        "fg": to_hex(fg),
        "fg_dim": to_hex(fg_dim),
        "accent": to_hex(accent),
        "accent2": to_hex(accent2),
        "on_accent": to_hex(on_accent),
        "border_active": to_hex(border_active),
        "border_inactive": to_hex(border_inactive),
        "shadow": to_hex(shadow),
        "error": "e5484d",
        "success": "2f9e44",
        "warning": "f08c00",
    }


def wal_rgb(hex6):
    h = str(hex6).lstrip("#")
    if len(h) != 6:
        raise ValueError(hex6)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def accent_from_wal(colors):
    """Pick the MOST SATURATED wal hue so the accent follows the wallpaper:
    green wallpaper -> green accent, red -> red, and an achromatic (white/BW)
    wallpaper -> light neutral instead of a random blue."""
    scored = []
    for i in list(range(1, 7)) + list(range(9, 15)):
        key = "color%d" % i
        if key not in colors:
            continue
        rgb = wal_rgb(colors[key])
        _, s, l = hsl(rgb)
        scored.append((s, l, rgb))
    scored.sort(reverse=True)
    sat, lum, accent = scored[0]
    if sat < 0.25:                            # no dominant hue -> neutral white
        accent = wal_rgb(colors.get("color7", "#e4cbcf"))
        accent2 = accent
    else:
        accent2 = scored[1][2]
        if luma(accent) < 0.18:               # too dark for the UI -> lift a bit
            accent = blend(accent, (0xEF, 0xF1, 0xF4), 0.55)
    return accent, accent2


def build_palette_from_wal(wallpaper):
    """Use pywal's cache (same source as the terminal) so waybar/swaync/wofi
    match the terminal exactly. Falls back to pixel extraction if wal has no cache."""
    try:
        data = json.load(open(Path(HOME) / ".cache" / "wal" / "colors.json"))
    except Exception:
        return None
    c = data.get("colors", {})
    sp = data.get("special", {})
    try:
        bg = wal_rgb(sp.get("background", "#0d0d0f"))
        fg = wal_rgb(sp.get("foreground", "#eff1f4"))
        surface0 = wal_rgb(c["color0"])
        accent, accent2 = accent_from_wal(c)
    except Exception:
        return None
    mode = "dark"
    surface = blend(surface0, (0xFF, 0xFF, 0xFF), 0.92)
    on_accent = contrast_text(tuple(accent))
    return {
        "mode": mode,
        "bg": to_hex(bg),
        "surface": to_hex(surface),
        "fg": to_hex(fg),
        "fg_dim": "a6a9b0",
        "accent": to_hex(accent),
        "accent2": to_hex(accent2),
        "on_accent": to_hex(on_accent),
        "border_active": to_hex(accent),
        "border_inactive": to_hex(blend(accent, bg, 0.35)),
        "shadow": to_hex(blend(accent, (0x00, 0x00, 0x00), 0.25)),
        "error": "e5484d",
        "success": "2f9e44",
        "warning": "f08c00",
        "_reg": [c["color%d" % i].lstrip("#") for i in range(8)],
        "_bri": [c["color%d" % i].lstrip("#") for i in range(8, 16)],
        "_bg_hex": sp.get("background", "#0d0d0f").lstrip("#"),
    }


def ensure_wal(wallpaper, force=False):
    """Make sure ~/.cache/wal belongs to the CURRENT wallpaper before we read
    it — otherwise a stale cache (e.g. from boot) tints waybar wrong. Only runs
    wal when the sidecar mismatches (or force), so the engine is the single
    owner of wal runs."""
    if not wallpaper or not os.path.exists(wallpaper) or not shutil.which("wal"):
        return
    need = force
    if not need:
        try:
            known = open(Path(HOME) / ".cache" / "wal" / "wallpaper").read().strip()
            need = known != wallpaper
        except Exception:
            need = True
    if need:
        try:
            subprocess.run(["wal", "-i", wallpaper, "-n", "-q"],
                           capture_output=True, timeout=60)
        except Exception:
            pass


def build_palette(wallpaper):
    ensure_wal(wallpaper)
    wal_theme = build_palette_from_wal(wallpaper)
    pixels = None
    try:
        pixels = decode_image(wallpaper)
    except Exception:
        pixels = None
    if pixels:
        accent, accent2 = accent_from_pixels(pixels)
        if wal_theme is not None:
            a = tuple(accent)
            bg = wal_rgb(wal_theme["bg"])
            wal_theme["accent"] = to_hex(a)
            wal_theme["accent2"] = to_hex(tuple(accent2))
            wal_theme["on_accent"] = to_hex(contrast_text(a))
            wal_theme["border_active"] = to_hex(a)
            wal_theme["border_inactive"] = to_hex(blend(a, bg, 0.35))
            wal_theme["shadow"] = to_hex(blend(a, (0x00, 0x00, 0x00), 0.25))
            wal_theme["wallpaper"] = wallpaper
            return wal_theme
        theme = build_palette_from_pixels(pixels)
        theme["wallpaper"] = wallpaper
        return theme
    if wal_theme is not None:
        wal_theme["wallpaper"] = wallpaper
        return wal_theme
    theme = build_palette_from_pixels([(0x0D, 0x0D, 0x0F), (0xEF, 0xF1, 0xF4)])
    theme["wallpaper"] = wallpaper
    return theme


THEME_LUA = """THEME = {{
    mode          = "{mode}",
    bg            = "{bg}",
    surface       = "{surface}",
    fg            = "{fg}",
    fg_dim        = "{fg_dim}",
    accent        = "{accent}",
    accent2       = "{accent2}",
    on_accent     = "{on_accent}",
    border_active = "{border_active}",
    border_inactive = "{border_inactive}",
    shadow        = "{shadow}",
}}
"""

WAYBAR_CSS = """* {{
    font-family: "JetBrainsMono Nerd Font", "Symbols Nerd Font Mono", monospace;
    font-size: 16px;
    min-height: 0;
    border: none;
    border-radius: 0;
    box-shadow: none;
    text-shadow: none;
}}

window#waybar {{
    background: transparent;
    color: #{fg};
}}

window#waybar.hidden {{ opacity: 0.0; }}

window#waybar.termite {{ padding: 0; }}

window#waybar.empty #window {{ background: none; }}

/* ===== pill containers (liquid glass) ===== */
.modules-left,
.modules-center,
.modules-right {{
    background: {glass};
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 18px;
    margin-top: 8px;
    margin-bottom: 6px;
    padding: 2px 8px;
    box-shadow: 0 0 0 1px rgba(0,0,0,0.08), 0 6px 18px rgba(0,0,0,0.12);
}}
.modules-left:hover,
.modules-center:hover,
.modules-right:hover {{ background: {glass_hover}; }}
.modules-left {{ margin-left: 10px; }}
.modules-right {{ margin-right: 10px; }}

/* ===== logo ===== */
#custom-logo {{
    font-size: 20px;
    padding: 0 10px 0 8px;
    color: #{accent};
}}

/* ===== workspaces ===== */
#workspaces button {{
    padding: 0 6px;
    margin: 0 1px;
    color: #{fg_dim};
    border-radius: 12px;
}}
#workspaces button.active {{
    background: #{accent};
    color: #{on_accent};
}}
#workspaces button:hover {{
    background: #{surface};
    color: #{accent};
    border: 1px solid #{accent};
}}

/* ===== generic modules ===== */
#clock, #custom-language, #network, #bluetooth, #pulseaudio, #battery,
#cpu, #memory, #temperature, #tray, #custom-power, #custom-weather, #idle_inhibitor {{
    padding: 0 9px;
    margin: 1px 2px;
    border-radius: 12px;
    color: #{fg};
}}

#clock {{
    font-weight: bold;
    color: #{fg};
}}
#clock:hover {{ color: #{accent}; }}

#custom-language {{
    background: #{accent};
    color: #{on_accent};
    border-radius: 12px;
    padding: 0 9px;
    margin: 1px 2px;
}}

#network, #bluetooth, #pulseaudio, #battery, #cpu, #memory, #temperature {{
    color: #{fg_dim};
}}
#network:hover, #bluetooth:hover, #pulseaudio:hover, #battery:hover,
#cpu:hover, #memory:hover, #temperature:hover {{ color: #{accent}; }}

#battery.warning {{ color: #{warning}; }}
#battery.critical {{ color: #{error}; }}
#temperature.critical {{ color: #{error}; }}

#custom-power {{
    font-size: 19px;
    color: #{fg_dim};
}}
#custom-power:hover {{ color: #{error}; }}

#tray > .passive {{
    color: #{fg_dim};
}}
#tray > .active {{
    color: #{fg};
}}
#tray > .needs-attention {{
    background: #{error};
    color: #{on_accent};
}}

/* ===== tooltip ===== */
tooltip {{
    background: #{bg};
    border: 1px solid #{accent};
    border-radius: 12px;
    color: #{fg};
}}
tooltip label {{
    color: #{fg};
    font-size: 15px;
}}
"""

SWAYNC_CSS = """* {{
    font-family: "JetBrainsMono Nerd Font", "Symbols Nerd Font Mono", monospace;
}}

.control-center {{
    background: {cc_bg};
    border: 1px solid #{accent}44;
    border-radius: 18px;
}}

.notification-window {{
    background: #{bg};
    border: 1px solid #{accent}44;
    border-radius: 18px;
}}

.widget-title {{
    color: #{fg};
}}
.widget-title > button {{
    background: #{surface};
    color: #{fg};
    border-radius: 10px;
}}

.notification-row {{
    outline: none;
}}

.notification {{
    background: #{surface};
    border-radius: 14px;
    padding: 8px 12px;
    color: #{fg};
}}

.notification-content {{
    background: #{surface};
    color: #{fg};
}}

.notification-default-action, .notification-action {{
    background: #{bg};
    color: #{fg};
    border-radius: 8px;
}}

.notification-default-action:hover, .notification-action:hover {{
    background: #{accent};
    color: #{on_accent};
}}

.notification-body {{
    color: #{fg_dim};
}}

.notification-title {{
    color: #{fg};
    font-weight: bold;
}}

.close-button {{
    background: #{error};
    color: #{on_accent};
    border-radius: 50%;
}}

#dnd {{
    color: #{accent};
}}
#dnd > button {{
    background: #{surface};
    color: #{accent};
    border-radius: 10px;
}}

.parameter-value {{
    color: #{accent};
}}

/* --- Control-center tiles (Android-style quick settings) --- */
/* --- Quick toggles (menubar buttons#quick -> css class "quick") --- */
 .widget-menubar {{
     margin: 4px 0;
     background: transparent;
 }}
 .quick button {{
     background: #{accent}40;
     color: #{accent};
     border: 2px solid transparent;
     border-top: 2px solid #{accent}88;
     border-bottom: 2px solid #{accent}2E;
     border-radius: 18px;
     font-weight: bold;
     padding: 12px 14px;
 }}
 .quick button label {{
     color: #{accent};
 }}
 .quick button:hover {{
     border: 2px solid #{accent};
     background: #{accent}55;
 }}
 .quick button:active {{
     background: #{accent}66;
 }}
 /* A toggle tile that is ON gets the .active class and is filled with the wallpaper accent (like Android) */
 .quick button.active {{
     background: #{accent};
     color: #{on_accent};
     border: 2px solid #{accent2};
 }}
 .quick button.active:hover {{
     border: 2px solid #{accent2};
     background: #{accent};
     opacity: 0.95;
 }}

/* --- Sliders (volume + mic) follow the wallpaper accent --- */
#volume trough, #brightness trough,
.widget-volume trough, .widget-backlight trough {{
    background: rgba(0, 0, 0, 0.28);
    border-radius: 999px;
    min-width: 6px;
    min-height: 6px;
}}
#volume highlight, #brightness highlight,
.widget-volume highlight, .widget-backlight highlight {{
    background: #{accent};
    border-radius: 999px;
    opacity: 0.92;
}}
#volume scale trough, #brightness scale trough,
#volume slider trough, #brightness slider trough,
.widget-volume scale trough, .widget-backlight scale trough,
.mic scale trough, #mic scale trough, .volume scale trough {{
    background: rgba(0, 0, 0, 0.28);
    border-radius: 999px;
    min-width: 6px;
    min-height: 6px;
}}
#volume scale trough highlight, #brightness scale trough highlight,
#volume slider trough highlight, #brightness slider trough highlight,
.widget-volume scale trough highlight, .widget-backlight scale trough highlight,
.mic scale trough highlight, #mic scale trough highlight, .volume scale trough highlight {{
    background: #{accent};
    border-radius: 999px;
    opacity: 0.92;
}}
#volume scale slider, #brightness scale slider,
#volume slider slider, #brightness slider slider,
.widget-volume scale slider, .widget-backlight scale slider,
.mic scale slider, #mic scale slider, .volume scale slider {{
    background: #{accent2};
    border: 2px solid #{accent};
    border-radius: 50%;
    min-width: 14px;
    min-height: 14px;
}}
"""

WOFI_CSS = """window {{
    background-color: rgba(20, 20, 23, 0.62);
    border-radius: 18px;
    border: 1px solid #{accent}66;
}}

#outer-box {{
    margin: 14px;
    border-radius: 14px;
}}

#input {{
    background-color: #2a2a30;
    color: #eff1f4;
    border: 1px solid #{accent}88;
    border-radius: 10px;
    padding: 8px 12px;
}}

#input:focus {{
    border-color: #{accent};
}}

#entry {{
    color: #eff1f4;
    border-radius: 10px;
}}

#entry:selected {{
    background-color: #{accent};
    color: #{on_accent};
}}

#scroll {{
    background: transparent;
}}

#text {{
    color: #d6dae2;
    margin: 4px 8px;
}}

#text:selected {{
    color: #{on_accent};
}}

#img {{
    margin: 4px 8px;
}}
"""

def read_wal():
    """Read the wal cache WITHOUT running wal (the engine runs wal itself,
    once, via ensure_wal). Returns (colors, special) or (None, None)."""
    try:
        data = json.loads(WAL_CACHE.read_text())
        return data.get("colors"), data.get("special")
    except Exception:
        return None, None


def diff_write(path, text):
    """Write only when the content actually changed, so downstream apps stop
    seeing pointless mtimes/rebuilds and nothing looks like a live zombie."""
    try:
        if path.read_text(errors="replace") == text:
            return False
    except Exception:
        pass
    ensure_dir(path)
    path.write_text(text)
    return True


def foot_sections(theme):
    reg = theme.get("_reg")
    bri = theme.get("_bri")
    if not reg or not bri:
        s = theme
        reg = [s["surface"], s["error"], s["success"], s["warning"],
               s["accent"], s["accent2"], s["accent"], s["fg"]]
        bri = reg
    # selection/url follow the THEME accent, not wal's arbitrary color5.
    sel, url = theme["accent"], theme["accent2"]
    body = "foreground=%s\nbackground=%s\n" % (theme["fg"], theme["bg"])
    body += "\n".join("regular%d=%s" % (i, reg[i]) for i in range(8)) + "\n"
    body += "\n".join("bright%d=%s" % (i, bri[i]) for i in range(8)) + "\n"
    body += "selection-foreground=%s\nselection-background=%s\nurls=%s\n" % (theme["fg"], sel, url)
    body = body.rstrip("\n")
    dark = "[colors-dark]\nalpha=0.78\nblur=yes\n" + body
    light = "[colors-light]\n" + body
    return dark + "\n\n" + light


def sync_foot(theme):
    if not FOOT_INI.exists():
        return
    text = FOOT_INI.read_text(errors="replace")
    text = re.sub(r"(?ms)^\[colors-dark\][^\n]*(?:\n(?!\[).*)*\n?", "", text)
    text = re.sub(r"(?ms)^\[colors-light\][^\n]*(?:\n(?!\[).*)*\n?", "", text)
    if "shell=" not in text and "font=" not in text:
        text = ("shell=fish\ntitle=foot\nfont=MesloLGS Nerd Font:size=14\n"
                "letter-spacing=0\ndpi-aware=no\npad=25x25\n"
                "bold-text-in-bright=no\ngamma-correct-blending=no\n\n"
                "[scrollback]\nlines=10000\n\n[cursor]\nstyle=beam\nbeam-thickness=1.5\n")
    text = text.rstrip("\n") + "\n" + foot_sections(theme)
    diff_write(FOOT_INI, text)


def write_fish_colors(theme):
    """fish colors: wal RAMPA for numbers, but every accent-ish binding uses
    the THEME accent so fish follows the wallpaper the same way waybar does."""
    c, _ = read_wal()
    if not c:
        c = {"color%d" % i: ("#" + theme["surface"]) for i in range(8)}
        c.update({"color%d" % i: ("#" + theme["accent"]) for i in range(8, 16)})
    a = theme["accent"]
    a2 = theme["accent2"]
    bg = theme["_bg_hex"] or theme["bg"]
    lines = [
        "set -g wal_fg '#%s'" % theme["fg"],
        "set -g wal_bg '#%s'" % bg,
    ]
    for i in range(16):
        lines.append("set -g wal_c%d '#%s'" % (i, c["color%d" % i].lstrip("#")))
    lines += [
        "set -g fish_color_normal '#%s'" % theme["fg"],
        "set -g fish_color_command '#%s'" % a,
        "set -g fish_color_param '#%s'" % a2,
        "set -g fish_color_error '#%s'" % theme["error"],
        "set -g fish_color_quote '#%s'" % a2,
        "set -g fish_color_redirection '#%s'" % a,
        "set -g fish_color_operator '#%s'" % a,
        "set -g fish_color_end '#%s'" % a,
        "set -g fish_color_cwd '#%s'" % a,
        "set -g fish_color_autosuggestion '#%s'" % (c.get("color8", "#8b8b99").lstrip("#")),
        "set -g fish_color_selection --background '#%s' --foreground '#%s'" % (a, bg),
        "set -g fish_pager_color_prefix '#%s'" % a,
        "set -g fish_pager_color_description '#%s'" % (c.get("color8", "#8b8b99").lstrip("#")),
        "set -g fish_pager_color_progress '#%s'" % a,
        "",
        "# Recolor THIS terminal session (any emulator); foot themes itself via foot.ini.",
        "if not string match -q -- '*foot*' \"$TERM\"",
        "    printf '\\e]10;%s\\a' $wal_fg",
        "    printf '\\e]11;%s\\a' $wal_bg",
        "    printf '\\e]17;%s\\a' $wal_c5",
        "    printf '\\e]19;%s\\a' $wal_bg",
    ]
    for i in range(16):
        lines.append("    printf '\\e]4;%d;%s\\a' $wal_c%d" % (i, "%s", i))
    lines.append("end")
    diff_write(FISH_COLORS, "\n".join(lines) + "\n")


def write_fastfetch(theme):
    def h(x):
        return "#" + x
    conf = {
        "logo": {
            "type": "builtin",
            "source": "arch",
            "color": {"1": h(theme["accent"]), "2": h(theme["accent2"]), "3": h(theme["accent"])},
        },
        "display": {"separator": "  ", "color": {"keys": h(theme["accent"])}},
        "modules": [
            "title", "separator", "os", "host", "kernel", "uptime", "packages",
            "shell", "resolution", "de", "wm", "terminal", "cpu", "gpu",
            "memory", "disk", "colors",
        ],
    }
    diff_write(FASTFETCH, json.dumps(conf, indent=4) + "\n")


def write_cava(theme):
    c, _ = read_wal()
    if not c:
        return
    bri = ["#" + c["color%d" % i].lstrip("#") for i in range(8, 16)]

    def grad(n):
        return "gradient_color_%d = '%s'" % (n, bri[n - 1])

    text = (
        "# Cava Audio Visualizer Configuration Template\n"
        "# Colors auto-synced with the wallpaper via palette.py\n\n"
        "[general]\nframerate = 144\n\n[input]\nmethod = pulse\nsource = auto\n\n"
        "[output]\nmethod = ncurses\nstyle = stereo\n\n[color]\n"
        "gradient = 1\ngradient_count = 8\n"
        + "\n".join(grad(i) for i in range(1, 9))
        + "\n\n[smoothing]\nnoise_reduction = 85\nmonstercat = 1\nwaves = 0\n"
        "gravity = 120\n\n[eq]\n1 = 0.8\n2 = 0.9\n3 = 1.0\n4 = 1.1\n5 = 1.2\n"
    )
    diff_write(CAVA, text)


def write_gtk_accent(theme):
    """GTK/Thunar accent = THEME accent (pixel-driven, same as waybar), so a
    white wallpaper gives white GTK and the 'blue comes back' in Thunar dies."""
    accent = "#" + theme["accent"]
    dark = "#" + theme["_bg_hex"] if theme.get("_bg_hex") else "#" + theme["bg"]
    for sub in ("gtk-3.0", "gtk-4.0"):
        gtk_css = Path(HOME) / ".config" / sub / "gtk.css"
        thunar_css = Path(HOME) / ".config" / sub / "thunar.css"
        try:
            text = gtk_css.read_text(errors="replace")
            text = re.sub(r"(?m)^@define-color accent_color .*$",
                          "@define-color accent_color " + accent + ";", text)
            text = re.sub(r"(?m)^@define-color accent_bg_color .*$",
                          "@define-color accent_bg_color " + accent + ";", text)
            text = re.sub(r"(?m)^@define-color accent_fg_color .*$",
                          "@define-color accent_fg_color " + dark + ";", text)
            diff_write(gtk_css, text)
        except Exception:
            pass
        try:
            text = thunar_css.read_text(errors="replace")
            text = text.replace("#9bd0d3", accent)
            diff_write(thunar_css, text)
        except Exception:
            pass


def ensure_dir(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def sync_qt_scheme(mode):
    scheme = "BreezeDarkOrange" if mode == "dark" else "BreezeLightOrange"
    accent = "233,100,58"  # keep the user's identity accent (orange) in both modes
    if shutil.which("plasma-apply-colorscheme"):
        try:
            subprocess.run(["plasma-apply-colorscheme", scheme], capture_output=True)
        except Exception:
            pass
    if shutil.which("kwriteconfig6"):
        try:
            subprocess.run(
                ["kwriteconfig6", "--file", "kdeglobals", "--group", "KDE", "--key", "ColorScheme", scheme],
                capture_output=True,
            )
            subprocess.run(
                ["kwriteconfig6", "--file", "kdeglobals", "--group", "General", "--key", "AccentColor", accent],
                capture_output=True,
            )
        except Exception:
            pass
    sync_gtk_scheme(mode)


def sync_gtk_scheme(mode):
    if not shutil.which("gsettings"):
        return
    gtk = "Breeze-Dark" if mode == "dark" else "Breeze"
    color = "prefer-dark" if mode == "dark" else "prefer-light"
    for cmd in (
        ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", gtk],
        ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", color],
    ):
        try:
            subprocess.run(cmd, capture_output=True)
        except Exception:
            pass


def rgba_from(hex6, alpha):
    try:
        r = int(hex6[0:2], 16)
        g = int(hex6[2:4], 16)
        b = int(hex6[4:6], 16)
        return "rgba(%d, %d, %d, %s)" % (r, g, b, alpha)
    except Exception:
        return "rgba(42, 42, 44, %s)" % alpha


def generate(theme):
    ensure_dir(OUT_LUA)
    diff_write(OUT_LUA, THEME_LUA.format(**theme))
    theme = dict(theme)
    theme["glass"] = rgba_from(theme["surface"], "0.40")
    theme["glass_hover"] = rgba_from(theme["surface"], "0.55")
    theme["cc_bg"] = rgba_from(theme["bg"], "0.80")  # solid-ish control-center (no panel blur)
    ensure_dir(OUT_WAYBAR_CSS)
    css = WAYBAR_CSS.format(**theme) + "\n"
    if INCLUDE_WAYBAR_CUSTOM.exists():
        custom = INCLUDE_WAYBAR_CUSTOM.read_text()
        for k, v in theme.items():
            if isinstance(v, str):
                custom = custom.replace("@" + k + "@", "#" + v)
        css += custom + "\n"
    diff_write(OUT_WAYBAR_CSS, css)
    ensure_dir(OUT_SWAYNC_CSS)
    diff_write(OUT_SWAYNC_CSS, SWAYNC_CSS.format(**theme))
    ensure_dir(OUT_WOFI_CSS)
    diff_write(OUT_WOFI_CSS, WOFI_CSS.format(**theme))
    sync_foot(theme)
    write_fish_colors(theme)
    write_fastfetch(theme)
    write_cava(theme)
    write_gtk_accent(theme)
    sync_qt_scheme(theme["mode"])
    forbidden_hit = []
    for path in (OUT_LUA, OUT_WAYBAR_CSS, OUT_SWAYNC_CSS, OUT_WOFI_CSS, FOOT_INI, FISH_COLORS, FASTFETCH, CAVA):
        try:
            text = path.read_text(errors="replace").lower()
        except Exception:
            continue
        for bad in FORBIDDEN:
            if bad.lower() in text:
                forbidden_hit.append((str(path), bad))
    if forbidden_hit:
        print("[palette] WARNING forbidden colors written: %r" % forbidden_hit, flush=True)
        for path, bad in forbidden_hit:
            txt = Path(path).read_text(errors="replace")
            Path(path).write_text(txt.replace(bad, theme["accent"]))
        print("[palette] replaced with accent %s" % theme["accent"], flush=True)


def reload():
    if shutil.which("hyprctl"):
        subprocess.run(["hyprctl", "reload"], capture_output=True)
    if shutil.which("swaync-client"):
        subprocess.run(["swaync-client", "-R"], capture_output=True)
        subprocess.run(["swaync-client", "-rs"], capture_output=True)  # style must reload too
    if shutil.which("waybar") and subprocess.run(["pgrep", "-x", "waybar"], capture_output=True).returncode == 0:
        subprocess.run(["pkill", "-x", "waybar"], capture_output=True)
        subprocess.Popen(["setsid", "waybar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def apply(wallpaper, do_reload):
    theme = build_palette(wallpaper)
    generate(theme)
    if do_reload:
        reload()
    return theme


def watch_loop():
    last = None
    last_wall = None
    last_accent = None
    while True:
        if HYPREPAPER.exists():
            stamp = HYPREPAPER.stat().st_mtime
            wall = current_wallpaper()
            if stamp != last or wall != last_wall:
                last = stamp
                last_wall = wall
                if wall and os.path.exists(wall):
                    try:
                        theme = apply(wall, False)
                        # Reload the DE only when the accent actually changed;
                        # otherwise identical re-fires (boot, calls) stay quiet.
                        if theme["accent"] != last_accent:
                            last_accent = theme["accent"]
                            reload()
                        print("[palette] %s %s %s" % (theme["mode"], wall, theme["accent"]), flush=True)
                    except Exception as exc:
                        print("[palette] error %r" % exc, flush=True)
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--print", action="store_true")
    parser.add_argument("--wall", default=None)
    parser.add_argument("--default-mode", choices=("dark", "auto"), default="dark",
                        help="dark = always dark; auto = follow wallpaper brightness")
    args = parser.parse_args()

    if args.default_mode == "auto":
        global FORCE_DARK
        FORCE_DARK = False

    if args.watch:
        watch_loop()
        return

    wall = args.wall or current_wallpaper()
    if not wall:
        print("no wallpaper found in %s" % HYPREPAPER)
        sys.exit(1)
    if not os.path.exists(wall):
        print("wallpaper missing: %s" % wall)
        sys.exit(1)

    try:
        theme = apply(wall, args.apply)
    except Exception as exc:
        print("error: %r" % exc)
        sys.exit(1)

    if args.print or not args.apply:
        for key in ("mode", "bg", "surface", "fg", "fg_dim", "accent", "accent2", "on_accent",
                    "border_active", "border_inactive", "shadow"):
            print("%-15s #%s" % (key, theme[key]))
        print("wallpaper: %s" % wall)


if __name__ == "__main__":
    main()