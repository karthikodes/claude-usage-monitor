# Claude Code Usage Monitor

Monitor your Claude Code usage limits from the macOS menu bar or terminal.

Shows session (5-hour) and weekly utilization with progress bars, reset timers, and threshold alerts — powered by the Anthropic OAuth usage API.

## Prerequisites

- **macOS** (reads OAuth token from Keychain)
- **Claude Code** must be installed and logged in (the token is stored automatically)
- **Python 3.9+** (for the menu bar app)
- **Node.js 18+** (for the CLI, optional)

## Menu Bar App

A native macOS menu bar widget that shows live usage at a glance.

### What you see

**Menu bar** (always visible):

```
CC 2%·25%
```

Session % and Weekly % separated by a dot.

**Click to expand:**

```
╭─ Claude Code Usage ──────────────────╮
│  ⏱  Session (17m)   🟢 2%           │
│  █░░░░░░░░░░░░░░░░░░  resets 4h 43m │
│                                       │
│  📊 Weekly (All)   🟢 25%           │
│  █████░░░░░░░░░░░░░░░  resets 5d    │
│                                       │
│  🎯 Sonnet Only    🟢 10%           │
│  ██░░░░░░░░░░░░░░░░░░  resets 5d    │
│                                       │
│  Updated: 2:15 PM                    │
╰─────────────────────────────────────╯

↻ Refresh
──────
⚙ Settings
  🔔 Notifications: ON
Quit
```

### Status indicators

| Icon | Usage | Meaning |
|------|-------|---------|
| 🟢 | < 60% | Comfortable |
| 🟡 | 60-80% | Watch out |
| 🔴 | > 80% | Near limit |

### Setup

```bash
git clone https://github.com/karthikodes/claude-usage-monitor.git
cd claude-usage-monitor/menubar

# Install the only dependency
pip3 install rumps

# Run it
python3 claude_usage_menubar.py
```

The app appears in your menu bar immediately. No Dock icon.

### Auto-refresh

The widget refreshes every 15 minutes automatically. Click **Refresh** for an immediate update.

### Notifications

When any metric crosses 80%, a macOS notification fires (once per hour per metric). Toggle via **Settings > Notifications**.

### Build as a standalone .app (optional)

If you want it as a proper macOS app with login auto-start:

```bash
# One-step: build + install to /Applications + auto-start on login
./scripts/install.sh
```

This will:
1. Build `Claude Usage Monitor.app` via py2app
2. Copy it to `/Applications/`
3. Install a LaunchAgent so it starts on login
4. Launch it immediately

To build without installing:

```bash
pip3 install py2app rumps
cd menubar
python3 setup.py py2app
# Output: menubar/dist/Claude Usage Monitor.app
```

### Uninstall

```bash
# Stop and remove LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.karthikodes.claude-usage-monitor.plist
rm ~/Library/LaunchAgents/com.karthikodes.claude-usage-monitor.plist

# Remove app
rm -rf "/Applications/Claude Usage Monitor.app"
```

---

## Terminal CLI

A rich terminal display as an alternative to the menu bar app.

### Setup

```bash
cd claude-usage-monitor
npm install
npm link    # makes `claude-usage` available globally
```

### Usage

```bash
# Pretty terminal output
claude-usage

# Machine-readable JSON
claude-usage --json

# Exit code 1 if any metric >= 80% (useful for scripts/cron)
claude-usage --check
```

### Threshold alert script

A standalone shell script for cron jobs or automation:

```bash
./scripts/check-and-alert.sh
# Exits 0 if all metrics < 70%, exits 1 with alert message otherwise
```

---

## How it works

1. Reads the OAuth token from the macOS Keychain entry `Claude Code-credentials` (written automatically when you log in to Claude Code)
2. Calls the Anthropic usage API:
   ```
   GET https://api.anthropic.com/api/oauth/usage
   Authorization: Bearer <token>
   anthropic-beta: oauth-2025-04-20
   ```
3. Parses the response for session (5-hour window), weekly (7-day), and sonnet-specific utilization

No API keys or secrets are stored in the repo. The token is read from Keychain at runtime.

## Project structure

```
claude-usage-monitor/
├── menubar/
│   ├── claude_usage_menubar.py   # Menu bar app (Python/rumps)
│   └── setup.py                  # py2app build config
├── src/
│   └── index.ts                  # Terminal CLI (TypeScript)
├── scripts/
│   ├── build-app.sh              # Build .app bundle
│   ├── install.sh                # Build + install + LaunchAgent
│   ├── check-and-alert.sh        # Threshold checker for cron
│   └── com.karthikodes.claude-usage-monitor.plist
├── bin/
│   └── claude-usage              # CLI entry point
└── package.json
```

## License

MIT
