#!/usr/bin/env python3
# vol-bar.py - slim drop-down audio bar (GTK3): VOL + MIC sliders, mute each,
# headphones/speakers switch. Smooth slide-down (GtkRevealer). Closes on ESC,
# focus-out, or ~8s idle. Running again toggles it closed.
import gi, os, re, subprocess, sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

HOME = os.path.expanduser("~")
PROC = "vol-bar.py"

# Toggle: if another instance is open, close it and quit.
try:
    out = subprocess.run(["pgrep", "-f", PROC], capture_output=True, text=True).stdout.split()
    me = str(os.getpid())
    out = [p for p in out if p != me]
    if out:
        subprocess.run(["pkill", "-f", PROC])
        sys.exit(0)
except Exception:
    pass


def wpctl(args):
    try:
        return subprocess.run(["wpctl"] + args, capture_output=True, text=True).stdout
    except Exception:
        return ""


def accent_hex():
    try:
        css = open(os.path.join(HOME, ".config", "swaync", "style.css")).read()
        m = re.search(r"\.quick button\.active \{\s*background:\s*#([0-9a-fA-F]{6})", css)
        if not m:
            m = re.search(r"\.quick button \{\s*background:\s*#([0-9a-fA-F]{6})", css)
        return ("#" + m.group(1)) if m else "#f8ac21"
    except Exception:
        return "#f8ac21"


ACCENT = accent_hex()


def initial_pct(tag):
    if tag == "VOL":
        return pct("@DEFAULT_AUDIO_SINK@")
    try:
        out = subprocess.run([os.path.join(HOME, ".local", "bin", "mic-vol"), "get"],
                             capture_output=True, text=True).stdout.strip()
        if out and out.isdigit():
            return max(0, min(100, int(out)))
    except Exception:
        pass
    return 0


def pct(target):
    out = wpctl(["get-volume", target])
    if not out or len(out.split()) < 2:
        return 0
    try:
        return max(0, min(100, round(float(out.split()[1]) * 100)))
    except ValueError:
        return 0


def muted(target):
    return "MUTED" in wpctl(["get-volume", target])


