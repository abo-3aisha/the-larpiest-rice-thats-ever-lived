# the larpiest rice that's ever lived

It's my first project so be nice i used ai alot cause i'm a beginner but i like how hyprland
so i want something that's reflect my self into any pc or laptop
So:
I'ts a Hyprland rice on CachyOS, themed around a certain virtual idol with long teal hair.
Everything is driven by **one color engine** glued to the wallpaper.

## Highlights

- **Hyprland** config written in Lua (`hyprland.lua` + rules), with live wallpaper
  theming via `palette.py` — the single source of truth for colors
- **waybar** with custom battery (egg-shaped PNG), whole-device network speed,
  weather, and a switched-by-pressure wifi indicator
- **swaync** control center with Android-style quick settings (real RE-to-glue
  `type: toggle` tiles), volume + mic sliders
- **wofi** launcher, control center, logout menu and emoji picker (offline, types
  the emoji — no clipboard)
- **hyprlock** with live blur behind the lock screen (session_lock_xray)
- **video wallpaper** via mpvpaper + awww image transitions
- **foot, fish, cava, fastfetch, GTK/Thunar, wlogout, wal** all re-themed from
  the same palette run
- **~/.local/bin** with 50+ helper scripts: `notif-center`, `ctrl-center`,
  `fn-key`, `vol-bar.py`, `net-speed-waybar.sh`, `emoji-picker`, and more

## Colors

Colors are never hardcoded — they come from the active wallpaper through
`palette.py` (pywal neutrals + an accent sampled from the real image). Gray
wallpapers map to white accents, teal to teal, azure to azure. A guard rejects
leaked fallback colors (`7aa2f7` / `6068c8`).

## Wallpaper switching

`rand-wallpaper` / `pick-wallpaper` -> hyprpaper.conf -> `apply-wallpaper`
(awww grow transition, falls back to swww, then swaybg) -> one `palette.py --apply`.

## Install

These are personal dotfiles meant as a reference. Copy what you need into
`~/.config` and `~/.local/bin`, then reload Hyprland.

## Wallpaper daemon

`awww` (successor to swww) for images, `mpvpaper` for video. Not both at once.
`apply-wallpaper` auto-detects by extension.


Note: i wanted to mix the cleanest things from android , default hyprland and other known shells
