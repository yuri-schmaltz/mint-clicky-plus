#!/bin/bash

# Get the absolute path of the repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define paths
LIB_DIR="$REPO_ROOT/usr/lib/clicky"
SCHEMA_DIR="$REPO_ROOT/usr/share/glib-2.0/schemas"

# Compile schemas locally if they aren't already valid or update is needed
if [ -f "$SCHEMA_DIR/org.x.clicky.gschema.xml" ]; then
    echo "Compiling GSettings schemas locally..."
    glib-compile-schemas "$SCHEMA_DIR"
fi

# Build translations locally (mo files)
if command -v make >/dev/null 2>&1; then
    make -s buildmo
fi

# Set Environment Variables
export PYTHONPATH="$LIB_DIR:$PYTHONPATH"
export GSETTINGS_SCHEMA_DIR="$SCHEMA_DIR"

echo "Starting Clicky from local source..."
echo "PYTHONPATH: $PYTHONPATH"
echo "GSETTINGS_SCHEMA_DIR: $GSETTINGS_SCHEMA_DIR"

/usr/bin/python3 "$LIB_DIR/clicky.py"