def set_vol(v):
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "%d%%" % int(v)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def set_mic(v):
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", "%d%%" % int(v)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mute(target, on):
    subprocess.run(["wpctl", "set-mute", target, "1" if on else "0"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sink_id():
    out = wpctl(["status"])
    if not out:
        return ""
    in_sinks = False
    for line in out.splitlines():
        if "Sinks:" in line:
            in_sinks = True
            continue
        if in_sinks:
            if "Sources:" in line:
                break
            m = re.search(r"\*\s*(\d+)\.\s+(?:\"([^\"]+)\"|\S+)", line)
            if m:
                return m.group(1)
    return ""


def port_state(node):
    out = wpctl(["inspect", node])
    if not out:
        return [], ""
    ports = re.findall(r"\[port\][^\n]*?\bname:\s*(\S+)", out)
    if not ports:
        ports = list(dict.fromkeys(re.findall(r"available port:\s*(\S+)", out)))
    ac = re.search(r"active port:\s*(\S+)", out)
    return ports, (ac.group(1) if ac else "")


def alsa_speaker_route(to_spk):
    for c in range(0, 4):
        out = subprocess.run(["amixer", "-c", str(c), "scontrols"],
                             capture_output=True, text=True).stdout
        if not out:
            continue
        if "Auto-Mute Mode" in out:
            subprocess.call(["amixer", "-c", str(c), "set", "Auto-Mute Mode",
                             "Disabled" if to_spk else "Enabled"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if "'Speaker'" in out:
            subprocess.call(["amixer", "-c", str(c), "set", "Speaker",
                             "unmute" if to_spk else "mute"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pactl_default_sink():
    try:
        out = subprocess.run(["pactl", "info"], capture_output=True, text=True).stdout
        m = re.search(r"Default Sink:\s*(\S+)", out)
        return m.group(1) if m else ""
    except Exception:
        return ""


def pactl_default_source():
    try:
        out = subprocess.run(["pactl", "info"], capture_output=True, text=True).stdout
        m = re.search(r"Default Source:\s*(\S+)", out)
        return m.group(1) if m else ""
    except Exception:
        return ""


def native_default_ok(key, name):
    out = subprocess.run(["pw-metadata", "-n", "default"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if key in line and name in line:
            return True
    return False


def ensure_default():
    for key, name in (("default.audio.sink", pactl_default_sink()),
                      ("default.audio.source", pactl_default_source())):
        if name and not native_default_ok(key, name):
            subprocess.call(["pw-metadata", "-n", "default", "0", key,
                             '{ "name": "%s" }' % name, "Spa:String:JSON"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pactl_ports(sink):
    try:
        out = subprocess.run(["pactl", "list", "sinks"], capture_output=True, text=True).stdout
    except Exception:
        return [], ""
    for block in out.split("Sink #")[1:]:
        m = re.search(r"\n\tName: (\S+)", block)
        if m and m.group(1) == sink:
            ports = re.findall(r"^\t+(analog-output-[a-z-]+):", block, re.M)
            am = re.search(r"\n\tActive Port: (\S+)", block)
            return ports, (am.group(1) if am else "")
    return [], ""


def active_port():
    return port_state(sink_id())[1]


def port_label():
    return "Speakers" if "headphone" not in active_port() else "Headphones"


def switch_output():
    sink = pactl_default_sink()
    node = ""
    ports, active = pactl_ports(sink) if sink else ([], "")
    used = "pactl"
    if not ports:
        node = sink_id()
        ports, active = port_state(node)
        used = "wpctl"
        if not ports:
            notify("Output", "no switchable ports (pactl/wiports empty)")
            return
    cand = [p for p in ports if p.startswith("analog-output-")]
    cand = cand or ports
    if len(cand) < 2:
        notify("Output", "only one output available (%s)" % ",".join(cand))
        return
    target = cand[0] if cand[0] != active else cand[1]
    ok = subprocess.call(["pactl", "set-sink-port", sink, target],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _, new_active = pactl_ports(sink) if sink else ([], "")
    done = new_active == target
    if not done and used == "wpctl":
        ok2 = subprocess.call(["wpctl", "set-port", sink_id(), target],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ok2 == 0:
            done, ok = True, 0
    if done or ok == 0:
        to_spk = "headphone" not in target
        alsa_speaker_route(to_spk)
        ensure_default()
        if muted("@DEFAULT_AUDIO_SINK@"):
            mute("@DEFAULT_AUDIO_SINK@", False)
        if pct("@DEFAULT_AUDIO_SINK@") <= 2:
            set_vol(60)
        outp_lbl.set_text("Headphones" if "headphone" in target else "Speakers")
        notify("Output", "Switched to %s" % ("Headphones" if "headphone" in target else "Speakers"))
    else:
        notify("Output", "could not switch (sink=%s node=%s ports=%s active=%s want=%s)"
               % (sink, node, ",".join(cand), active, target))


def notify(title, msg):
    subprocess.Popen(["notify-send", title, msg],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def on_vol_change(sl):
    set_vol(sl.get_value())
    vol_pct.set_text("VOL %d%%" % int(sl.get_value()))


def on_mic_change(sl):
    set_mic(sl.get_value())
    mic_pct.set_text("MIC %d%%" % int(sl.get_value()))


rev = None


def do_close(*_):
    rev.set_reveal_child(False)
    GLib.timeout_add(250, Gtk.main_quit)


win = Gtk.Window()
win.set_decorated(False)
win.set_skip_taskbar_hint(True)
win.set_skip_pager_hint(True)
win.set_keep_above(True)
win.set_app_paintable(True)
screen = win.get_screen()
if screen.get_rgba_visual():
    win.set_visual(screen.get_rgba_visual())

css = ("""
#volbar { background-color: rgba(16,18,22,0.92); border-radius: 16px;
          border: 1px solid rgba(255,255,255,0.10); }
.lbl { color: %s; font-weight: bold; font-size: 13px; }
.pct { color: %s; font-size: 12px; font-weight: bold; }
scale trough { background-color: rgba(255,255,255,0.14); min-height: 6px; border-radius: 3px; }
scale highlight { background-color: %s; border-radius: 3px; }
scale slider { background-color: #f2e9d0; border-radius: 8px; min-width: 6px; min-height: 16px; }
button { background-color: rgba(255,255,255,0.08); border-radius: 10px; color: %s;
         border: 1px solid rgba(255,255,255,0.10); font-size: 12px; font-weight: bold; }
button:hover { background-color: rgba(255,255,255,0.16); }
button:checked { background-color: %s; color: #0d0d0f; }
""" % (ACCENT, ACCENT, ACCENT, ACCENT, ACCENT))
provider = Gtk.CssProvider()
provider.load_from_data(css.encode())
Gtk.StyleContext.add_provider_for_screen(screen, provider,
                                         Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

rev = Gtk.Revealer()
rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
rev.set_transition_duration(260)
win.add(rev)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
box.set_margin_start(14); box.set_margin_end(14)
box.set_margin_top(12); box.set_margin_bottom(12)
box.set_name("volbar")
rev.add(box)


def vol_row(tag):
    r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    l = Gtk.Label(label=tag)
    l.get_style_context().add_class("lbl")
    l.set_width_chars(3)
    p = Gtk.Label()
    p.get_style_context().add_class("pct")
    p.set_width_chars(7)
    adj = Gtk.Adjustment(value=initial_pct(tag),
                         lower=0, upper=100, step_increment=1, page_increment=5, page_size=0)
    s = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
    s.set_digits(0)
    s.set_draw_value(False)
    s.set_hexpand(True)
    mt = Gtk.ToggleButton(label="Mute")
    r.pack_start(l, False, False, 0)
    r.pack_start(p, False, False, 0)
    r.pack_start(s, True, True, 0)
    r.pack_start(mt, False, False, 0)
    return r, p, s, mt

row_v, vol_pct, vol_slider, vol_mute = vol_row("VOL")
row_m, mic_pct, mic_slider, mic_mute = vol_row("MIC")
box.pack_start(row_v, False, False, 0)
box.pack_start(row_m, False, False, 0)

vol_pct.set_text("VOL %d%%" % int(vol_slider.get_value()))
mic_pct.set_text("MIC %d%%" % int(mic_slider.get_value()))
vol_slider.connect("value-changed", on_vol_change)
mic_slider.connect("value-changed", on_mic_change)
vol_mute.connect("toggled", lambda b: mute("@DEFAULT_AUDIO_SINK@", b.get_active()))
mic_mute.connect("toggled", lambda b: mute("@DEFAULT_AUDIO_SOURCE@", b.get_active()))

outp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
outp_lbl = Gtk.Label()
outp_lbl.get_style_context().add_class("lbl")
outp_lbl.set_text(port_label())
sw = Gtk.Button(label="Switch output")
sw.connect("clicked", lambda *_x: switch_output())
outp.pack_start(outp_lbl, False, False, 0)
outp.pack_start(sw, True, False, 0)
box.pack_start(outp, False, False, 0)


def refresh_mutes():
    vol_mute.set_active(muted("@DEFAULT_AUDIO_SINK@"))
    mic_mute.set_active(muted("@DEFAULT_AUDIO_SOURCE@"))
    return True


win.connect("key-press-event", lambda *_x: do_close() if _x[1].keyval == 0xFF1B else None)
win.connect("focus-out-event", do_close)


def on_realize(*_):
    try:
        idx = win.get_window().get_monitor()
        geo = screen.get_monitor_geometry(idx)
        win.move(geo.x + geo.width - 428, geo.y + 42)
    except Exception:
        pass
    rev.set_reveal_child(True)


win.connect("realize", on_realize)
win.set_default_size(420, 150)
ensure_default()
win.show_all()
win.present()
GLib.timeout_add(2500, refresh_mutes)
GLib.timeout_add(20000, do_close)
Gtk.main()