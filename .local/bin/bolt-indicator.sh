#!/usr/bin/env bash
# bolt-indicator — the small bolt next to the battery. One continuous glow
# animation whose SHAPE depends on the power source:
#
#   on AC  -> a calm, wide "breathing" halo  (charging, energy flowing in)
#   full   -> a still, low glow              (done, nothing left to do)
#   on batt-> a quiet single "tick"         (nothing happening, stay out of the way)
#
# It is an animation, so this runs several times a second. It therefore forks
# NOTHING on the hot path: the battery is read with the `read` builtin, the
# frame index comes from bash's EPOCHREALTIME, and the result is one printf.
# Every cat/date here would cost a percent of a core for the whole session.
#
# The animation itself is CSS opacity on #custom-bolt (see
# ~/.config/waybar/style.custom.css). This script only decides WHICH curve to
# walk and how many steps — it never changes the glyph, because a changing
# glyph would change the module width and shove the battery % sideways.
#
# FRAMES below must match the c0..cN rules in style.custom.css.

BOLT=$'\xf3\xb1\x90\x8b'   # MDI lightning-bolt (the glyph already in use)

# Two curves, so the bolt visibly means different things.
#   charge: 8 steps over 1.6s  -> a slow, even swell
#   full:   2 steps over 3.0s  -> an almost-steady low glow, barely moving
#   batt:   3 steps over 1.5s  -> one dip and return, mostly resting
CHARGE_FRAMES=8
CHARGE_STEP_US=200000       # 200 ms  => 1.6 s cycle
FULL_FRAMES=2
FULL_STEP_US=1500000        # 1.5 s   => 3.0 s cycle
BATT_FRAMES=3
BATT_STEP_US=500000         # 500 ms  => 1.5 s cycle

# Pick the same battery battery-bar.sh picks: type Battery, present, highest
# capacity (so a mouse/keypad battery never wins over the pack).
best=""
bestcap=-1
for b in /sys/class/power_supply/BAT*; do
    [ -d "$b" ] || continue
    # sysfs attributes carry NO trailing newline, so `read` exits non-zero at
    # EOF even though it filled the variable. Never branch on read's exit code
    # here — clear the variable first and test its value.
    type=""; read -r type < "$b/type" 2>/dev/null
    [ "$type" = "Battery" ] || continue
    if [ -f "$b/present" ]; then
        present=""; read -r present < "$b/present" 2>/dev/null
        [ "$present" = "1" ] || continue
    fi
    cap=""; read -r cap < "$b/capacity" 2>/dev/null
    case "$cap" in
        '' | *[!0-9]*) continue ;;
    esac
    if [ "$cap" -gt "$bestcap" ]; then best="$b"; bestcap="$cap"; fi
done

if [ -z "$best" ]; then
    printf '{"text":"","class":["off"],"alt":"no battery"}\n'
    exit 0
fi

# on_ac: any power_supply online == 1 means the charger is plugged in.
ac=0
for p in /sys/class/power_supply/*/online; do
    [ -f "$p" ] || continue
    v=""; read -r v < "$p" 2>/dev/null
    [ "$v" = "1" ] && ac=1
done

# EPOCHREALTIME is seconds.microseconds, e.g. 1759372345.123456
us=${EPOCHREALTIME/./}

if [ "$ac" = "1" ]; then
    status=""; read -r status < "$best/status" 2>/dev/null
    if [ "$status" = "Full" ]; then
        # 100%: a still, low glow. Only two steps and a 3s cycle, so it reads
        # as "settled" rather than as more charging.
        frame=$(( (10#$us / FULL_STEP_US) % FULL_FRAMES ))
        printf '{"text":"%s","class":["full","c%d"],"alt":"fully charged"}\n' "$BOLT" "$frame"
        exit 0
    fi
    if [ "$status" = "Charging" ]; then
        frame=$(( (10#$us / CHARGE_STEP_US) % CHARGE_FRAMES ))
        printf '{"text":"%s","class":["charging","c%d"],"alt":"charging"}\n' "$BOLT" "$frame"
        exit 0
    fi
    # Plugged in but neither charging nor full (a paused pack).
    printf '{"text":"","class":["off"],"alt":"on ac, not charging"}\n'
    exit 0
fi

# On battery: a much quieter presence, but still alive.
frame=$(( (10#$us / BATT_STEP_US) % BATT_FRAMES ))
printf '{"text":"%s","class":["battery","c%d"],"alt":"on battery"}\n' "$BOLT" "$frame"
