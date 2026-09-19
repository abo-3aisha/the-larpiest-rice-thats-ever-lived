{
    "positionX": "right",
    "positionY": "top",
    "control-center-margin-top": 8,
    "control-center-margin-bottom": 8,
    "control-center-margin-right": 8,
    "control-center-margin-left": 0,
    "control-center-width": 400,
    "control-center-height": 700,
    "notification-window-width": 430,
    "notification-icon-size": 48,
    "notification-body-image-height": 100,
    "notification-body-image-width": 200,
    "timeout": 7,
    "hide-on-clear": false,
    "hide-on-action": true,
    "script-fail-notify": true,
    "layer": "overlay",
    "cssPriority": "user",
    "widgets": [
        "title",
        "dnd",
        "media",
        "menubar",
        "volume",
        "slider#mic",
        "backlight",
        "notifications"
    ],
    "widget-config": {
        "title": {
            "text": "Notifications",
            "clear-all-button": true,
            "button-text": "Clear All"
        },
        "dnd": {
            "text": "Do Not Disturb"
        },
        "menubar": {
            "buttons#quick": {
                "position": "right",
                "actions": [
                    {
                        "label": "󰤨  Wi-Fi",
                        "type": "toggle",
                        "active": false,
                        "command": "/home/abo3aisha/.local/bin/q-toggle wifi-radio",
                        "update-command": "timeout 2 sh -c 'if [ \"$(nmcli radio wifi 2>/dev/null)\" = \"enabled\" ]; then echo true; else echo false; fi'"
                    },
                    {
                        "label": "󰂯  Bluetooth",
                        "type": "toggle",
                        "active": false,
                        "command": "/home/abo3aisha/.local/bin/q-toggle bt",
                        "update-command": "timeout 2 sh -c 'if systemctl is-active --quiet bluetooth 2>/dev/null && bluetoothctl show 2>/dev/null | grep -q \"Powered: yes\"; then echo true; else echo false; fi'"
                    },
                    {
                        "label": "󰽥  Night Light",
                        "type": "toggle",
                        "active": false,
                        "command": "/home/abo3aisha/.local/bin/q-toggle night",
                        "update-command": "timeout 2 sh -c 'if pgrep -x gammastep >/dev/null 2>&1; then echo true; else echo false; fi'"
                    },
                    {
                        "label": "󰐥  Power",
                        "command": "/home/abo3aisha/.local/bin/q-toggle power"
                    }
                ]
            }
        },
        "volume": {},
        "backlight": {},
        "slider#mic": {
            "label": "MIC",
            "cmd_setter": "/home/abo3aisha/.local/bin/mic-vol set $value",
            "cmd_getter": "/home/abo3aisha/.local/bin/mic-vol get",
            "min": 0,
            "max": 100,
            "min_limit": 0,
            "max_limit": 100
        }
    }
}