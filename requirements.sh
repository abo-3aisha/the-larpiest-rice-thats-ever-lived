#!/usr/bin/env bash
# requirements.sh — install every tool this rice needs, freshly and safely.
#
#   ./requirements.sh            install everything (pacman repos first, AUR
#                                from yay when the package is not in any repo)
#   ./requirements.sh --check    print what would be installed, change nothing
#   ./requirements.sh --optional also install the optional extras below
#   ./requirements.sh --yes      skip the confirmation prompt
#   ./requirements.sh --help     this message
#
# Design:
#   * Idempotent — a package that is already installed is skipped.
#   * Repository-first — each name is tried against the enabled pacman repos
#     (base + CachyOS) and only falls back to yay (or cachyos-yay) when pacman
#     cannot see it. That way a package like `awww` or `hyprshot`, which lives
#     in a repo on some distros and only in the AUR on others, resolves on
#     both without you having to know which.
#   * The compositor is CachyOS's Lua build (cachyos-hypr-noctalia). It is the
#     `hl.*` Lua API this Hyprland config is written against — upstream
#     `hyprland` cannot run hyprland.lua. On plain Arch the script says so
#     loudly instead of silently installing the wrong thing.
#   * Only Arch-family distros are supported (pacman).

set -uo pipefail

R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; C=$'\033[36m'; N=$'\033[0m'
say() { printf '  %s%s%s\n' "$C" "$1" "$N"; }
ok()  { printf '  %s%s%s\n' "$G" "$1" "$N"; }
warn(){ printf '  %s%s%s\n' "$Y" "$1" "$N"; }
bad() { printf '  %s%s%s\n' "$R" "$1" "$N"; }

MODE="install"; EXTRA=0; YES=0
while [ $# -gt 0 ]; do
    case "$1" in
        --check)   MODE="check" ;;
        --optional) EXTRA=1 ;;
        --yes)     YES=1 ;;
        --help|-h) sed -n '2,22p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) bad "unknown option: $1 (see --help)"; exit 1 ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# Distro guard
# ---------------------------------------------------------------------------
if ! command -v pacman >/dev/null 2>&1; then
    bad "This rice is Arch-family only (pacman). Nothing was installed."
    exit 1
fi
IS_CACHYOS=0
[ -f /etc/os-release ] && grep -qi "cachyos" /etc/os-release && IS_CACHYOS=1

# Pick the AUR helper. cachyos-yay is the CachyOS-wrapped yay; anything with a
# working `-S` works here. If none exists, bootstrap yay from the AUR.
AUX=""
for c in cachyos-yay yay paru; do
    if command -v "$c" >/dev/null 2>&1; then AUX="$c"; break; fi
done
if [ -z "$AUX" ]; then
    if [ "$MODE" = "check" ]; then
        warn "no AUR helper found (yay/paru missing) — needed for: AUR packages"
    else
        say "No AUR helper — bootstrapping yay (git clone + makepkg -si)…"
        TMP="$(mktemp -d)"
        git clone --depth=1 https://aur.archlinux.org/yay.git "$TMP/yay" >/dev/null 2>&1 \
            || { bad "AUR helper bootstrap failed (needs git + base-devel). Install yay, then re-run."; exit 1; }
        ( cd "$TMP/yay" && makepkg -si --noconfirm ) || { bad "yay build failed."; exit 1; }
        rm -rf "$TMP"
        AUX="yay"
        ok "yay installed."
    fi
fi
[ "$MODE" = "check" ] && AUX="${AUX} (available)"

# ---------------------------------------------------------------------------
# The package list.
# ---------------------------------------------------------------------------
# Compose every name the scripts + configs call directly. A name here is a
# real binary/package the rice invokes at runtime — nothing is here "just in
# case". pacman repos are tried first, yay only when pacman cannot see it, so
# any of these may live in a repo or in the AUR and still resolve.
NEED=(
    # compositor + the wm tools
    hyprlock hypridle hyprpaper hyprpicker
    waybar swaync wofi wlogout cava fastfetch swaybg
    # xdg portals + the polkit agent (hyprland.conf exec-once)
    xdg-desktop-portal xdg-desktop-portal-hyprland xdg-desktop-portal-gtk polkit-gnome
    # clipboard / emoji / picker / wifi-share / search + screenshots
    wl-clipboard cliphist wtype hyprshot qrencode grim slurp
    # audio + video pipeline (video wallpapers, adhan, remux, recording)
    pipewire pipewire-pulse wireplumber libpulse alsa-utils
    ffmpeg mpv mpvpaper wf-recorder
    # wallpaper daemons (awww primary; swww + swaybg fallbacks)
    awww swww
    # input + desktop control
    playerctl brightnessctl networkmanager bluez bluez-utils gammastep
    # python runtime the widget kit runs on
    python python-gobject python-pillow python-cairo gtk-layer-shell
    # Qt/GTK theming the palette engine drives
    qt6ct breeze-gtk
    # terminals + app launcher + file manager
    fish foot contour kitty dolphin
    # misc runtime binaries the scripts call directly
    libnotify jq psmisc glib2 xdg-utils imv
    # fonts: waybar/swaync/wofi glyph icons + Arabic + emoji
    ttf-jetbrains-mono-nerd noto-fonts noto-fonts-emoji
)

