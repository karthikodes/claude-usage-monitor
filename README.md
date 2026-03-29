# Claude Code Usage Monitor

A macOS menu bar widget that shows your Claude Code usage limits at a glance.

Session and weekly utilization, progress bars, reset timers, projected usage, and smart notifications — all from one tiny menu bar icon.

## Prerequisites

- **macOS**
- **Python 3.9+**
- **Claude Code** installed and logged in ([download](https://claude.ai/download))

## Install

```bash
git clone https://github.com/karthikodes/claude-usage-monitor.git
cd claude-usage-monitor
./scripts/install.sh
```

That's it. The script will:
1. Check that Python 3 and Claude Code credentials exist
2. Install the `rumps` dependency
3. Set up a LaunchAgent so it auto-starts on login
4. Start the widget immediately

You should see **CC 0%·0%** appear in your menu bar.

## What you see

**Menu bar** (always visible):

```
CC 2%·25%
```

Session % · Weekly %. Updates every 15 minutes.

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
│  ⚡ 🟠 ~90% by reset · 13%/day     │
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
| 🟡 | 60–80% | Watch out |
| 🔴 | > 80% | Near limit |

### Weekly projection

The `⚡` line shows your projected weekly usage at current pace:

| Icon | Projected | Meaning |
|------|-----------|---------|
| 🟢 | < 50% | Light usage |
| 🟡 | 50–75% | Moderate |
| 🟠 | 75–100% | Heavy |
| 🔴 | > 100% | Will hit limit (shows which day) |

### Notifications

Three types of macOS notifications (once per hour max):

| Trigger | Notification |
|---------|-------------|
| Any metric >= 80% | "⚠️ Session usage is at 85%" |
| Was high, drops below 30% | "✅ Session dropped to 12% — good to go" |
| Session resets in < 20 min | "🔄 Session resets in 14m" |

Toggle via **Settings > Notifications** in the dropdown.

## Run without auto-start

If you just want to try it without installing:

```bash
pip3 install rumps
cd menubar
python3 claude_usage_menubar.py
```

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.karthikodes.claude-usage-monitor.plist
rm ~/Library/LaunchAgents/com.karthikodes.claude-usage-monitor.plist
```

## Terminal CLI (optional)

A rich terminal display as an alternative to the menu bar app.

```bash
npm install
npm link

claude-usage          # Pretty terminal output
claude-usage --json   # Machine-readable JSON
claude-usage --check  # Exit code 1 if any metric >= 80%
```

## How it works

1. Reads the OAuth token from macOS Keychain (`Claude Code-credentials` — written automatically when you log in to Claude Code)
2. Calls the Anthropic usage API:
   ```
   GET https://api.anthropic.com/api/oauth/usage
   Authorization: Bearer <token>
   ```
3. Displays session (5-hour), weekly (7-day), and sonnet utilization

No API keys or secrets are stored in the repo.

## Project structure

```
claude-usage-monitor/
├── menubar/
│   └── claude_usage_menubar.py   # Menu bar app (Python/rumps)
├── src/
│   └── index.ts                  # Terminal CLI (TypeScript)
├── scripts/
│   ├── install.sh                # One-step install + auto-start
│   └── check-and-alert.sh        # Threshold checker for cron
├── bin/
│   └── claude-usage              # CLI entry point
└── package.json
```

## License

MIT
