#!/bin/sh
# screenshot.sh [region|window|output]
# Saves to ~/Pictures/Screenshots/ AND copies the PNG to the clipboard.
DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"
MODE="${1:-region}"
FILE="$DIR/$(date +%Y-%m-%d_%H-%M-%S).png"

case "$MODE" in
    window)
        hyprshot -m window -o "$DIR" -f "$(basename "$FILE")" 2>/dev/null
        [ ! -s "$FILE" ] && {
            G="$(hyprctl -j activewindow 2>/dev/null | python3 -c 'import json,sys
try:
    w = json.load(sys.stdin)
    print("%d,%d %dx%d" % (w["at"][0], w["at"][1], w["size"][0], w["size"][1]))
except Exception:
    pass')"
            [ -n "$G" ] && grim -g "$G" "$FILE"
        }
        ;;
    output)
        hyprshot -m output -o "$DIR" -f "$(basename "$FILE")" 2>/dev/null
        [ ! -s "$FILE" ] && grim "$FILE"
        ;;
    *)
        # Region via grim+slurp — the selection UI never lands in the capture,
        # so there is no washed-out/dimmed result (hyprshot's overlay caused it).
        G="$(slurp 2>/dev/null)"
        if [ -n "$G" ]; then
            sleep 0.2
            grim -g "$G" "$FILE" 2>/dev/null
        fi
        ;;
esac

if [ -s "$FILE" ]; then
    wl-copy --type image/png < "$FILE"
    notify-send -a "Screenshot" -i "$FILE" "Screenshot saved" "$(basename "$FILE") — also in clipboard"
else
    notify-send -a "Screenshot" -u critical "Screenshot failed" "hyprshot/grim could not capture"
fi