-- ============================================================
-- Hyprland Lua Config — Minimal & Clean
-- ============================================================

local HOME = (os and os.getenv and os.getenv("HOME")) or "/home/abo3aisha"

local ok_theme = pcall(dofile, HOME .. "/.config/hypr/theme.lua")

if not ok_theme or not THEME then
    THEME = {
        mode = "dark",
        bg = "17171a",
        surface = "2a2a2c",
        fg = "eff1f4",
        fg_dim = "a6a9b0",
        accent = "dfdfdf",
        accent2 = "dfdfdf",
        on_accent = "111113",
        border_active = "dfdfdf",
        border_inactive = "a9a9a9",
        shadow = "eeeeee",
    }
end

------------------
---- MONITORS ----
------------------

hl.monitor({
    output   = "eDP-1",
    mode     = "1920x1080@144",
    position = "auto",
    scale    = 1,
})

hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "auto",
})


-------------------
---- AUTOSTART ----
-------------------

hl.on("hyprland.start", function()
    hl.exec_cmd("dbus-update-activation-environment --systemd --all")
    hl.exec_cmd("systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")

    -- Wallpaper (swaybg preferred, hyprpaper fallback)
    hl.exec_cmd("/home/abo3aisha/.local/bin/apply-wallpaper")

    -- Top bar
    hl.exec_cmd("waybar")

    -- Miku desktop pet (floats on workspace 1)
    hl.exec_cmd("/home/abo3aisha/.local/bin/miku-pet")

    -- Notifications
    hl.exec_cmd("swaync")

    -- Idle / auto-lock
    hl.exec_cmd("hypridle")

    -- Clipboard
    hl.exec_cmd("wl-paste --type text --watch cliphist store")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")

    -- Polkit
    hl.exec_cmd("hyprpolkitagent")

    -- Material-You theme engine (applies current wallpaper palette + watches changes)
    hl.exec_cmd("sh -c 'setsid python3 $HOME/.config/hypr/themes/palette.py --watch >/tmp/palette.log 2>&1 &'")
end)


-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------

hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")
hl.env("XCURSOR_THEME", "Bibata-Modern-Ice")
hl.env("HYPRCURSOR_THEME", "Bibata-Modern-Ice")

