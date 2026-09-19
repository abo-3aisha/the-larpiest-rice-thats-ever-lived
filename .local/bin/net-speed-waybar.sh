#!/usr/bin/env python3
"""waybar module (one-shot, waybar re-runs it every second via interval:1):
whole-device upload/download speed, stacked (up above, down below).
Sums rx/tx bytes across every real interface (excludes lo and bridge/veth/
docker/virbr/tun/tap/wg virtuals). EMA-smoothed so numbers glide instead of
jumping. Hidden completely when the machine has no default route (offline).
Glow-up on reconnect: EMA restarts from 0 so speeds visibly climb from zero."""
import json
import os
import time
from pathlib import Path

NET = Path("/sys/class/net")
CACHE = Path.home() / ".cache/waybar-netspeed.json"

EXCLUDE = {"lo"}
SKIP_PREFIX = ("veth", "docker", "virbr", "br-", "tun", "tap", "wg",
               "vlan", "dummy", "sit", "ip6tnl", "tailscale", "nm-bridge")
ALPHA = 0.35  # EMA smoothing (0..1); higher = quicker, lower = smoother


def interfaces():
    if not NET.is_dir():
        return {}
    out = {}
    for name in os.listdir(NET):
        if name in EXCLUDE or name.startswith(SKIP_PREFIX):
            continue
        if not (NET / name / "statistics/rx_bytes").is_file():
            continue
        try:
            up = (NET / name / "operstate").read_text().strip() == "up"
        except Exception:
            up = False
        out[name] = up
    return out


def totals():
    rx = tx = 0
    for name in interfaces():
        b = NET / name / "statistics"
        try:
            rx += int((b / "rx_bytes").read_text())
            tx += int((b / "tx_bytes").read_text())
        except Exception:
            pass
    return rx, tx


def has_default_route():
    try:
        for line in Path("/proc/net/route").read_text(errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "00000000":
                return True
    except Exception:
        pass
    return False


def fmt(b):
    if b >= 2 ** 20:
        return f"{b / 2 ** 20:.1f} MB/s"
    if b >= 2 ** 10:
        return f"{b / 2 ** 10:.0f} KB/s"
    return f"{b:.0f} B/s"


def load():
    try:
        return json.loads(CACHE.read_text())
    except Exception:
        return {}


if not has_default_route():
    CACHE.write_text(json.dumps({"online": False}))
    print('{"text":"","class":"offline"}')
    raise SystemExit

now = time.time()
rx, tx = totals()
old = load()
prev = old.get("online", False)
last_t = old.get("t")
ema_rx = float(old.get("ema_rx", 0) or 0)
ema_tx = float(old.get("ema_tx", 0) or 0)

if last_t is not None and prev:
    dt = now - last_t
    if 0.2 < dt < 3.0:  # skip stale samples (waybar restart / suspend)
        irx = max(0.0, (rx - old.get("rx", rx)) / dt)
        itx = max(0.0, (tx - old.get("tx", tx)) / dt)
        ema_rx = ema_rx * (1 - ALPHA) + irx * ALPHA
        ema_tx = ema_tx * (1 - ALPHA) + itx * ALPHA
    # else: keep previous EMA -> no fake spike on resume

CACHE.write_text(json.dumps({
    "online": True, "t": now, "rx": rx, "tx": tx,
    "ema_rx": ema_rx, "ema_tx": ema_tx,
}))

tooltip = "Download \u2193 {}  \u00b7  Upload \u2191 {}".format(fmt(ema_rx), fmt(ema_tx))
text = "\u2191 {up}\n\u2193 {down}".format(up=fmt(ema_tx), down=fmt(ema_rx))
print(json.dumps({"text": text, "class": "online", "tooltip": tooltip}))