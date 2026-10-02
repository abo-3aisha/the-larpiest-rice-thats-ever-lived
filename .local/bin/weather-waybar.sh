#!/usr/bin/env bash
# weather-waybar.sh — cached current weather from Open-Meteo.
# Edit LAT/LON for your city (default: Damascus 33.5138,36.2765).
#
# The cache stores the raw WMO weather CODE ("<code> 22°|hum|wind"), not a
# word, so the description is translated at render time and a language switch
# never needs a refetch.
LAT="33.5138"
LON="36.2765"
CACHE="$HOME/.cache/waybar-weather"
TTL=600
B="$HOME/.local/bin"

# shellcheck disable=SC1090
eval "$("$B/i18n.py" dump)"

fetch() {
    python3 - "$LAT" "$LON" <<'PY'
import json, sys, urllib.request
lat, lon = sys.argv[1], sys.argv[2]
url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
       "&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
       "&timezone=auto" % (lat, lon))
req = urllib.request.Request(url, headers={"User-Agent": "waybar-weather/1.0"})
d = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
c = d["current"]
code = int(c["weather_code"])
temp = round(float(c["temperature_2m"]))
hum = int(float(c.get("relative_humidity_2m", 0)))
wind = int(round(float(c.get("wind_speed_10m", 0))))
print("%d %d°|%d|%d" % (code, temp, hum, wind))
PY
}

# code -> translated phrase (falls back to the key only if truly absent)
desc_of() { local v; v=$("$B/i18n.py" get "WX_$1" 2>/dev/null); printf '%s' "${v:-$1}"; }

if [ "$1" = "--detail" ]; then
    fresh=$(fetch 2>/dev/null)
    if [ -n "$fresh" ]; then
        head="${fresh%%|*}"; rest="${fresh#*|}"
        hum="${rest%%|*}"; wind="${rest##*|}"
        info="$(desc_of "${head%% *}") ${head##* }  |  $T_WX_WIND $wind km/h  |  $T_WX_HUM $hum%"
        [ -s "$CACHE" ] && info="$info  $T_WX_UPDATED"
    elif [ -s "$CACHE" ]; then
        head="$(grep -o '^[^|]*' < "$CACHE")"
        info="$(desc_of "${head%% *}") ${head##* }$T_WX_OFFLINE_CACHED"
    else
        info="$T_WX_OFFLINE"
    fi
    command -v notify-send >/dev/null 2>&1 && \
        notify-send -t 4000 -u low "$T_WBAR_WEATHER" "$info" 2>/dev/null
    exit 0
fi

if [ ! -f "$CACHE" ] || [ $(( $(date +%s) - $(stat -c %Y "$CACHE") )) -gt $TTL ]; then
    fetch > "$CACHE" 2>/dev/null
fi

if [ ! -s "$CACHE" ]; then
    echo '{"text":"...","class":"off"}'
    exit 0
fi

raw=$(tr -d '\n' < "$CACHE")
head="${raw%%|*}"
code="${head%% *}"; temp="${head##* }"
desc=$(desc_of "$code")
cls=$(printf '%s' "$desc" | tr '[:upper:]' '[:lower:]' | tr -s ' ' '-')
printf '{"text":"%s %s","class":"%s","tooltip":"%s"}' "$desc" "$temp" "$cls" "$desc $temp"
