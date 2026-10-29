# Changelog

## 1.2 — 2026-10-29

### Workspace transitions you can pick
`SUPER + S → Animations` opens a two-pane picker with ten presets (Classic
Slide, Slide Fade, Snappy, Cinematic, Super Smooth, Abala Shell, …), live
preview of each transition's character, and one click applies it. The choice is
written to `~/.config/rice/ws-anim.conf`, which `hyprland.lua` reads at startup
and feeds into `hl.animation` for `workspaces`, `workspacesIn` and
`workspacesOut`. The same file drives `general.gaps_workspaces`, so presets that
want the wallpaper to show between desktops set the gap themselves. Added the
`superSmooth`, `abala.standard` and `abala.emphasized` beziers the presets need.

### Lock-screen editor v3 — and it actually stays where you put it
The editor now follows the same convention as the desktop widget manager: the
`(x, y)` you see is the widget's **top-left** corner, dragging keeps the grab
offset so the box never jumps to the cursor, arrow keys nudge, and Shift nudges
by 1 px. Under the hood, hyprlock's `position` is a layout value that is parsed
with a comma; the old space-separated `position = X Y` silently failed and
piled every widget into one corner. The generator now always writes
`position = X, Y`, refuses to build a comma-less position, and `--build`
regenerates `hyprlock.conf` headlessly. New lock widgets: **Day Clock**
(`lockclockday`) and **Photo Frame** (`lockframe`, six transitions).

### Three new desktop widgets
- **Big Day Clock** (`widget-clockday`) — time pill on top, a huge weekday that
  slides when the day changes, full date underneath.
- **Photo Frame** (`widget-frame`) — glass photo slideshow with six
  transitions (fade, slide in four directions, zoom-fade), never repeating the
  same image or transition twice in a row.
- **Dino** (`widget-dino`) — an offline T-Rex endless runner. Click it to give
  it the keyboard, Space/Up to jump, Down to duck, R to restart; the accent
  colours the dino and the speed ramps up.

The Widget Manager learned all three, shows a faint 10% grid for alignment,
keeps the same grab-offset dragging, and now has **Apply (live)** next to
**Save & Close** so you can tune placement without closing the window.

### Bluetooth menu that really scans
`SUPER + S → Bluetooth` is now a full manager: power, discoverable/pairable,
scan for new devices, and connect/disconnect with auto-pair. The old scan was
`timeout 8 bluetoothctl scan on`, but `bluetoothctl` reads stdin and exits on
EOF — discovery stopped instantly, so headphones were never found. The scan now
keeps a command pipe open for the whole discovery window and caches what it
sees, then re-runs the menu so every state is fresh.

### Folder icons follow the wallpaper — including the plain folder
`palette.py` now rebuilds a `WallpaperAccent` icon theme and repaints Breeze's
folder SVGs: neutral grays take the accent hue while keeping their shading ramp,
and the KDE-blue folder face is recoloured too (it used to stay blue no matter
what the wallpaper was). The same pass fixes Dolphin's `inode-directory` MIME
icon. Genuinely grayscale wallpapers keep a neutral `#DFDFDF` accent instead of
picking up a stray warm or blue cast from a single tinted region.

### Wallpaper pipeline: no more parallel switches
`apply-wallpaper` now takes a lock before touching anything, and a burst of
requests can no longer run in parallel (the old code waited and then removed a
fresh holder's lock, which produced the 9× log lines and widget respawn storms).
A lock older than 60 s is treated as a crash leftover and reclaimed. Widget
restarts are debounced the same way: `--force-restart` calls that arrive within
2.5 s are coalesced, so a theme apply plus a leftover watcher no longer kill and
respawn every widget twice.

### Wallpaper picker: focus, state and accent
The picker opens on the wallpaper that is **actively set** in `hyprpaper.conf`
(the state file is only a fallback, so a slideshow rotation no longer leaves it
on a stale manual pick). It restores its own focus after every navigation, and
the selected card's border re-tints from the live `theme.lua` accent.

### Menus and small fixes
- Session menu (waybar power button) now delegates to `wlogout` with its
  default 3-per-row layout, so Log out / Sleep / Reboot / Power off sit in one
  horizontal row; the wofi glyph menu remains as a fallback.
- `wofi --lines N` was invalid and ignored — replaced with `--height`, so the
  Wi-Fi, Bluetooth and notification menus size themselves correctly.
- The screen-record tile in the notification center uses its intended icon.
- `dolphin` gets a shim that forces `QT_QPA_PLATFORMTHEME=qt6ct`, and Hyprland
  exports that variable at startup — Dolphin now renders the wallpaper scheme
  whether it is launched from the keybind, wofi or a script.
- `rules.lua` fades the launcher layer in so the drop reads as part of the bar
  instead of a ghost popup.

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