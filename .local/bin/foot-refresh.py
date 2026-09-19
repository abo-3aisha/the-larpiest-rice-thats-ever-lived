#!/usr/bin/env python3
# foot-refresh — terminal-only fast color sync.
# There is now ONE theme engine: ~/.config/hypr/themes/palette.py (builds the
# theme, runs wal itself, writes WAYBAR+swaync+wofi+foot+fish+fastfetch+cava+gtk).
# This thin CLI only re-applies the terminal/fish/GTK pieces after a terminal
# opens — cheap, never restarts waybar, and can't drift from the main palette.
import importlib.util
import sys

SPEC = "/home/abo3aisha/.config/hypr/themes/palette.py"


def main():
    sys.argv = ["palette.py"]
    spec = importlib.util.spec_from_file_location("palette", SPEC)
    P = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(P)
    except SystemExit:
        pass

    args = set(sys.argv[1:])
    force = "--force" in args

    wall = P.current_wallpaper()
    if not wall or not os.path.exists(wall):
        return
    P.ensure_wal(wall, force)
    theme = P.build_palette(wall)
    P.sync_foot(theme)
    P.write_fish_colors(theme)
    P.write_gtk_accent(theme)


if __name__ == "__main__":
    import os  # noqa: WPS  (kept local so palette.py imports stay unaffected)
    main()