#!/usr/bin/env bash
# Install Claude Usage Monitor menu bar app
# - Builds the .app
# - Copies to /Applications
# - Installs LaunchAgent for auto-start on login
# - Starts the app immediately

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
MENUBAR_DIR="$REPO_DIR/menubar"
PLIST_SRC="$SCRIPT_DIR/com.karthikodes.claude-usage-monitor.plist"
APP_NAME="Claude Usage Monitor.app"
APP_DEST="/Applications/$APP_NAME"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/com.karthikodes.claude-usage-monitor.plist"
LABEL="com.karthikodes.claude-usage-monitor"

# ── 1. Build ──────────────────────────────────────────────────────────────────
echo "🔨 Building $APP_NAME..."
"$SCRIPT_DIR/build-app.sh"

# ── 2. Copy to /Applications ──────────────────────────────────────────────────
echo "📦 Installing to /Applications..."
if [ -d "$APP_DEST" ]; then
    echo "  Removing existing installation..."
    rm -rf "$APP_DEST"
fi
cp -R "$MENUBAR_DIR/dist/$APP_NAME" "$APP_DEST"
echo "  ✅ Installed: $APP_DEST"

# ── 3. Install LaunchAgent ────────────────────────────────────────────────────
echo "🚀 Installing LaunchAgent..."
mkdir -p "$LAUNCH_AGENTS_DIR"
cp "$PLIST_SRC" "$PLIST_DEST"

# Unload if already loaded (ignore errors)
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load it
launchctl load "$PLIST_DEST"
echo "  ✅ LaunchAgent installed: $PLIST_DEST"

# ── 4. Start immediately ──────────────────────────────────────────────────────
echo "▶️  Starting Claude Usage Monitor..."
# Kill any running instance first
pkill -f "claude_usage_menubar" 2>/dev/null || true
sleep 1

# Launch the .app
open "$APP_DEST"
echo "  ✅ Running!"

echo ""
echo "✅ Installation complete!"
echo "   • App: $APP_DEST"
echo "   • LaunchAgent: $PLIST_DEST"
echo "   • Auto-starts on login"
echo "   • Logs: /tmp/claude-usage-monitor.log"
