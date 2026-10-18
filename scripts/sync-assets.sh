#!/bin/bash
# Sync brand assets from assets/ to web/static/
# This script should be run as part of the build process
#
# Note: favicon.svg and favicon.png at the root of web/static/ are
# manually maintained and not synced from assets/ (they are separate
# 32px versions distinct from the favicons/ directory)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/../assets"
STATIC_DIR="$SCRIPT_DIR/../web/static"

echo "Syncing assets from $ASSETS_DIR to $STATIC_DIR..."

# Create directories if they don't exist
mkdir -p "$STATIC_DIR/favicons"
mkdir -p "$STATIC_DIR/icons"
mkdir -p "$STATIC_DIR/images"

# Copy favicon files
cp "$ASSETS_DIR/favicons"/* "$STATIC_DIR/favicons/"

# Copy icon files
cp "$ASSETS_DIR/icons"/* "$STATIC_DIR/icons/"

# Copy image files (og-image)
cp "$ASSETS_DIR/images"/* "$STATIC_DIR/images/"

echo "Assets synced successfully."
