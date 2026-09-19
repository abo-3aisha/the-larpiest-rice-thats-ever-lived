#!/usr/bin/env bash
# battery-bar — Android-style horizontal battery DRAWN in CSS: shell + nub +
# exact fill level, with the % inside. class encodes the exact capacity.

best=""
bestcap=-1
for b in /sys/class/power_supply/BAT*; do
    [ -d "$b" ] || continue
    [ "$(cat "$b/type" 2>/dev/null)" = "Battery" ] || continue
    if [ -f "$b/present" ] && [ "$(cat "$b/present" 2>/dev/null)" != "1" ]; then
        continue
    fi
    cap=$(cat "$b/capacity" 2>/dev/null)
    case "$cap" in
        '' | *[!0-9]*) continue ;;
    esac
    if [ "$cap" -gt "$bestcap" ]; then best="$b"; bestcap="$cap"; fi
done

if [ -z "$best" ]; then
    printf '{"text":"󱉞","class":["none"],"alt":"no battery"}\n'
    exit 0
fi

cap=$((bestcap > 100 ? 100 : bestcap))
status=$(cat "$best/status" 2>/dev/null)

cls=("battery" "b$cap")
[ "$cap" -le 20 ] && cls+=("critical")
case "$status" in
    Charging | Full) cls+=("charging") ;;
esac

printf '{"text":"%d%%","class":[%s],"alt":"%d%% %s"}\n' "$cap" \
    "$(printf '"%s",' "${cls[@]}" | sed 's/,$//')" \
    "$cap" "$status"