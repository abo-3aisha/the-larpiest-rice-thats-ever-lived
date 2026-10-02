#!/usr/bin/env python3
"""i18n — translation engine for the rice.

Design contract (user requirement):
  * Every language file is SELF-CONTAINED. A missing key NEVER falls back to
    English — it surfaces as the raw key so the gap is visible instead of
    silently mixing two languages. `i18n-check` enforces parity.
  * Date / time names come from the language file itself, not from the host
    locale, so Arabic day names work even without ar_SY installed.

CLI:
  i18n.py get KEY            print one string
  i18n.py dump               print every key as `T_<KEY>='...'` (bash-evalable)
  i18n.py lang               print the active language code (en/ar/fr/es)
  i18n.py name               print the active language's own name
  i18n.py rtl                print 1 for a right-to-left language, else 0
  i18n.py list               list available languages
  i18n.py format CLOCKFMT... render now using the active language's names
  i18n.py check              verify every language file has the same key set
"""
import os
import sys
import time

HOME = os.path.expanduser("~")
DIR = os.path.join(HOME, ".local/share/rice-lang")
CONF = os.path.join(HOME, ".config/rice/i18n.conf")
DEFAULT = "en"


def parse(path):
    d = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                    v = v[1:-1]
                d[k.strip()] = v.replace('\\"', '"')
    except OSError:
        pass
    return d


def available():
    out = []
    try:
        for f in sorted(os.listdir(DIR)):
            if f.endswith(".conf"):
                out.append(f[:-5])
    except OSError:
        pass
    return out or [DEFAULT]


def active():
    lang = _conf_val("LANG") or DEFAULT
    return lang if lang in available() else DEFAULT


def _conf_val(key):
    try:
        with open(CONF, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return None


def conf(lang=None):
    """Read ~/.config/rice/i18n.conf as a plain dict (LANG, CLOCK, TZ, ...)."""
    d = {}
    try:
        with open(CONF, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return d


def locale_code(lang=None):
    """The system locale this language should run under, e.g. ar_SY.UTF-8."""
    return table(lang or active()).get("CODE", "")


def table(lang=None):
    return parse(os.path.join(DIR, (lang or active()) + ".conf"))


def t(key, lang=None):
    """Translate. Never falls back to another language."""
    return table(lang).get(key, key)


def bash_dump(lang=None):
    tab = table(lang)
    out = []
    for k in sorted(tab):
        v = tab[k].replace("'", "'\\''")
        out.append("T_%s='%s'" % (k, v))
    return "\n".join(out)


# ---------------------------------------------------------------- dates --
WD_SHORT = ["WD_MON", "WD_TUE", "WD_WED", "WD_THU", "WD_FRI", "WD_SAT", "WD_SUN"]


def _names(tab):
    wd = [tab.get(k, k) for k in WD_SHORT]          # index 0 = Monday
    mo = [tab.get("MONTH_%d" % i, str(i)) for i in range(1, 13)]
    ms = [tab.get("MSHORT_%d" % i, str(i)) for i in range(1, 13)]
    dy = [tab.get("DAY_%d" % i, str(i)) for i in range(0, 7)]
    return wd, mo, dy, ms


def render(fmt, lang=None, now=None):
    """Render strftime-style format using the language's OWN day/month names.

    Supported: %H %I %M %S %p %d %m %y %Y %A %a %B %b %Z  and literal %%
    """
    tab = table(lang)
    wd, mo, dy, ms = _names(tab)
    lt = time.localtime(now)
    # python weekday(): Monday=0 ; our DAY_0 is also Monday.
    dow = lt.tm_wday

    def ampm():
        # Every language supplies its own meridiem, so %p can never leak an
        # English "AM/PM" into a non-English UI. Missing = the key itself,
        # which is loud enough to notice rather than silently mixing.
        return tab.get("AM" if lt.tm_hour < 12 else "PM",
                       "AM" if lt.tm_hour < 12 else "PM")

    table_map = {
        "H": "%02d" % lt.tm_hour,
        "I": "%02d" % (lt.tm_hour % 12 or 12),
        "M": "%02d" % lt.tm_min,
        "S": "%02d" % lt.tm_sec,
        "p": ampm(),
        "d": "%02d" % lt.tm_mday,
        "e": "%d" % lt.tm_mday,
        "m": "%02d" % lt.tm_mon,
        "y": "%02d" % (lt.tm_year % 100),
        "Y": "%d" % lt.tm_year,
        "A": dy[dow],
        "a": wd[dow],
        "B": mo[lt.tm_mon - 1],
        "b": ms[lt.tm_mon - 1],
        "Z": time.strftime("%Z"),
    }

    out = []
    i = 0
    while i < len(fmt):
        c = fmt[i]
        if c == "%" and i + 1 < len(fmt):
            nxt = fmt[i + 1]
            if nxt == "%":
                out.append("%")
            else:
                out.append(table_map.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ----------------------------------------------------------------- main --
def main(argv):
    if len(argv) < 2:
        print("i18n: need a command", file=sys.stderr)
        return 2
    cmd, rest = argv[1], argv[2:]
    lang = active()

    if cmd == "get":
        if not rest:
            return 2
        sys.stdout.write(t(rest[0]) + "\n")
    elif cmd == "dump":
        sys.stdout.write(bash_dump() + "\n")
    elif cmd == "lang":
        print(lang)
    elif cmd == "name":
        print(t("NAME"))
    elif cmd == "rtl":
        print("1" if t("RTL") == "1" else "0")
    elif cmd == "list":
        print(" ".join(available()))
    elif cmd == "format":
        # no argument = use the CLOCK format from the rice config (lock screen,
        # widgets, anything that just wants "the clock the way I set it up")
        if not rest or rest[0] in ("--date", "-d"):
            key = "DATE" if rest and rest[0] in ("--date", "-d") else "CLOCK"
            fmt = _conf_val(key) or ("%a, %b %d" if key == "DATE" else "%I:%M %p")
        else:
            fmt = rest[0]
        print(render(fmt))
    elif cmd == "check":
        return _check()
    else:
        print("i18n: unknown command %r" % cmd, file=sys.stderr)
        return 2
    return 0


def _check():
    langs = available()
    ref = set(table("en").keys())
    bad = 0
    for lang in langs:
        keys = set(table(lang).keys())
        missing = sorted(ref - keys)
        extra = sorted(keys - ref)
        if missing or extra:
            bad = 1
            print("%s: %d missing %s" % (lang, len(missing), missing[:6]))
            if extra:
                print("%s: %d extra %s" % (lang, len(extra), extra[:6]))
    print("%d languages, %d keys each — %s"
          % (len(langs), len(ref), "OK" if not bad else "INCOMPLETE"))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))