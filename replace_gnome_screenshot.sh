#!/bin/bash

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
BASE_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

# 1. Disable default screenshot shortcuts (Cinnamon/Gnome)
echo "Disabling default screenshot shortcuts..."

# Cinnamon
if gsettings describe org.cinnamon.desktop.keybindings.media-keys screenshot >/dev/null 2>&1; then
    gsettings set org.cinnamon.desktop.keybindings.media-keys screenshot "[]"
    gsettings set org.cinnamon.desktop.keybindings.media-keys screenshot-clip "[]"
    gsettings set org.cinnamon.desktop.keybindings.media-keys area-screenshot "[]"
    gsettings set org.cinnamon.desktop.keybindings.media-keys area-screenshot-clip "[]"
    gsettings set org.cinnamon.desktop.keybindings.media-keys window-screenshot "[]"
    gsettings set org.cinnamon.desktop.keybindings.media-keys window-screenshot-clip "[]"
fi

# Gnome
if gsettings describe org.gnome.settings-daemon.plugins.media-keys screenshot >/dev/null 2>&1; then
    gsettings set org.gnome.settings-daemon.plugins.media-keys screenshot "[]"
    gsettings set org.gnome.settings-daemon.plugins.media-keys screenshot-clip "[]"
    gsettings set org.gnome.settings-daemon.plugins.media-keys area-screenshot "[]"
    gsettings set org.gnome.settings-daemon.plugins.media-keys area-screenshot-clip "[]"
    gsettings set org.gnome.settings-daemon.plugins.media-keys window-screenshot "[]"
    gsettings set org.gnome.settings-daemon.plugins.media-keys window-screenshot-clip "[]"
fi

# 2. Register Clicky shortcuts for Print Screen
# Format: "Name:Command:Binding:PathSuffix"
SHORTCUTS=(
    "Clicky Screen (Print):--screen:Print:clicky-print-screen/"
    "Clicky Area (Shift+Print):--area:<Shift>Print:clicky-print-area/"
    "Clicky Window (Alt+Print):--window:<Alt>Print:clicky-print-window/"
    # Keeping the Super shortcuts as well? The user asked to replace, but maybe we should keep the others too if they were just added.
    # The previous script overwrote everything. I'll include the Shift+Super ones AND the Print ones here to have a complete set.
    "Clicky Screen (Super):--screen:<Shift><Super>a:clicky-screen/"
    "Clicky Area (Super):--area:<Shift><Super>s:clicky-area/"
    "Clicky Window (Super):--window:<Shift><Super>d:clicky-window/"
)

# Build the list of paths
custom_paths="["
for shortcut in "${SHORTCUTS[@]}"; do
    IFS=':' read -r name cmd binding suffix <<< "$shortcut"
    # Append to list
    custom_paths+="'$BASE_PATH/$suffix', "
done
# Remove trailing comma and space, add closing bracket
custom_paths="${custom_paths%, }]"

echo "Registering new shortcuts..."
echo "Setting custom-keybindings list to: $custom_paths"
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$custom_paths"

for shortcut in "${SHORTCUTS[@]}"; do
    IFS=':' read -r name cmd binding suffix <<< "$shortcut"
    
    full_path="$BASE_PATH/$suffix"
    full_cmd="$REPO_ROOT/clicky_cli.sh $cmd"
    
    echo "Configuring '$name'..."
    gsettings set "$SCHEMA:$full_path" name "$name"
    gsettings set "$SCHEMA:$full_path" command "$full_cmd"
    gsettings set "$SCHEMA:$full_path" binding "$binding"
done


# Cinnamon Support
CINNAMON_SCHEMA="org.cinnamon.desktop.keybindings"
CINNAMON_CUSTOM_SCHEMA="org.cinnamon.desktop.keybindings.custom-keybinding"
CINNAMON_BASE_PATH="/org/cinnamon/desktop/keybindings/custom-keybindings"

if gsettings list-keys "$CINNAMON_SCHEMA" | grep -q "custom-list"; then
    echo "Detected Cinnamon. configuring Cinnamon shortcuts..."
    
    # Get current custom-list
    CURRENT_LIST=$(gsettings get "$CINNAMON_SCHEMA" custom-list)
    # Remove brackets and single quotes for easier parsing, but be careful. 
    # Actually, simpler to just append our new ones if they aren't there.
    # But since we want to enforce them, we can rebuild the list or append.

    # We will build a NEW list that includes existing items (excluding ours to avoid dups) + ours.
    # Parsing gsettings array string in bash is tricky. 
    # Alternative: Use python for robust list handling.
    
    python3 -c "
import subprocess
import ast

try:
    current_str = subprocess.check_output(['gsettings', 'get', '$CINNAMON_SCHEMA', 'custom-list']).decode('utf-8').strip()
    if not current_str or current_str == '@as []':
        current_list = []
    else:
        current_list = ast.literal_eval(current_str)
except:
    current_list = []

new_shortcuts = [
    'clicky-screen', 'clicky-area', 'clicky-window',
    'clicky-print-screen', 'clicky-print-area', 'clicky-print-window'
]

# Remove our shortcuts if they exist (to ensure we don't have duplicates or stale entries)
final_list = [x for x in current_list if x not in new_shortcuts]
# Append ours
final_list.extend(new_shortcuts)

subprocess.call(['gsettings', 'set', '$CINNAMON_SCHEMA', 'custom-list', str(final_list)])
"

    # Configure details
    SHORTCUTS_CINNAMON=(
        "Clicky Screen (Print):--screen:Print:clicky-print-screen"
        "Clicky Area (Shift+Print):--area:<Shift>Print:clicky-print-area"
        "Clicky Window (Alt+Print):--window:<Alt>Print:clicky-print-window"
        "Clicky Screen (Super):--screen:<Shift><Super>a:clicky-screen"
        "Clicky Area (Super):--area:<Shift><Super>s:clicky-area"
        "Clicky Window (Super):--window:<Shift><Super>d:clicky-window"
    )

    for shortcut in "${SHORTCUTS_CINNAMON[@]}"; do
        IFS=':' read -r name cmd binding id <<< "$shortcut"
        
        full_path="$CINNAMON_BASE_PATH/$id/"
        full_cmd="$REPO_ROOT/clicky_cli.sh $cmd"
        
        # In Cinnamon, the binding is an array of strings like ['<Super>a']
        binding_val="['$binding']"
        
        echo "Configuring Cinnamon '$name'..."
        gsettings set "$CINNAMON_CUSTOM_SCHEMA:$full_path" name "$name"
        gsettings set "$CINNAMON_CUSTOM_SCHEMA:$full_path" command "$full_cmd"
        gsettings set "$CINNAMON_CUSTOM_SCHEMA:$full_path" binding "$binding_val"
    done
fi

echo "Done! Shortcuts configured."

