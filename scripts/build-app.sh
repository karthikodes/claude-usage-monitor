#!/usr/bin/env bash
# Build Claude Usage Monitor as a macOS .app bundle
# Requires: Python 3, pip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
MENUBAR_DIR="$REPO_DIR/menubar"

echo "🔨 Installing Python dependencies..."
pip3 install --quiet py2app rumps

echo "🏗  Building .app bundle..."
cd "$MENUBAR_DIR"
rm -rf build dist

python3 setup.py py2app 2>&1

APP_PATH="$MENUBAR_DIR/dist/Claude Usage Monitor.app"
if [ -d "$APP_PATH" ]; then
    echo "✅ Build succeeded: $APP_PATH"
else
    echo "❌ Build failed — check output above"
    exit 1
fi
