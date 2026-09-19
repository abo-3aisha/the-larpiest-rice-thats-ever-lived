#!/bin/sh
W="${1:?usage: setwall.sh /path/to/image}"
[ -f "$W" ] || { echo "file not found: $W"; exit 1; }
W="$(realpath "$W")"

printf 'preload = %s\nwallpaper = eDP-1,%s\n' "$W" "$W" > "$HOME/.config/hypr/hyprpaper.conf"

# Route through apply-wallpaper so a single pipeline (swaybg + palette engine)
# handles the switch — setwall.sh no longer duplicates theming logic.
exec "$HOME/.local/bin/apply-wallpaper"