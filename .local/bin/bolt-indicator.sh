#!/usr/bin/env bash
# bolt-indicator — tiny lightning bolt shown NEXT to the battery icon ONLY
# while charging (or full = on AC). Reads the same battery source as
# battery-bar.sh so the two always agree. No other module is touched.

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
    printf '{"text":"","class":["off"],"alt":"no battery"}\n'
    exit 0
fi

status=$(cat "$best/status" 2>/dev/null)
case "$status" in
    Charging | Full) printf '{"text":"\xf3\xb1\x90\x8b","class":["charging"],"alt":"charging"}\n' ;;
    *) printf '{"text":"","class":["off"],"alt":"discharging"}\n' ;;
esac