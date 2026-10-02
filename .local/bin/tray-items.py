#!/usr/bin/env python3
"""tray-items — the real StatusNotifierItem (SNI) tray, the same source
waybar's `tray` module reads. Emits one JSON array on stdout:

  [{"id":"org.kde.x:/StatusNotifierItem/3","service":"org.kde.x",
    "path":"/StatusNotifierItem/3","icon":"/abs/...png","tip":"Network",
    "status":"Active","category":"SystemTray"}]

Icon resolution walks the icon theme once and caches the index, so a consumer
only has to decode a PNG/SVG. Nothing here is a window list: these are the tray
icons the desktop published on DBus.

Also acts on an item when called as
  tray-items.py activate <service> <path>     (left click)
  tray-items.py menu <service> <path>         (right / middle click)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

IFACE_ITEM = "org.kde.StatusNotifierItem"
IFACE_WATCHER = "org.kde.StatusNotifierWatcher"

CACHE = Path.home() / ".cache/tray-items-icon-index.json"
ICON_DIRS = [
    Path.home() / ".local/share/icons",
    Path.home() / ".icons",
    Path("/usr/share/icons"),
    Path("/run/host/usr/share/icons"),
]
PREFERRED = ("scalable", "22x22", "24x24", "20x20", "16x16", "32x32", "48x48")


def run(args, timeout=4):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip()
    except Exception:
        return 1, ""


# ------------------------------------------------------------------ bus reads
def bus_get(service, path, iface, prop):
    rc, out = run([
        "busctl", "--user", "get-property", service, path, iface, prop,
    ])
    if rc != 0 or not out:
        return None
    # `a(ss) 2 "svc" "/path" "svc" "/path"`  ->  pull the quoted pairs
    if out.startswith("a(ss)"):
        q = re.findall(r'"([^"]*)"', out)
        return ["%s:%s" % (q[i], q[i + 1]) for i in range(0, len(q) - 1, 2)]
    if out.startswith('"'):
        m = re.findall(r'"([^"]*)"', out)
        return m[0] if m else None
    return out.split(" ", 1)[-1] if " " in out else out


def props_all(service, path, iface):
    """Every property of one object in a single busctl call.

    Three separate get-property calls per icon is slow enough to matter on a
    2s poll; GetAll hands us IconName + Status + Category + ToolTip at once.
    A dead registration (the app quit between the list and this call) returns
    {} and the item is skipped, exactly like waybar does.
    """
    rc, out = run([
        "busctl", "--user", "call", service, path,
        "org.freedesktop.DBus.Properties", "GetAll", "s", iface,
    ], timeout=4)
    if rc != 0 or not out:
        return {}
    d = {}
    for m in re.finditer(r'"(\w+)"\s+s\s+"([^"]*)"', out):
        d[m.group(1)] = m.group(2)
    for m in re.finditer(r'"(\w+)"\s+[bi]\s+(-?\d+)', out):
        d.setdefault(m.group(1), m.group(2))
    # ToolTip is (sa(iiay)ss): icon name, title, description
    m = re.search(
        r'"ToolTip"\s+\(sa\(iiay\)ss\)\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"', out
    )
    if m:
        d["ToolTip"] = "\0".join(x for x in m.groups() if x)
    return d


def tip_of(props):
    """The human label for the icon.

    ToolTip is (icon_name, title, description) — the *title* is the label, the
    first field is a theme name like `nm-wireless`, which would show up as
    garbage, so it is only used as a last resort.
    """
    parts = [p.strip() for p in (props.get("ToolTip") or "").split("\0")]
    for part in parts[1:]:
        if part and "/" not in part:
            return part[:48]
    stem = props.get("IconName") or parts[0] or props.get("Category") or ""
    return stem.split("-")[0][:48]


def icon_of(props, idx):
    """IconName — or the attention icon while the app is asking for it."""
    name = props.get("IconName") or ""
    if (props.get("Status") or "") == "NeedsAttention" and props.get("AttentionIcon"):
        name = props["AttentionIcon"]
    return resolve(idx, name)


# ------------------------------------------------------------------ icons
def load_index():
    """name -> file, best size wins. Cached forever (themes do not move)."""
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text())
        except Exception:
            pass
    idx = {}
    for root in ICON_DIRS:
        if not root.is_dir():
            continue
        for dirpath, _dirs, files in os.walk(root):
            rel = os.path.relpath(dirpath, root)
            rank = PREFERRED.index(rel) if rel in PREFERRED else len(PREFERRED)
            for fn in files:
                stem, ext = os.path.splitext(fn)
                if ext.lower() not in (".png", ".svg", ".webp", ".xpm"):
                    continue
                prev = idx.get(stem)
                cand = (rank, os.path.join(dirpath, fn))
                if prev is None or cand[0] < prev[0]:
                    idx[stem] = cand
    flat = {k: v[1] for k, v in idx.items()}
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(flat))
    except Exception:
        pass
    return flat


def resolve(idx, name):
    if not name:
        return None
    if name.startswith("/") and Path(name).exists():
        return name
    for key in (name, name.replace("-symbolic", ""), name + "-symbolic"):
        if key in idx:
            return idx[key]
    return None


# ------------------------------------------------------------------ watchers
def watchers():
    """Every StatusNotifierWatcher on the bus.

    A host (waybar today) implements the watcher
    itself and owns the well-known name with its own pid appended:
    `org.kde.StatusNotifierWatcher-<pid>`. Querying the bare well-known name
    therefore finds nothing — that is exactly why the tray came up empty.
    """
    rc, out = run(["busctl", "--user", "list", "--no-legend"], timeout=4)
    names = set()
    if rc == 0:
        for m in re.finditer(r"org\.kde\.StatusNotifierWatcher[-0-9]+", out):
            names.add(m.group(0))
        for m in re.finditer(r"org\.freedesktop\.StatusNotifierWatcher[-0-9]*", out):
            names.add(m.group(0))
    if not names:
        names = {"org.kde.StatusNotifierWatcher"}
    # shortest suffix first: the oldest host owns the most items
    return sorted(names, key=len)


def live_watcher():
    """The host with the most published items is the live one."""
    best, n = None, -1
    for w in watchers():
        got = bus_get(
            w, "/StatusNotifierWatcher", IFACE_WATCHER, "RegisteredStatusNotifierItems"
        ) or []
        if len(got) > n:
            best, n = w, len(got)
    return best, max(n, 0)


def _call(w, method, sig, *args):
    run(
        ["busctl", "--user", "call", w, "/StatusNotifierWatcher",
         IFACE_WATCHER, method, sig] + list(args),
        timeout=4,
    )


def activate(service, path):
    """ActivateWatcher(s service, s object_path, s action, i timestamp)"""
    w, _n = live_watcher()
    if w:
        _call(w, "ActivateWatcher", "ss", service, path, "", "i", "0")


def menu(service, path):
    """ContextMenu(s service, s object_path, i timestamp)"""
    w, _n = live_watcher()
    if w:
        _call(w, "ContextMenu", "s", service, path, "i", "0")


# ------------------------------------------------------------------ main
def main():
    if len(sys.argv) == 4 and sys.argv[1] in ("activate", "menu"):
        (activate if sys.argv[1] == "activate" else menu)(sys.argv[2], sys.argv[3])
        return

    w, n = live_watcher()
    if not w or n <= 0:
        json.dump([], sys.stdout)
        return

    idx = load_index()
    out = []
    for ident in bus_get(
        w, "/StatusNotifierWatcher", IFACE_WATCHER, "RegisteredStatusNotifierItems"
    ) or []:
        if ":" not in ident:
            continue
        service, path = ident.split(":", 1)
        props = props_all(service, path, IFACE_ITEM)
        if not props:
            continue  # the app quit; drop the stale registration
        out.append({
            "id": ident,
            "service": service,
            "path": path,
            "icon": icon_of(props, idx),
            "tip": tip_of(props),
            "status": props.get("Status", ""),
            "category": props.get("Category", ""),
        })
    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
