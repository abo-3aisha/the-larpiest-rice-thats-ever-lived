#!/usr/bin/env bash
# weather-waybar.sh - cached current weather from Open-Meteo (English, no Arabic).
# Edit LAT/LON for your city (default: Damascus 33.5138,36.2765).
# Cache (plain text "Descr 22°|hum%|wind") lives 600s.
LAT="33.5138"
LON="36.2765"
CACHE="$HOME/.cache/waybar-weather"
TTL=600

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
names = {
    0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    56: "Freezing Drizzle", 57: "Freezing Drizzle",
    61: "Rain", 63: "Rain", 65: "Rain",
    66: "Freezing Rain", 67: "Freezing Rain",
    71: "Snow", 73: "Snow", 75: "Snow", 77: "Snow Grains",
    80: "Showers", 81: "Showers", 82: "Showers",
    85: "Snow Showers", 86: "Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Thunderstorm with Hail",
}
desc = names.get(int(c["weather_code"]), "Weather")
temp = round(float(c["temperature_2m"]))
hum = int(float(c.get("relative_humidity_2m", 0)))
wind = int(round(float(c.get("wind_speed_10m", 0))))
print("%s %d\u00b0|%d|%d" % (desc, temp, hum, wind))
PY
}

if [ "$1" = "--detail" ]; then
    fresh=$(fetch 2>/dev/null)
    if [ -n "$fresh" ]; then
        main="${fresh%%|*}"; rest="${fresh#*|}"; hum="${rest%%|*}"; wind="${rest##*|}"
        info="$main | wind $wind km/h | humidity $hum%"
        [ -s "$CACHE" ] && info="$info  (updated)"
    elif [ -s "$CACHE" ]; then
        main="$(grep -o '^[^|]*' < "$CACHE")"
        info="$main (offline - cached)"
    else
        info="Offline - no cached weather yet"
    fi
    command -v notify-send >/dev/null 2>&1 && \
        notify-send -t 4000 -u low "Weather" "$info" 2>/dev/null
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
main="${raw%%|*}"
desc="${main% *}"
temp="${main##* }"
cls=$(tr '[:upper:]' '[:lower:]' <<<"$desc" | tr -s ' ' '-')
printf '{"text":"%s %s","class":"%s","tooltip":"%s"}' "$desc" "$temp" "$cls" "$raw"