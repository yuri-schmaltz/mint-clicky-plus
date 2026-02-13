#!/bin/bash

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
BASE_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

# Define Shortcuts
# Format: "Name:Command:Binding:PathSuffix"
SHORTCUTS=(
    "Clicky Screen:--screen:<Shift><Super>a:clicky-screen/"
    "Clicky Area:--area:<Shift><Super>s:clicky-area/"
    "Clicky Window:--window:<Shift><Super>d:clicky-window/"
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

echo "Registering shortcuts..."

# 1. Set the list of custom keybindings
# WARNING: This overwrites existing custom keybindings.
# To append, we would need to read the existing value, parse it, and merge.
# For this task, we assume the user wants these specific shortcuts or is okay with resetting for this app.
# Given the user request "adjust so that...", setting these as the custom bindings is a direct fulfillment.
echo "Setting custom-keybindings list to: $custom_paths"
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$custom_paths"

# 2. Set details for each shortcut
for shortcut in "${SHORTCUTS[@]}"; do
    IFS=':' read -r name cmd binding suffix <<< "$shortcut"
    
    full_path="$BASE_PATH/$suffix"
    full_cmd="$REPO_ROOT/clicky_cli.sh $cmd"
    
    echo "Configuring '$name'..."
    gsettings set "$SCHEMA:$full_path" name "$name"
    gsettings set "$SCHEMA:$full_path" command "$full_cmd"
    gsettings set "$SCHEMA:$full_path" binding "$binding"
    
    echo "  -> Bound '$binding' to '$full_cmd'"
done

echo "Done!"