hl.env("GBM_BACKEND", "nvidia-drm")
hl.env("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
hl.env("WLR_NO_HARDWARE_CURSORS", "1")


-----------------------
---- LOOK AND FEEL ----
-----------------------

hl.config({
    general = {
        gaps_in     = 6,
        gaps_out    = 18,
        border_size = 0,
        layout      = "dwindle",
        resize_on_border = true,
        allow_tearing = true,

        col = {
            active_border   = "rgba(" .. THEME.accent .. "ff)",
            inactive_border = "rgba(" .. THEME.border_inactive .. "aa)",
        },
    },
})

hl.config({
    decoration = {
        rounding       = 20,
        rounding_power = 3,

        active_opacity   = 1.0,
        inactive_opacity = 0.85,

        shadow = {
            enabled      = true,
            range        = 12,
            render_power = 3,
            color        = "rgba(" .. THEME.shadow .. "40)",
        },

        blur = {
            enabled   = true,
            size      = 8,
            passes    = 2,
            vibrancy  = 0.15,
            xray      = false,
            popups    = true,
        },
    },
})

hl.config({
    animations = {
        enabled = true,
    },
})

hl.curve("easeOutQuint",   { type = "bezier", points = { {0.23, 1},    {0.32, 1}    } })
hl.curve("easeInOutCubic", { type = "bezier", points = { {0.65, 0.05}, {0.36, 1}    } })
hl.curve("linear",         { type = "bezier", points = { {0, 0},       {1, 1}       } })
hl.curve("almostLinear",   { type = "bezier", points = { {0.5, 0.5},   {0.75, 1}    } })
hl.curve("quick",          { type = "bezier", points = { {0.15, 0},    {0.1, 1}     } })
hl.curve("easy",           { type = "spring", mass = 0.85, stiffness = 220, dampening = 24 })
hl.curve("buttery",        { type = "spring", mass = 0.75, stiffness = 320, dampening = 30 })

hl.animation({ leaf = "global",        enabled = true,  speed = 8,    bezier = "default" })
hl.animation({ leaf = "border",        enabled = true,  speed = 5,    bezier = "easeOutQuint" })
hl.animation({ leaf = "windows",       enabled = true,  speed = 4.5,  spring = "buttery" })
hl.animation({ leaf = "windowsIn",     enabled = true,  speed = 3.6,  spring = "easy",        style = "popin 82%" })
hl.animation({ leaf = "windowsOut",    enabled = true,  speed = 1.4,  spring = "easy",        style = "popin 82%" })
hl.animation({ leaf = "fadeIn",        enabled = true,  speed = 2.2,  bezier = "almostLinear" })
hl.animation({ leaf = "fadeOut",       enabled = true,  speed = 1.6,  bezier = "almostLinear" })
hl.animation({ leaf = "fade",          enabled = true,  speed = 3,    bezier = "quick" })
hl.animation({ leaf = "layers",        enabled = true,  speed = 3.5,  bezier = "easeOutQuint" })
hl.animation({ leaf = "layersIn",      enabled = true,  speed = 4,    bezier = "easeOutQuint", style = "fade" })
hl.animation({ leaf = "layersOut",     enabled = true,  speed = 1.5,  bezier = "linear",      style = "fade" })
hl.animation({ leaf = "fadeLayersIn",  enabled = true,  speed = 2,    bezier = "almostLinear" })
hl.animation({ leaf = "fadeLayersOut", enabled = true,  speed = 1.5,  bezier = "almostLinear" })
hl.animation({ leaf = "workspaces",    enabled = true,  speed = 1.8,  bezier = "easeOutQuint", style = "slide" })
hl.animation({ leaf = "workspacesIn",  enabled = true,  speed = 1.6,  bezier = "easeOutQuint", style = "slide" })
hl.animation({ leaf = "workspacesOut", enabled = true,  speed = 1.8,  bezier = "easeOutQuint", style = "slide" })
-- Super+K drawer: smooth slide+fade for open/close.
-- NOTE: `popin` (zoom) is NOT a valid style for this leaf on this Hyprland
-- ("unknown style"); the only known-good style here is slidefade/slidefadevert.
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 1.6, bezier = "easeOutQuint", style = "slidefadevert 15%" })


----------------
---- LAYOUT ----
----------------

hl.config({
    dwindle = {
        preserve_split = true,
    },
})


----------------
----  MISC  ----
----------------

hl.config({
    misc = {
        force_default_wallpaper = -1,
        disable_hyprland_logo   = true,
        disable_splash_rendering = true,
        mouse_move_enables_dpms = true,
        key_press_enables_dpms  = true,
        font_family = "JetBrainsMono Nerd Font",

        -- Live lockscreen: keep rendering the desktop below hyprlock
        -- (so a playing video keeps moving) + blur that live backdrop.
        session_lock_xray = true,
        session_lock_blur = true,
    },
})


---------------
---- INPUT ----
---------------

hl.config({
    input = {
        kb_layout  = "us,ara",
        kb_options = "grp:alt_shift_toggle",
        follow_mouse = 1,
        sensitivity = 0,
        touchpad = {
            natural_scroll = false,
        },
    },
})

hl.config({
    cursor = {
        no_warps = true,
    },
})


---------------------
---- KEYBINDINGS ----
---------------------

local mainMod = "SUPER"

-- === FX EXEMPTIONS: games & video stay crisp (no blur/opacity) ===

hl.window_rule({ match = { class = "mpv|vlc|celluloid|motion|mkvtoolnix-gui" }, no_blur = true, opaque = true })
hl.window_rule({ match = { class = "steam|steam_app_|steamwebhelper|gamescope|.*%.exe" }, no_blur = true, opaque = true, idle_inhibit = "always" })
hl.window_rule({ match = { fullscreen = true }, no_blur = true, opaque = true })

-- === NOW PLAYING PANEL (top dropdown bar) ===

hl.window_rule({ match = { class = "nowpanel" }, float = true, size = "1160 300", move = "(monitor_w-1160)*0.5 (monitor_h-300)*0.5", rounding = 18, border_size = 1 })