# AUR-only packages (no repo copy on any release the script knows about).
AUR=(
    wl-screenrec    # screen-rec: NVENC-capable fallback behind wf-recorder
    sweet-cursors   # the cursor the rice sets (variables.lua -> cursorTheme)
)

# Nice-but-not-required apps. Shipped configs reference them, but the rice
# runs fine without them. Enable with --optional.
OPTIONAL=(
    thunar gwenview satty papirus-icon-theme gnome-keyring
    wezterm ghostty alacritty
    eza zoxide direnv starship bat ripgrep fzf micro
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
is_installed() { pacman -Qq "$1" >/dev/null 2>&1; }
in_repo()      { pacman -Si "$1" >/dev/null 2>&1; }

want() { # want <pkg> <is-aur?>
    local p="$1"
    if is_installed "$p"; then
        [ "$MODE" = "check" ] && ok "  already installed: $p"
        return 0
    fi
    local src="repo"
    in_repo "$p" || src="AUR"
    if [ "$MODE" = "check" ]; then
        say "  would install ($src): $p"
        return 0
    fi
    if [ "$src" = "repo" ]; then
        sudo pacman -S --noconfirm --needed "$p" >/dev/null 2>&1 \
            && ok "  ${G}installed (repo): $p" \
            || { bad "  failed (repo): $p"; return 1; }
    else
        "$AUX" -S --noconfirm --needed "$p" >/dev/null 2>&1 \
            && ok "  installed (AUR/$AUX): $p" \
            || { bad "  failed (AUR): $p"; return 1; }
    fi
}

# ---------------------------------------------------------------------------
# Compositor — special case, never silently wrong
# ---------------------------------------------------------------------------
COMP="cachyos-hypr-noctalia"
if ! is_installed hyprland && ! is_installed "$COMP"; then
    if in_repo "$COMP"; then
        say "Compositor: $COMP (CachyOS Lua Hyprland)"
        if [ "$MODE" = "check" ]; then say "  would install (repo): $COMP"; else
            sudo pacman -S --noconfirm --needed "$COMP" >/dev/null 2>&1 \
                && ok "  installed: $COMP" || bad "  failed: $COMP"
        fi
    else
        warn "Compositor: $COMP is NOT found in your repos."
        warn "  This config is written against the Lua Hyprland build —"
        warn "  upstream 'hyprland' cannot run hl.* (hyprland.lua/rules.lua)."
        warn "  On CachyOS:  sudo pacman -S cachyos-hypr-noctalia"
        if is_installed hyprland; then
            warn "  vanilla 'hyprland' is present but the Lua config will not work."
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Confirm, then install
# ---------------------------------------------------------------------------
if [ "$MODE" = "install" ] && [ "$YES" -eq 0 ]; then
    echo
    warn "This will install the rice's required packages"
    warn "(${#NEED[@]} pacman/AUR + ${#AUR[@]} AUR-only; optional extras add ${#OPTIONAL[@]})."
    printf '  Continue? [y/N] '
    read -r ANS || exit 1
    case "$ANS" in
        y|Y|yes|YES) ;;
        *) say "Aborted."; exit 0 ;;
    esac
fi

plan() {
    for p in "${NEED[@]}"; do want "$p" || true; done
    for p in "${AUR[@]}";  do want "$p" || true; done
}
if [ "$MODE" = "check" ]; then
    plan
    echo
    if [ "$EXTRA" -eq 1 ]; then
        say "Optional (--optional):"
        for p in "${OPTIONAL[@]}"; do want "$p" || true; done
    else
        say "Optional extras not included. Re-run with --optional to install them:"
        say "    ${OPTIONAL[*]}"
    fi
    echo
    warn "Nothing was changed. Run ./requirements.sh without --check to install."
    exit 0
fi

plan

if [ "$EXTRA" -eq 1 ]; then
    say "Optional extras:"
    for p in "${OPTIONAL[@]}"; do want "$p" || true; done
fi

# ---------------------------------------------------------------------------
# Post-install
# ---------------------------------------------------------------------------
if command -v fc-cache >/dev/null 2>&1; then
    fc-cache -f >/dev/null 2>&1 && ok "font cache rebuilt (nerd glyphs will render)."
fi

cat <<EOF

  ${C}Done.${N} Now:
    1. ./install.sh          — copy the rice files + rewrite paths (absolutely safe)
    2. Re-login (Hyprland reads the new files) — or restart it from tty.
    3. sudo systemctl enable --now bluetooth      (only if you use BT)
    4. Acer Nitro AN515-57 only: sudo ~/.local/bin/fix-kbd-backlight + reboot
    5. The adhan defaults to Damascus — edit ~/.config/prayer/times.conf
       (or set AUTO=0 so location lookup can't overwrite it).

  Tips:
    - Anything in the AUR section came through yay; keep it updated with:
        $AUX -Syu
    - If you did NOT get the Noctalia compositor, the Lua config will not
      load. On CachyOS: sudo pacman -S cachyos-hypr-noctalia
EOF
exit 0