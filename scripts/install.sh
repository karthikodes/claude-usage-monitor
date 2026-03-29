#!/usr/bin/env bash
# Install Claude Usage Monitor menu bar app
# - Installs Python dependency (rumps)
# - Creates a LaunchAgent for auto-start on login
# - Starts the app immediately

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPT_PATH="$REPO_DIR/menubar/claude_usage_menubar.py"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/com.karthikodes.claude-usage-monitor.plist"
PYTHON="$(command -v python3)"

# ── 1. Check prerequisites ───────────────────────────────────────────────────
echo "🔍 Checking prerequisites..."

if [ -z "$PYTHON" ]; then
    echo "❌ python3 not found. Install Python 3.9+ first."
    exit 1
fi

echo "  Python: $PYTHON ($($PYTHON --version 2>&1))"

# Check for Claude Code credentials in Keychain
if ! security find-generic-password -s "Claude Code-credentials" -w &>/dev/null; then
    echo "❌ Claude Code credentials not found in Keychain."
    echo "  Install Claude Code and log in first: https://claude.ai/download"
    exit 1
fi
echo "  Keychain: ✅ Claude Code credentials found"

# ── 2. Install dependency ────────────────────────────────────────────────────
echo "📦 Installing rumps..."
$PYTHON -m pip install --quiet rumps
echo "  ✅ rumps installed"

# ── 3. Create LaunchAgent ────────────────────────────────────────────────────
echo "🚀 Setting up auto-start..."
mkdir -p "$LAUNCH_AGENTS_DIR"

cat > "$PLIST_DEST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.karthikodes.claude-usage-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${SCRIPT_PATH}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/claude-usage-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-usage-monitor.error.log</string>
</dict>
</plist>
PLIST

# Unload if already loaded
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# ── 4. Start ─────────────────────────────────────────────────────────────────
echo "▶️  Starting Claude Usage Monitor..."
pkill -f "claude_usage_menubar" 2>/dev/null || true
sleep 1

launchctl load "$PLIST_DEST"
echo "  ✅ Running!"

echo ""
echo "✅ Installation complete!"
echo "   • Script: $SCRIPT_PATH"
echo "   • Python: $PYTHON"
echo "   • LaunchAgent: $PLIST_DEST"
echo "   • Auto-starts on login"
echo "   • Logs: /tmp/claude-usage-monitor.log"
echo ""
echo "To uninstall:"
echo "   launchctl unload $PLIST_DEST"
echo "   rm $PLIST_DEST"
