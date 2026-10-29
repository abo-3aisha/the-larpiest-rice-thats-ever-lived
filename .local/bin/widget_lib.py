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
    "clockday": "Widget Clockday",
    "frame": "Widget Frame",
    "dino": "Widget Dino",
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


# ----------------------------------------------------------- animations --
_TRANS = None  # lazy Gtk.StackTransitionType table


def _tt(name):
    global _TRANS
    if _TRANS is None:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        _TRANS = {
            "fade": Gtk.StackTransitionType.CROSSFADE,
            "slide-up": Gtk.StackTransitionType.SLIDE_UP_DOWN,
            "slide-left": Gtk.StackTransitionType.SLIDE_LEFT,
            "slide-right": Gtk.StackTransitionType.SLIDE_RIGHT,
            "slide-down": Gtk.StackTransitionType.SLIDE_DOWN,
        }
    return _TRANS.get(name, _TRANS["fade"])


def make_flip(box, css_name, text="", ttype="slide-up", dur=320, pack=True,
              halign="center", width=None, ellipsize=False):
    """Two-label Gtk.Stack: flip_set() swaps them with a smooth transition.
    GTK paces Stack transitions on the frame clock, so text rolls/fades are
    vsync-smooth with zero animation code in the widgets."""
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    st = Gtk.Stack()
    st.set_transition_type(_tt(ttype))
    st.set_transition_duration(dur)
    st.set_halign(Gtk.Align.CENTER if halign == "center" else Gtk.Align.START)
    for nm in ("f0", "f1"):
        lb = Gtk.Label(label=text)
        lb.set_name(css_name)
        if halign != "center":
            lb.set_halign(Gtk.Align.START)
        if width:
            lb.set_size_request(width, -1)
        if ellipsize:
            lb.set_ellipsize(3)  # Pango.EllipsizeMode.END
        st.add_named(lb, nm)
    st.set_visible_child_name("f0")
    st._flip_cur = "f0"
    st._flip_txt = text
    if pack:
        box.pack_start(st, True, True, 0)
    return st


def flip_set(st, text):
    """Update a make_flip stack; animates only when the text really changed."""
    if text == getattr(st, "_flip_txt", None):
        return
    st._flip_txt = text
    nxt = "f1" if st._flip_cur == "f0" else "f0"
    cur_lb = st.get_child_by_name(st._flip_cur)
    nxt_lb = st.get_child_by_name(nxt)
    if nxt_lb is None:
        return
    nxt_lb.set_text(text)
    if not st.get_mapped():
        # A visible-child switch made BEFORE the window is mapped can get
        # dropped by GTK (the stack then shows the stale child forever —
        # that was the prayer/hijri "..."). Keep both children identical
        # so the first paint is correct; transitions start from the next
        # change once the widget is on screen.
        if cur_lb is not None:
            cur_lb.set_text(text)
        return
    st.set_visible_child_name(nxt)
    st._flip_cur = nxt


def ease_out(p):
    """Cubic ease-out 0..1 (fast start, gentle settle)."""
    p = max(0.0, min(1.0, p))
    return 1.0 - (1.0 - p) ** 3


_BODY = """
window.wwin {
  background: rgba(13,13,17,0.55);
  background-image: linear-gradient(to bottom, rgba(255,255,255,0.09), rgba(255,255,255,0.0) 32%%);
  border: 2px solid #%s;
  border-radius: 14px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 8px 22px rgba(0,0,0,0.30);
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

    is_x11 = (not os.environ.get("WAYLAND_DISPLAY")) and os.environ.get("DISPLAY")
    placed = False
    if not is_x11:
        try:
            gi.require_version("GtkLayerShell", "0.1")
            from gi.repository import GtkLayerShell
            GtkLayerShell.init_for_window(win)
            GtkLayerShell.set_layer(win, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_margin(win, GtkLayerShell.Edge.LEFT, int(e.get("x", 0.5) * sw))
            GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, int(e.get("y", 0.5) * sh))
            # -1 = anchor to the RAW output edges. 0/positive makes the compositor
            # keep the surface out of other surfaces' exclusive zones — Hyprland
            # then pushes every widget below waybar's zone (+58px) and the screen
            # never matched the manager preview. -1 = WYSIWYG with the preview.
            GtkLayerShell.set_exclusive_zone(win, -1)
            GtkLayerShell.set_namespace(win, "widget-" + key)
            GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.NONE)
            placed = True
        except Exception:
            placed = False

    if not placed:
        # X11 twin: no layer-shell — stick to all desktops, keep below apps,
        # and park the top-left at the configured fraction of the screen.
        try:
            win.stick()
        except Exception:
            pass
        try:
            win.set_keep_below(True)
        except Exception:
            pass
        try:
            win.set_type_hint(Gdk.WindowTypeHint.DOCK)
        except Exception:
            pass

        def _place(*_a):
            try:
                win.move(int(e.get("x", 0.5) * sw), int(e.get("y", 0.5) * sh))
            except Exception:
                pass
            return False

        try:
            from gi.repository import GLib
            win.connect("realize", lambda *_: GLib.idle_add(_place))
            GLib.idle_add(_place)
        except Exception:
            pass

    return win, box