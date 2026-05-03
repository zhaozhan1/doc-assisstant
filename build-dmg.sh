#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="公文助手"
DMG_NAME="公文助手-0.1.0"
APP_PATH="$PROJECT_ROOT/dist/${APP_NAME}.app"
DMG_PATH="$PROJECT_ROOT/dist/${DMG_NAME}.dmg"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Run build.sh first."
    exit 1
fi

echo "=== Creating DMG: ${DMG_NAME}.dmg ==="

rm -f "$DMG_PATH"

STAGING_DIR=$(mktemp -d)
trap "rm -rf '$STAGING_DIR'" EXIT

cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo "=== DMG created: $DMG_PATH ==="
du -sh "$DMG_PATH"
