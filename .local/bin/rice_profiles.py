#!/usr/bin/env python3
"""rice-profiles — named performance profiles (Performance app, SUPER+S).

One file, ~/.config/rice/profiles.json, holds every profile the user has.
Three come built in; the Performance app can create, duplicate, rename and
delete more. Applying a profile writes the single active set into
~/.config/rice/perf.conf, which is what perf-mode / perf.lua already read —
so nothing downstream needed to learn about profiles.
"""
import json
import os

HOME = os.path.expanduser("~")
CONF = os.path.join(HOME, ".config/rice/profiles.json")
PERF_CONF = os.path.join(HOME, ".config/rice/perf.conf")

# every knob a profile owns
FIELDS = ("ANIMATIONS", "BLUR", "CAVA", "WIDGETS",
          "TIMER", "IDLE_SCREEN", "LOGIN_ONLY")

BUILTIN = [
    # name          anim blur cava wid  timer screen login   mode
    ("Balanced",     1,   1,    1,   1,    15,    0,     0, "balanced"),
    ("Saver",        0,   0,    0,   0,     2,    2,     0, "saver"),
    ("Gaming",       1,   0,    0,   0,     0,    0,     0, "balanced"),
]


def _mk(name, anim, blur, cava, wid, timer, screen, login, builtin=True,
        mode="balanced"):
    return {
        "name": name,
        "builtin": builtin,
        "MODE": mode,
        "ANIMATIONS": anim, "BLUR": blur, "CAVA": cava, "WIDGETS": wid,
        "TIMER": timer, "IDLE_SCREEN": screen, "LOGIN_ONLY": login,
    }


def defaults():
    return [_mk(*b) for b in BUILTIN]


def load():
    """Read the profile list; fall back to the three built-ins."""
    if not os.path.exists(CONF):
        return defaults()
    try:
        d = json.load(open(CONF, encoding="utf-8"))
    except (ValueError, OSError):
        return defaults()
    profs = d.get("profiles") or []
    # repair anything a hand-edit or an older version left incomplete
    names = {p.get("name") for p in profs}
    for b in BUILTIN:
        if b[0] not in names:
            profs.append(_mk(*b))
    for p in profs:
        p.setdefault("builtin", False)
        p.setdefault("MODE", "balanced")
        for f in FIELDS:
            p.setdefault(f, 0)
        # A profile whose numbers say "saver" must not claim to be balanced, or
        # perf-mode/status lies about what is actually running.
        if not p.get("ANIMATIONS") and not p.get("BLUR") and not p.get("CAVA") \
                and not p.get("WIDGETS"):
            p["MODE"] = "saver"
    return profs


def save(profs, active=None):
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    tmp = CONF + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"active": active or "", "profiles": profs}, fh,
                  indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, CONF)


def get(profs, name):
    for p in profs:
        if p["name"] == name:
            return p
    return None


def unique_name(profs, base):
    """A free name, so 'Gaming 2' never silently overwrites 'Gaming'."""
    names = {p["name"] for p in profs}
    if base not in names:
        return base
    i = 2
    while "%s %d" % (base, i) in names:
        i += 1
    return "%s %d" % (base, i)


def write_perf_conf(p):
    """Make p the live profile. perf-mode/perf.lua read exactly this file."""
    os.makedirs(os.path.dirname(PERF_CONF), exist_ok=True)
    with open(PERF_CONF, "w", encoding="utf-8") as fh:
        fh.write("# rice: performance profile — from the Performance app\n")
        fh.write("PROFILE=%s\n" % p["name"])
        # Was hardcoded to "balanced" for every profile, which is why the status
        # and the notification could never agree with what the user picked.
        fh.write("MODE=%s\n" % p.get("MODE", "balanced"))
        for f in ("ANIMATIONS", "BLUR", "CAVA", "WIDGETS", "TIMER",
                  "IDLE_SCREEN", "LOGIN_ONLY", "AUTO"):
            fh.write("%s=%s\n" % (f, p.get(f, 0) if f != "AUTO" else 1))
    return PERF_CONF


if __name__ == "__main__":
    for p in load():
        print("%-12s anim=%s blur=%s cava=%s wid=%s timer=%s screen=%s%s"
              % (p["name"], p["ANIMATIONS"], p["BLUR"], p["CAVA"], p["WIDGETS"],
                 p["TIMER"], p["IDLE_SCREEN"],
                 "  (built-in)" if p["builtin"] else ""))
