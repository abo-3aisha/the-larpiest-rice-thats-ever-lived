# Foot terminal + fish: colors from the current wallpaper.
# The single theme engine (palette.py --watch at hyprland boot + apply-wallpaper
# on switches) writes ~/.cache/wal/fish-colors.fish; new shells just source that
# cache. Do NOT regenerate here — that used to add seconds to every terminal.
test -f ~/.cache/wal/fish-colors.fish; and source ~/.cache/wal/fish-colors.fish