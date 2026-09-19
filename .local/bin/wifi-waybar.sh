#!/usr/bin/env bash
# wifi-waybar — state for waybar custom/wifi. Never disappears: shows
# "󰤮 off" when the radio is off, signal bars + SSID when connected, and
# an ethernet/empty state otherwise. JSON output for waybar.
json() { printf '{"text":"%s","class":"%s","alt":"%s"}\n' "$1" "$2" "$3"; }

radio=$(nmcli radio wifi 2>/dev/null)

if [ "$radio" = "disabled" ]; then
    json "󰤮 off" "off" "off"
    exit 0
fi

line=$(nmcli -t -f IN-USE,SIGNAL,SSID dev wifi 2>/dev/null | awk -F: '$1 == "*" { print; exit }')
if [ -n "$line" ]; then
    sig=$(printf '%s' "$line" | cut -d: -f2)
    ssid=$(printf '%s' "$line" | cut -d: -f3-)
    case "$sig" in
        75|7[6-9]|[89][0-9]|100) ic="󰤩" ;;
        5[0-9]|6[0-9]|7[0-4])    ic="󰤪" ;;
        3[0-9]|4[0-9])           ic="󰤫" ;;
        *)                       ic="󰤬" ;;
    esac
    json "$ic $ssid" "connected" "connected"
    exit 0
fi

if nmcli -t -f DEVICE,TYPE,STATE dev status 2>/dev/null | grep -qE ':ethernet:connected'; then
    json "󰈁" "ethernet" "ethernet"
    exit 0
fi

json "󰤮 Disconnected" "disconnected" "off"