-- === MIKU DESKTOP PET (floating, bottom-right, no decorations) ===

hl.window_rule({ match = { class = "miku-pet" }, float = true, size = "336 414", move = "(monitor_w-336-32) (monitor_h-414-22)" })

-- === WALLPAPER (Super+W) ===

hl.bind(mainMod .. " + W", hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/pick-wallpaper"))
hl.bind(mainMod .. " + SHIFT + W", hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/cycle-wallpaper toggle"))

-- === SCREENSHOTS ===

local shot = "/home/abo3aisha/.local/bin/screenshot.sh"
hl.bind("PRINT",                 hl.dsp.exec_cmd(shot .. " region"))
hl.bind(mainMod .. " + PRINT",   hl.dsp.exec_cmd(shot .. " output"))
hl.bind("ALT + PRINT",           hl.dsp.exec_cmd(shot .. " window"))
hl.bind("CTRL + PRINT",          hl.dsp.exec_cmd(shot .. " output"))

-- === ESSENTIAL APPS ===

hl.bind(mainMod .. " + SPACE",  hl.dsp.exec_cmd("wofi --show drun"))
hl.bind(mainMod .. " + T",      hl.dsp.exec_cmd("foot"))
hl.bind(mainMod .. " + E",      hl.dsp.exec_cmd("thunar"))
hl.bind(mainMod .. " + B",          hl.dsp.exec_cmd("cycle-power"))
hl.bind(mainMod .. " + SHIFT + B", hl.dsp.exec_cmd("firefox"))
hl.bind(mainMod .. " + RETURN", hl.dsp.exec_cmd("foot"))

-- === WINDOW MANAGEMENT ===

hl.bind(mainMod .. " + Q",      hl.dsp.window.close())
hl.bind(mainMod .. " + V",      hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + F",      hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }))
-- Mirror tiled windows left<->right on the active workspace
hl.bind(mainMod .. " + D", function()
    local aws = hl.get_active_workspace()
    if not aws then return end
    local act = hl.get_active_window()
    if not act or act.floating then return end
    local mon = hl.get_active_monitor()
    if not mon or not act.at or not act.size then return end

    local mx = mon.x + mon.width / (2 * (mon.scale or 1))
    local acx = act.at.x + act.size.x / 2
    if acx >= mx then
        hl.dispatch(hl.dsp.window.move({ direction = "left" }))
    else
        hl.dispatch(hl.dsp.window.move({ direction = "right" }))
    end
end)
hl.bind(mainMod .. " + SHIFT + E", hl.dsp.exec_cmd("wlogout"))
hl.bind(mainMod .. " + N", hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/notif-center"))
hl.bind(mainMod .. " + S", hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/ctrl-center"))

-- Focus
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }))

-- Workspaces
for i = 1, 10 do
    local key = i % 10
    hl.bind(mainMod .. " + " .. key,         hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

-- Mouse
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Multimedia / Fn row — all routed through fn-key for OSD notifications
hl.bind("XF86AudioRaiseVolume",  hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key vol-up"),      { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume",  hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key vol-down"),    { locked = true, repeating = true })
hl.bind("XF86AudioMute",         hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key vol-mute"),    { locked = true, repeating = true })
-- SCREEN brightness (comes from the "Video Bus" ACPI device).
-- NOTE: the AN515-57 keyboard-backlight scancodes 0xef/0xf0 are fixed in the
-- systemd hwdb (see /etc/udev/hwdb.d/70-acer-nitro-an515-57-kbd.hwdb), so they
-- no longer leak in here as XF86MonBrightness*.
hl.bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key bright-up"),   { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key bright-down"), { locked = true, repeating = true })
hl.bind("XF86AudioMicMute",      hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key mic-mute"),    { locked = true, repeating = true })
-- Fn extras: touchpad, airplane (radio), display switch, keyboard backlight
hl.bind("XF86TouchpadToggle",    hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key touchpad"))
hl.bind("XF86TouchpadOn",        hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key touchpad-on"))
hl.bind("XF86TouchpadOff",       hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key touchpad-off"))
hl.bind("XF86WLAN",              hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key airplane"))
hl.bind("XF86RFKill",            hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key airplane"))
hl.bind("XF86Display",           hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key display"))
hl.bind("XF86KbdBrightnessUp",   hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key kbd-up"),      { locked = true, repeating = true })
hl.bind("XF86KbdBrightnessDown", hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key kbd-down"),    { locked = true, repeating = true })
hl.bind("XF86KbdLightOnOff",     hl.dsp.exec_cmd("/home/abo3aisha/.local/bin/fn-key kbd-toggle"))

-- === MEDIA / MIC KEYS (your hardware keys) ===

hl.bind("XF86AudioPlay",    hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPause",   hl.dsp.exec_cmd("playerctl pause"),      { locked = true })
hl.bind("XF86AudioNext",    hl.dsp.exec_cmd("playerctl next"),       { locked = true })
hl.bind("XF86AudioPrev",    hl.dsp.exec_cmd("playerctl previous"),   { locked = true })
hl.bind("XF86AudioStop",    hl.dsp.exec_cmd("playerctl stop"),       { locked = true })
-- (mic mute is handled in the Fn-row block above, via fn-key)

-- === COLOR PICKER (Super+Shift+C) ===

hl.bind(mainMod .. " + SHIFT + C", hl.dsp.exec_cmd("hyprpicker -a"))

-- === CLIPBOARD HISTORY (Super+C) ===

hl.bind(mainMod .. " + C", hl.dsp.exec_cmd("clipboard-history"))

-- === LOCK (Super+L) ===

hl.bind(mainMod .. " + L", hl.dsp.exec_cmd("hyprlock"))

-- === DISCORD LAYER (Super+K) ===
-- Caelestia-style drawer: Discord lives on the special:communication workspace
-- (rules.lua already tags "discord|equibop|vesktop" onto it). SUPER+K shows the
-- drawer (launching Discord if needed) and hides it again. Done natively in Lua
-- because HyprMod HIJACKS `hyprctl dispatch` (the old shell script's dispatch
-- calls silently did nothing) — like logout-menu, display-switch.

hl.bind(mainMod .. " + K", function()
    local shown = false
    local aws = hl.get_active_special_workspace()
    if aws and aws.name and tostring(aws.name) == "special:communication" then
        shown = true
    end

    if shown then
        hl.dispatch(hl.dsp.workspace.toggle_special("communication"))
        return
    end

    -- Move any running Discord window into the drawer, else launch one.
    local found = false
    for _, w in ipairs(hl.get_windows() or {}) do
        local c = (w and w.class and tostring(w.class):lower()) or ""
        if c:find("discord") or c:find("equibop") or c:find("vesktop") then
            found = true
            local ws = (w.workspace and w.workspace.name) or ""
            if ws ~= "special:communication" then
                hl.dispatch(hl.dsp.window.move({ window = w, workspace = "special:communication", follow = false }))
            end
        end
    end
    if not found then
        hl.dispatch(hl.dsp.exec_cmd(
            "sh -c 'for c in equibop vesktop discord; do command -v $c >/dev/null 2>&1 && exec $c; done'",
            { workspace = "special:communication" }))
    end

    hl.dispatch(hl.dsp.focus({ workspace = "special:communication" }))
end)

hl.bind(mainMod .. " + ALT + K", function()
    local aws = hl.get_active_special_workspace()
    if aws and aws.name and tostring(aws.name) == "special:communication" then
        hl.dispatch(hl.dsp.workspace.toggle_special("communication"))
    end
end)

-- === EMOJI PICKER (Super + numpad0) ===
-- Bound twice because numpad0 reports KP_Insert with NumLock off and KP_0 with it on.

hl.bind(mainMod .. " + KP_Insert", hl.dsp.exec_cmd("emoji-picker"))
hl.bind(mainMod .. " + KP_0",      hl.dsp.exec_cmd("emoji-picker"))

-- HyprMod managed settings
require("hyprland-gui")

-- Window rules + layer rules (blur / animations for wofi & swaync) — loaded
-- here explicitly: Hyprland does NOT auto-load the hyprland/ dependency tree.
-- Without this, blur & animations on menus/panels silently never existed.
pcall(require, "hyprland.rules")
