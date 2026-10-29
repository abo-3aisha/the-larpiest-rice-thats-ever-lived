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

ac=0
for p in /sys/class/power_supply/*/online; do
    [ -f "$p" ] || continue
    [ "$(cat "$p" 2>/dev/null)" = "1" ] && ac=1
done

cap_disp=$cap
if [ "$ac" = "1" ]; then
    case "$status" in
        Charging | Full) ;;
        *)
            # Plugged in but the EC is in its "top-off pause" (it toggles
            # 100↔~97 with no steps in between, reporting Discharging for a
            # moment). Never read that as unplugged: keep the charging look
            # and show a steady full instead of a flickering 97.
            [ "$cap" -ge 97 ] && cap_disp=100
            ;;
    esac
fi

cls=("battery" "b$cap_disp")
[ "$cap" -le 20 ] && cls+=("critical")
if [ "$ac" = "1" ] || [ "$status" = "Charging" ] || [ "$status" = "Full" ]; then
    cls+=("charging")
fi

printf '{"text":"%d%%","class":[%s],"alt":"%d%% %s"}\n' "$cap_disp" \
    "$(printf '"%s",' "${cls[@]}" | sed 's/,$//')" \
    "$cap_disp" "$status"