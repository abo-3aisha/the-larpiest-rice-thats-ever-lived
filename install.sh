#!/usr/bin/env bash
# install.sh — install this rice on another machine and fix its paths.
#
# Why paths get rewritten instead of using $HOME:
# Hyprland, waybar and swaync execute the strings inside their config files
# literally. A $HOME in a waybar JSON value is NOT expanded, and a $HOME in a
# CSS url() is not expanded either. So the rice ships absolute paths, and this
# script swaps the original username for yours — every path stays absolute, it
# is just absolute for the right person.
#
# Usage:
#   ./install.sh            install the rice into $HOME (rewrites paths)
#   ./install.sh --check    report what would happen, change nothing
#   ./install.sh --force    overwrite files that already exist
#   ./install.sh --uninstall
#                           delete only the files this script installed
set -uo pipefail

OLD_USER="/home/abo3aisha"

R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; C=$'\033[36m'; N=$'\033[0m'
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$1"; }
info() { printf '  %s·%s %s\n' "$C" "$N" "$1"; }

MODE="install"; FORCE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --check)     MODE="check" ;;
        --force)     FORCE=1 ;;
        --uninstall) MODE="uninstall" ;;
        -h|--help)   sed -n '2,16p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) printf 'unknown option: %s\n' "$1" >&2; exit 1 ;;
    esac
    shift
done

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME"

printf '\n%s  hypr-rice installer%s\n' "$C" "$N"
printf '  source      %s\n' "$HERE"
printf '  installing  %s\n\n' "$DEST"

# --- guard: never run this on the machine the rice was authored on ---------
if [ "$DEST" = "$OLD_USER" ]; then
    printf '  %sThis is the rice'"'"'s own machine (%s).%s\n' "$G" "$DEST" "$N"
    printf '  Nothing to install — it is already live here.\n\n'
    exit 0
fi

cd "$HERE" || exit 1

# --- manifest: only these files get installed -------------------------------
# Images are skipped: they are README material, not configuration.
# The adhan is deliberately NOT skipped — the rice needs it to ring.
manifest() {
    git ls-files 2>/dev/null | grep -v -e '^screenshots/' -e '^README\.md$' \
        -e '^install\.sh$' -e '^requirements\.sh$' -e '^CHANGELOG\.md$' \
        -e '^\.git/' -e '\.webp$' -e '\.png$' -e '\.jpg$'
}

if [ "$MODE" = "uninstall" ]; then
    n=0
    while IFS= read -r rel; do
        [ -n "$rel" ] || continue
        tgt="$DEST/$rel"
        if [ -f "$tgt" ]; then rm -f "$tgt"; n=$((n+1)); fi
        # prune directories we created, if they end up empty
        d="$(dirname "$tgt")"
        [ -d "$d" ] && rmdir -p --ignore-fail-on-non-empty "$d" 2>/dev/null
    done < <(manifest)
    printf '  %sremoved %d files%s from %s\n\n' "$G" "$n" "$N" "$DEST"
    printf '  Nothing else was touched. Restart your session to undo any live changes.\n\n'
    exit 0
fi

installed=0; untouched=0; conflicts=0; fixed=0
missing_dirs=()

while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    src="$HERE/$rel"
    tgt="$DEST/$rel"
    [ -f "$src" ] || continue

    if [ -e "$tgt" ] || [ -L "$tgt" ]; then
        if [ "$FORCE" -eq 0 ]; then
            conflicts=$((conflicts+1))
            warn "exists, not touched: $rel  (--force to replace)"
            continue
        fi
        rm -f "$tgt"
    fi

    d="$(dirname "$tgt")"
    if [ ! -d "$d" ]; then
        mkdir -p "$d" 2>/dev/null || { bad "cannot write $d"; continue; }
        missing_dirs+=("$d")
    fi

    if [ "$MODE" = "check" ]; then
        if grep -q "$OLD_USER" "$src" 2>/dev/null; then
            info "would install + fix paths: $rel"
            fixed=$((fixed+1))
        else
            info "would install: $rel"
        fi
        installed=$((installed+1))
        continue
    fi

    cp -a "$src" "$tgt" 2>/dev/null || { bad "failed: $rel"; continue; }
    if grep -q "$OLD_USER" "$tgt" 2>/dev/null; then
        sed -i "s|$OLD_USER|$DEST|g" "$tgt" 2>/dev/null && fixed=$((fixed+1))
    fi
    installed=$((installed+1))
done < <(manifest)

printf '\n'
if [ "$MODE" = "check" ]; then
    printf '  %s%d files would be installed, %d of them with paths rewritten%s\n' \
        "$G" "$installed" "$fixed" "$N"
else
    printf '  %s%d files installed%s' "$G" "$installed" "$N"
    printf ', %d with paths rewritten\n' "$fixed"
fi
[ "$conflicts" -gt 0 ] && printf '  %s%d left alone because they already existed%s\n' "$Y" "$conflicts" "$N"
[ "${#missing_dirs[@]}" -gt 0 ] && printf '  %s%d directories created%s\n' "$C" "${#missing_dirs[@]}" "$N"
echo

# --- dependencies: report, never silently install 40 packages --------------
missing=""
have() { command -v "$1" >/dev/null 2>&1 || missing="$missing $2"; }
pkg()  { pacman -Qq "$1" >/dev/null 2>&1 || missing="$missing $1"; }

have hyprlock hyprlock;   have hypridle hypridle
have hyprpaper hyprpaper; have hyprpicker hyprpicker
have swaync-client swaync; have wlogout wlogout
have mpvpaper mpvpaper;   have awww awww;    have swww swww
have hyprshot hyprshot;   have grim grim;    have slurp slurp
have playerctl playerctl; have pactl wireplumber; have wpctl wireplumber
have brightnessctl brightnessctl; have gammastep gammastep
have amixer alsa-utils;   have cliphist cliphist; have wtype wtype
have qrencode qrencode;   have jq jq;    have killall psmisc
have wf-recorder wf-recorder
pkg waybar; pkg cava; pkg fish; pkg foot; pkg contour; pkg kitty; pkg dolphin
pkg python-gobject; pkg gtk-layer-shell; pkg wl-clipboard
pkg qt6ct; pkg ffmpeg; pkg mpv; pkg imv; pkg ttf-jetbrains-mono-nerd

printf '  %sDependencies%s\n' "$C" "$N"
if [ -z "$missing" ]; then
    ok "everything this rice needs is installed"
else
    warn "missing:$missing"
    printf '     sudo pacman -S%s\n' "$missing"
    printf '     or run ./requirements.sh to install ALL of them (repos + AUR) automatically\n'
fi
echo

# --- things no script can carry across machines ---------------------------
printf '  %sTo finish, by hand%s\n' "$C" "$N"
cat <<'EOF'
     1. Log out and back in so Hyprland reads the new files.
     2. Check your monitor name:   hyprctl monitors
        The rice assumes eDP-1; edit ~/.config/hypr/hyprland.lua if different.
     3. Adhan: the audio is in the repo, but ~/.config/prayer/times.conf
        defaults to Damascus. Edit it, or set AUTO=0 to stop the automatic
        location lookup from overwriting it.
     4. After editing anything in ~/.config/hypr/:   hyprctl reload
     5. Acer Nitro AN515-57 only: sudo ~/.local/bin/fix-kbd-backlight
        (fixes Fn+F9/F10 dimming the screen instead of the keyboard), reboot.
EOF
printf '\n'