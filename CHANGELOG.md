# Changelog

## 1.1 — 2026-10-07

### requirements.sh — one command brings up a fresh machine
New `./requirements.sh` installs every runtime tool the rice actually calls, in
the right order and idempotently. It tries the pacman repos first and falls
back to yay only for names that live in the AUR, so `awww`/`hyprshot` resolve
wherever they ship. It knows the compositor *must* be CachyOS's Lua build
(`cachyos-hypr-noctalia`) and says so loudly on vanilla Arch instead of
installing the wrong thing. `--check` previews, `--optional` adds extras
(thunar, gwenview, keyring, …), `--yes` skips the prompt. Bottled knowledge:
`hyprshot` for screenshots, `mpvpaper` for video wallpapers, `wl-screenrec` +
`wf-recorder` for recording, `gtk-layer-shell` + the python bindings for the
widget kit, `breeze-gtk` for the palette engine's `Breeze-Dark` GTK theme,
`ttf-jetbrains-mono-nerd` for the bar glyphs, and `sweet-cursors` for the
cursor the rice sets. `install.sh`'s dependency report was extended to match.

### Liquid glass, same recipe everywhere
One touch-glass recipe now covers the whole session — white specular top line,
`0.10→0.02` glass gradient, `1px` white rim, and a soft accent glow that
follows the wallpaper:
- waybar pills (protected in `style.custom.css`, so repainting the theme can't
  wipe it),
- swaync control center, notification popups (now translucent with `{cc_bg}`
  instead of a solid `#{bg}`, so the blurred desktop shows through) and the
  notification cards,
- every wofi menu (window and the search field),
- the vol-bar dropdown and the music widget's seek rail (GTK3 `highlight`
  selector — the old `progress` one painted it system-blue),
- app windows 0.95→0.90 opacity and blur vibrancy 0.40, so the wallpaper
  colour punches through the blur instead of going gray.

### Wallpaper picker: opens on the current wallpaper, and never ends
The picker no longer starts somewhere arbitrary and no longer has dead ends.
It opens focused on the *current* wallpaper (matched via `hyprpaper.conf`,
including video wallpapers' converted cache copies) and the strip wraps
forever in both directions — arrows and the wheel keep flipping; Home/End
jump to the nearest end of the infinite strip. Prefetch and draw order are
also wrapped, so a full wrap never flashes a blank slot.

### Video wallpaper that actually keeps playing
Root-caused the "notifications say *resumed* but the picture is frozen" bug:
mpvpaper was started with `-p -a FULL` = `--auto-pause / --auto-mode FULL`,
which pauses playback **by itself whenever any fullscreen window exists**
(man mpvpaper 1.9). Removed. Also: stdin from `/dev/null` so a
terminal-launched `apply-wallpaper` can't SIGTTIN-freeze the player, and a
hardened `stop_mpvpaper` (CONT → TERM → KILL) that can no longer race a
SIGSTOP'd instance when switching wallpapers mid-pause.

### SUPER+P: pause the video wallpaper on the exact frame
SIGSTOP/SIGCONT on mpvpaper — pixel-perfect freeze, zero CPU while paused. If
the player is gone it re-runs the (cached) apply pipeline instead of
complaining; every press breadcrumbs into `~/.cache/video-pause.dbg`, and the
new `vp-check` probe reports every mpvpaper pid with state + age so a stale
instance is visible next to a fresh one.

### Performance app ⇄ widgets: one master switch
`perf.conf` (the Performance app) is now honored in every place that could
resurrect something — `widgets-apply`, `cava-dock` (guards even an
`exec-once` spawn), the theme engine's cava restart, and `perf-mode`'s write
order. Turning Widgets/Cava off in the app now survives wallpaper changes and
reloads. Off anywhere = off.

### Waybar: breathing charging bolt
The bolt now pulses on AC with opacity keyframes that interpolate (GTK
transition) and follow the *live* accent — seamless wrap, dimmer on battery,
a still low glow at 100%.

### Fixes
- All 4 glass widgets were crashing at 01:37 with
  `ValueError: unsupported format character ')'` — an unescaped `%` in the
  widget CSS template (`widget_lib.py`). The whole widget set returned.
- `QT_QPA_PLATFORMTHEME` was `qtengine` (bogus — qt6ct never loaded); now
  `qt6ct`.
- Terminal binds now probe the installed terminals instead of hardcoding one
  (kitty → contour → ghostty → wezterm → foot → alacritty).
- Keyboard layout ownership moved out of `hyprland-gui.lua`; it was resetting
  the layout to `us,ara` on every reload.
- polkit-gnome agent autostart added (`hyprland.conf`).
- `palette.py` gained a state/lock so wallpaper changes can no longer double-
  restart the session.
- `swaync/config.json` is regenerated pretty-printed from its template.

## 1.0 — 2026-09-19
Initial release: single theme engine driven by the wallpaper, wallpaper
pipeline (images *and* video), virtual desktop, offline prayer times with
adhan, glass widgets, performance profiles, quick-settings notification
center, Acer Nitro key fixes.