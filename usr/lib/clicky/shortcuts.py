#!/usr/bin/python3
"""
shortcuts.py – Manage system screenshot keybindings for Clicky Plus.

Provides enable() / disable() functions to replace or restore
the native screenshot shortcuts on Cinnamon and GNOME.
"""

import ast
import os
import subprocess

# Shortcut definitions: (id, name, cli_flag, binding)
SHORTCUTS = [
    ("clicky-print-screen", "Clicky Screen (Print)", "--screen", "Print"),
    ("clicky-print-area", "Clicky Area (Shift+Print)", "--area", "<Shift>Print"),
    ("clicky-print-window", "Clicky Window (Alt+Print)", "--window", "<Alt>Print"),
    ("clicky-screen", "Clicky Screen (Super)", "--screen", "<Shift><Super>a"),
    ("clicky-area", "Clicky Area (Super)", "--area", "<Shift><Super>s"),
    ("clicky-window", "Clicky Window (Super)", "--window", "<Shift><Super>d"),
]

SHORTCUT_IDS = [s[0] for s in SHORTCUTS]

# Cinnamon native screenshot keys to disable/restore
CINNAMON_NATIVE_KEYS = [
    "screenshot", "screenshot-clip",
    "area-screenshot", "area-screenshot-clip",
    "window-screenshot", "window-screenshot-clip",
]

# Cinnamon default bindings (to restore when disabling)
CINNAMON_DEFAULTS = {
    "screenshot": "['Print']",
    "screenshot-clip": "['<Control>Print']",
    "area-screenshot": "['<Shift>Print']",
    "area-screenshot-clip": "['<Control><Shift>Print']",
    "window-screenshot": "['<Alt>Print']",
    "window-screenshot-clip": "['<Control><Alt>Print']",
}


def _gsettings(*args):
    """Run gsettings command, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["gsettings"] + list(args),
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _is_cinnamon():
    """Detect if running under Cinnamon."""
    output = _gsettings("list-keys", "org.cinnamon.desktop.keybindings")
    return "custom-list" in output


def _get_clicky_command(cli_flag):
    """Build the absolute command path for the given flag."""
    # Determine base path: installed or development
    usr_bin = "/usr/bin/clicky_cli.sh"
    if os.path.exists(usr_bin):
        return f"{usr_bin} {cli_flag}"
    # Development: use repo-relative path
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    cli_path = os.path.join(repo_root, "clicky_cli.sh")
    if os.path.exists(cli_path):
        return f"{cli_path} {cli_flag}"
    return f"clicky_cli.sh {cli_flag}"


def _cinnamon_get_custom_list():
    """Get the current Cinnamon custom-list."""
    raw = _gsettings("get", "org.cinnamon.desktop.keybindings", "custom-list")
    if not raw or raw == "@as []":
        return []
    try:
        return ast.literal_eval(raw)
    except Exception:
        return []


def _cinnamon_set_custom_list(lst):
    """Set the Cinnamon custom-list."""
    _gsettings("set", "org.cinnamon.desktop.keybindings", "custom-list", str(lst))


def enable():
    """Make Clicky the default screenshot app."""
    if _is_cinnamon():
        _enable_cinnamon()
    _enable_gnome()


def disable():
    """Restore the native screenshot app."""
    if _is_cinnamon():
        _disable_cinnamon()
    _disable_gnome()


def _enable_cinnamon():
    """Disable native Cinnamon screenshot keys and add Clicky shortcuts."""
    schema = "org.cinnamon.desktop.keybindings.media-keys"
    for key in CINNAMON_NATIVE_KEYS:
        _gsettings("set", schema, key, "[]")

    # Update custom-list
    current = _cinnamon_get_custom_list()
    final = [x for x in current if x not in SHORTCUT_IDS]
    final.extend(SHORTCUT_IDS)
    _cinnamon_set_custom_list(final)

    # Configure each shortcut
    base = "/org/cinnamon/desktop/keybindings/custom-keybindings"
    custom_schema = "org.cinnamon.desktop.keybindings.custom-keybinding"
    for sid, name, flag, binding in SHORTCUTS:
        path = f"{base}/{sid}/"
        cmd = _get_clicky_command(flag)
        _gsettings("set", f"{custom_schema}:{path}", "name", name)
        _gsettings("set", f"{custom_schema}:{path}", "command", cmd)
        _gsettings("set", f"{custom_schema}:{path}", "binding", f"['{binding}']")


def _disable_cinnamon():
    """Restore native Cinnamon screenshot keys and remove Clicky shortcuts."""
    schema = "org.cinnamon.desktop.keybindings.media-keys"
    for key in CINNAMON_NATIVE_KEYS:
        default = CINNAMON_DEFAULTS.get(key, "[]")
        _gsettings("set", schema, key, default)

    # Remove from custom-list
    current = _cinnamon_get_custom_list()
    updated = [x for x in current if x not in SHORTCUT_IDS]
    _cinnamon_set_custom_list(updated)

    # Reset each shortcut by clearing its binding
    base = "/org/cinnamon/desktop/keybindings/custom-keybindings"
    custom_schema = "org.cinnamon.desktop.keybindings.custom-keybinding"
    for sid, name, flag, binding in SHORTCUTS:
        path = f"{base}/{sid}/"
        _gsettings("set", f"{custom_schema}:{path}", "binding", "[]")


def _enable_gnome():
    """Register shortcuts in GNOME settings-daemon (for non-Cinnamon)."""
    schema = "org.gnome.settings-daemon.plugins.media-keys"
    custom_schema = f"{schema}.custom-keybinding"
    base = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

    # Disable native
    for key in ["screenshot", "screenshot-clip", "area-screenshot",
                "area-screenshot-clip", "window-screenshot", "window-screenshot-clip"]:
        _gsettings("set", schema, key, "[]")

    # Build paths list
    paths = [f"'{base}/{sid}/' " for sid, _, _, _ in SHORTCUTS]
    paths_str = "[" + ", ".join(paths) + "]"
    _gsettings("set", schema, "custom-keybindings", paths_str)

    for sid, name, flag, binding in SHORTCUTS:
        path = f"{base}/{sid}/"
        cmd = _get_clicky_command(flag)
        _gsettings("set", f"{custom_schema}:{path}", "name", name)
        _gsettings("set", f"{custom_schema}:{path}", "command", cmd)
        _gsettings("set", f"{custom_schema}:{path}", "binding", binding)


def _disable_gnome():
    """Remove Clicky shortcuts from GNOME settings-daemon."""
    schema = "org.gnome.settings-daemon.plugins.media-keys"
    # Re-enable native screenshot keys with defaults
    _gsettings("set", schema, "screenshot", "['Print']")
    _gsettings("set", schema, "screenshot-clip", "['<Control>Print']")
    _gsettings("set", schema, "area-screenshot", "['<Shift>Print']")
    _gsettings("set", schema, "area-screenshot-clip", "['<Control><Shift>Print']")
    _gsettings("set", schema, "window-screenshot", "['<Alt>Print']")
    _gsettings("set", schema, "window-screenshot-clip", "['<Control><Alt>Print']")

    # Clear custom keybindings list
    _gsettings("set", schema, "custom-keybindings", "[]")
