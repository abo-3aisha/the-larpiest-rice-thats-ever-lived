#!/usr/bin/env python3
# Shared helpers for the small glass widgets (clock/clockana/music/sys/miku).
import json
import os
import re
import subprocess
import sys

CFG = os.path.expanduser("~/.config/widgets/widgets.json")

TITLES = {
    "clock": "Widget Clock",
    "clockana": "Widget Clockana",
    "music": "Widget Music",
    "sys": "Widget Sys",
    "miku": "Widget Miku",
    "prayer": "Widget Prayer",
    "hijri": "Widget Hijri",
}


def load():
    try:
        return json.load(open(CFG)).get("widgets", {})
    except Exception:
        return {}


def entry(key):
    return load().get(key, {"enabled": False, "workspace": 1, "x": 0.5, "y": 0.5,
                            "w": 0.2, "h": 0.1, "scope": "workspace"})


def monitor_size():
    try:
        out = subprocess.run(["hyprctl", "-j", "monitors"], capture_output=True,
                             text=True).stdout
        mons = json.loads(out)
        for m in mons:
            if m.get("focused"):
                return m["width"], m["height"]
        m = mons[0]
        return m["width"], m["height"]
    except Exception:
        return 1920, 1080


def accent():
    try:
        t = open(os.path.expanduser("~/.config/hypr/theme.lua")).read()
        m = re.search(r'accent\s*=\s*"([0-9a-fA-F]{6})', t)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "d7cc00"


def one_instance(key):
    pidf = os.path.expanduser("~/.cache/widget-%s.pid" % key)
    try:
        if os.path.exists(pidf):
            old = int(open(pidf).read().strip())
            try:
                os.kill(old, 0)
                sys.exit(0)
            except ProcessLookupError:
                pass
        with open(pidf, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass
    return pidf


_BODY = """
window.wwin {
  background: rgba(13,13,17,0.55);
  border: 2px solid #%s;
  border-radius: 14px;
}
window.wwin label { color: #f1f1f3; }
"""


def mkwin(key, extra_css=""):
    """Create a glass widget window as a TRUE layer surface on the BOTTOM
    layer (above the wallpaper, BELOW every app window) so it never hides
    content you are working with. Anchored left+top at its x/y position,
    visible on every workspace. Keyboard interactions are disabled (they are
    passive desktop widgets)."""
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, Gtk

    e = entry(key)
    sw, sh = monitor_size()
    w, h = int(sw * e.get("w", 0.2)), int(sh * e.get("h", 0.1))
    if w < 80:
        w = 80
    if h < 30:
        h = 30
    scope = e.get("scope", "workspace")

    win = Gtk.Window()
    win.set_title(TITLES.get(key, key))
    win.set_decorated(False)
    win.set_app_paintable(True)
    try:
        scr = win.get_screen()
        vis = scr.get_rgba_visual()
        if vis:
            win.set_visual(vis)
    except Exception:
        pass
    win.set_skip_taskbar_hint(True)
    win.set_skip_pager_hint(True)
    win.set_resizable(False)
    win.set_accept_focus(False)
    win.set_can_focus(False)
    win.set_type_hint(Gdk.WindowTypeHint.UTILITY)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    win.add(box)

    a = accent()
    css = (_BODY % a) + extra_css
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    try:
        Gtk.StyleContext.add_provider_for_screen(win.get_screen(), provider, 800)
    except Exception:
        pass

    win.resize(w, h)

    try:
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import GtkLayerShell
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.LEFT, int(e.get("x", 0.5) * sw))
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, int(e.get("y", 0.5) * sh))
        GtkLayerShell.set_exclusive_zone(win, 0)
        GtkLayerShell.set_namespace(win, "widget-" + key)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.NONE)
    except Exception:
        pass

    return win, box