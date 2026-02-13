#!/bin/bash

# Get the absolute path of the repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define paths
LIB_DIR="$REPO_ROOT/usr/lib/clicky"
SCHEMA_DIR="$REPO_ROOT/usr/share/glib-2.0/schemas"

# Detect executables
PYTHON_BIN=$(which python3)
GLIB_COMPILE_SCHEMAS_BIN=$(which glib-compile-schemas)

# Compile schemas locally if they aren't already valid or update is needed
if [ -f "$SCHEMA_DIR/org.x.clickyplus.gschema.xml" ]; then
    if [ -n "$GLIB_COMPILE_SCHEMAS_BIN" ]; then
        echo "Compiling GSettings schemas locally..."
        "$GLIB_COMPILE_SCHEMAS_BIN" "$SCHEMA_DIR"
    else
        echo "Warning: glib-compile-schemas not found. Schemas might be outdated."
    fi
fi

# Set Environment Variables
export PYTHONPATH="$LIB_DIR:$PYTHONPATH"
export GSETTINGS_SCHEMA_DIR="$SCHEMA_DIR"

echo "Starting Clicky from local source..."
echo "PYTHONPATH: $PYTHONPATH"
echo "GSETTINGS_SCHEMA_DIR: $GSETTINGS_SCHEMA_DIR"

if [ -n "$PYTHON_BIN" ]; then
    "$PYTHON_BIN" "$LIB_DIR/clicky.py" "$@"
else
    echo "Error: python3 not found."
    exit 1
fi
