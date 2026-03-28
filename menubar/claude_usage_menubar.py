#!/usr/bin/env python3
"""
Claude Code Usage Monitor — macOS Menu Bar App
Shows live session & weekly usage limits in the menu bar.

Requirements: pip install rumps
"""

import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import rumps

# ── Constants ──────────────────────────────────────────────────────────────────

REFRESH_INTERVAL = 900  # seconds between auto-refresh (15min)
API_URL = "https://api.anthropic.com/api/oauth/usage"
KEYCHAIN_SERVICE = "Claude Code-credentials"
BAR_WIDTH = 18
NOTIF_THRESHOLD = 80.0
NOTIF_COOLDOWN = 3600  # 1 hour between repeated notifications per metric


# ── Token helpers ──────────────────────────────────────────────────────────────

def get_oauth_token() -> str:
    """Read OAuth token from macOS Keychain."""
    try:
        raw = subprocess.check_output(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        data = json.loads(raw.decode().strip())
        return data.get("claudeAiOauth", {}).get("accessToken", "")
    except Exception:
        return ""


# ── API ────────────────────────────────────────────────────────────────────────

def fetch_usage(token: str) -> dict:
    """Fetch usage data from Anthropic OAuth API."""
    req = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


# ── Formatting helpers ─────────────────────────────────────────────────────────

def bar_visual(pct: float, width: int = BAR_WIDTH) -> str:
    """Render a progress bar: ████████░░░░░░░░░░"""
    filled = min(round(pct / 100 * width), width)
    return "█" * filled + "░" * (width - filled)


def pct_str(pct) -> str:
    return "—" if pct is None else f"{int(pct)}%"


def status_emoji(pct) -> str:
    """Color indicator based on utilization."""
    if pct is None:
        return "⚪"
    if pct < 60:
        return "🟢"
    if pct < 80:
        return "🟡"
    return "🔴"


def time_until(iso_str: str) -> str:
    """Return compact reset time string: 'resets 4h', 'resets 5d', 'resets 18m'."""
    if not iso_str:
        return ""
    try:
        target = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        total_sec = int((target - now).total_seconds())

        if total_sec <= 0:
            return "resetting now"
        if total_sec < 3600:
            return f"resets {total_sec // 60}m"
        if total_sec < 86400:
            hours = total_sec // 3600
            mins = (total_sec % 3600) // 60
            return f"resets {hours}h{f' {mins}m' if mins else ''}"

        days = total_sec // 86400
        return f"resets {days}d"
    except Exception:
        return ""


def menu_bar_title(s_pct, w_pct) -> str:
    """Compact title: CC 5%·18%"""
    s = pct_str(s_pct)
    w = pct_str(w_pct)
    return f"CC {s}·{w}"


# ── Menu item factories ────────────────────────────────────────────────────────

def make_item(title: str) -> rumps.MenuItem:
    item = rumps.MenuItem(title)
    item.set_callback(None)
    return item


# ── App ────────────────────────────────────────────────────────────────────────

class ClaudeUsageApp(rumps.App):
    def __init__(self):
        super().__init__("CC …", quit_button=None)

        self.token: str = ""
        self.last_fetch: float = 0.0
        self._lock = threading.Lock()

        # Notification tracking: {metric_key: last_notified_timestamp}
        self._notif_sent: dict = {}
        self._notifications_enabled: bool = True

        # Previous values for recovery detection
        self._prev_pct: dict = {}  # {metric_key: last_pct}

        # ── Menu items ──
        # Header
        self.header_item = make_item("╭─ Claude Code Usage ──────────────────╮")

        # Session section
        self.session_label = make_item("│  ⏱  Session  —")
        self.session_bar_item = make_item("│  ░░░░░░░░░░░░░░░░░░  —")
        self.session_spacer = make_item("│")

        # Weekly section
        self.weekly_label = make_item("│  📊 Weekly (All)  —")
        self.weekly_bar_item = make_item("│  ░░░░░░░░░░░░░░░░░░  —")
        self.weekly_spacer = make_item("│")

        # Sonnet section
        self.sonnet_label = make_item("│  🎯 Sonnet Only  —")
        self.sonnet_bar_item = make_item("│  ░░░░░░░░░░░░░░░░░░  —")
        self.sonnet_spacer = make_item("│")

        # Footer
        self.updated_item = make_item("│  Updated: —")
        self.footer_item = make_item("╰─────────────────────────────────────────╯")

        # Controls
        self.refresh_btn = rumps.MenuItem("↻ Refresh", callback=self.manual_refresh)
        self.sep_item = make_item("──────")

        # Settings submenu
        self.notif_toggle = rumps.MenuItem(
            "🔔 Notifications: ON", callback=self.toggle_notifications
        )
        self.settings_menu = rumps.MenuItem("⚙ Settings")
        self.settings_menu.add(self.notif_toggle)

        self.quit_btn = rumps.MenuItem("Quit", callback=rumps.quit_application)

        # Assemble menu
        self.menu = [
            self.header_item,
            self.session_label,
            self.session_bar_item,
            self.session_spacer,
            self.weekly_label,
            self.weekly_bar_item,
            self.weekly_spacer,
            self.sonnet_label,
            self.sonnet_bar_item,
            self.sonnet_spacer,
            self.updated_item,
            self.footer_item,
            None,
            self.refresh_btn,
            None,
            self.settings_menu,
            self.quit_btn,
        ]

        # Kick off initial fetch
        threading.Thread(target=self._do_refresh, daemon=True).start()

    # ── Refresh logic ──────────────────────────────────────────────────────────

    def _do_refresh(self):
        """Fetch usage data and update UI. Thread-safe."""
        with self._lock:
            now = time.time()
            if now - self.last_fetch < 170:
                return  # rate-limit guard (except manual which resets last_fetch)

            if not self.token:
                self.token = get_oauth_token()

            if not self.token:
                self.title = "CC ❌"
                self.session_label.title = "│  ⚠ No OAuth token in Keychain"
                return

            try:
                data = fetch_usage(self.token)
                self.last_fetch = time.time()
                self._update_menu(data)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    # Token expired — try refreshing once
                    self.token = get_oauth_token()
                    try:
                        data = fetch_usage(self.token)
                        self.last_fetch = time.time()
                        self._update_menu(data)
                        return
                    except Exception:
                        pass
                self.title = "CC ⚠️"
                self.updated_item.title = f"│  Error {e.code}: {e.reason}"
            except Exception as exc:
                self.title = "CC ⚠️"
                self.updated_item.title = f"│  Error: {str(exc)[:35]}"

    def _update_menu(self, data: dict):
        """Parse API response and update all menu items + title."""
        five = data.get("five_hour") or {}
        seven = data.get("seven_day") or {}
        sonnet = data.get("seven_day_sonnet") or {}

        s_pct = self._to_pct(five.get("utilization"))
        w_pct = self._to_pct(seven.get("utilization"))
        sn_pct = self._to_pct(sonnet.get("utilization"))

        # Menu bar title (session + weekly only)
        self.title = menu_bar_title(s_pct, w_pct)

        # Session row
        s_reset = time_until(five.get("resets_at", ""))
        s_emoji = status_emoji(s_pct)
        session_hours = self._extract_hours(five.get("resets_at", ""))
        self.session_label.title = (
            f"│  ⏱  Session{session_hours}   {s_emoji} {pct_str(s_pct)}"
        )
        self.session_bar_item.title = (
            f"│  {bar_visual(s_pct or 0)}  {s_reset}"
        )

        # Weekly row
        w_reset = time_until(seven.get("resets_at", ""))
        w_emoji = status_emoji(w_pct)
        self.weekly_label.title = (
            f"│  📊 Weekly (All)   {w_emoji} {pct_str(w_pct)}"
        )
        self.weekly_bar_item.title = (
            f"│  {bar_visual(w_pct or 0)}  {w_reset}"
        )

        # Sonnet row
        sn_reset = time_until(sonnet.get("resets_at", ""))
        sn_emoji = status_emoji(sn_pct)
        if sn_pct is not None:
            self.sonnet_label.title = (
                f"│  🎯 Sonnet Only   {sn_emoji} {pct_str(sn_pct)}"
            )
            self.sonnet_bar_item.title = (
                f"│  {bar_visual(sn_pct)}  {sn_reset}"
            )
        else:
            self.sonnet_label.title = "│  🎯 Sonnet Only   ⚪ —"
            self.sonnet_bar_item.title = f"│  {'░' * BAR_WIDTH}"

        # Updated timestamp
        now_str = datetime.now().strftime("%-I:%M %p")
        self.updated_item.title = f"│  Updated: {now_str}"

        # Notifications
        self._check_notifications(s_pct, w_pct, sn_pct, five.get("resets_at", ""))

    @staticmethod
    def _to_pct(value) -> float | None:
        """Coerce utilization to a 0-100 percentage. API returns 0-100 directly."""
        if value is None:
            return None
        return float(value)

    def _extract_hours(self, iso_str: str) -> str:
        """Extract elapsed hours from a 5h window for display: ' (1h)', ' (23m)'."""
        if not iso_str:
            return ""
        try:
            target = datetime.fromisoformat(iso_str)
            now = datetime.now(timezone.utc)
            remaining_sec = max(0, (target - now).total_seconds())
            elapsed_sec = max(0, 18000 - remaining_sec)  # 5h = 18000s
            elapsed_min = int(elapsed_sec / 60)
            if elapsed_min >= 60:
                return f" ({elapsed_min // 60}h)"
            return f" ({elapsed_min}m)"
        except Exception:
            return ""

    # ── Notifications ──────────────────────────────────────────────────────────

    def _check_notifications(self, s_pct, w_pct, sn_pct, session_resets_at: str):
        if not self._notifications_enabled:
            return

        metrics = {
            "session": ("⏱ Session", s_pct),
            "weekly": ("📊 Weekly", w_pct),
            "sonnet": ("🎯 Sonnet", sn_pct),
        }
        now = time.time()

        for key, (label, pct) in metrics.items():
            if pct is None:
                continue
            prev = self._prev_pct.get(key)

            # High usage alert (>= 80%)
            if pct >= NOTIF_THRESHOLD:
                last = self._notif_sent.get(f"{key}_high", 0)
                if now - last >= NOTIF_COOLDOWN:
                    self._notif_sent[f"{key}_high"] = now
                    self._send_notification(
                        title="⚠️ Claude Usage High",
                        message=f"{label} usage is at {int(pct)}%",
                    )

            # Recovery alert: was high (>= 60%), now low (< 30%)
            if prev is not None and prev >= 60 and pct < 30:
                last = self._notif_sent.get(f"{key}_recovered", 0)
                if now - last >= NOTIF_COOLDOWN:
                    self._notif_sent[f"{key}_recovered"] = now
                    self._send_notification(
                        title="✅ Claude Usage Available",
                        message=f"{label} dropped to {int(pct)}% — good to go",
                    )

            self._prev_pct[key] = pct

        # Reset soon alert: session was high and resets within 20 minutes
        if session_resets_at and s_pct is not None:
            try:
                target = datetime.fromisoformat(session_resets_at)
                remaining = (target - datetime.now(timezone.utc)).total_seconds()
                prev_s = self._prev_pct.get("session_was_high", False)
                if s_pct >= 60:
                    self._prev_pct["session_was_high"] = True
                if prev_s and 0 < remaining <= 1200:  # within 20 min
                    last = self._notif_sent.get("session_reset_soon", 0)
                    if now - last >= NOTIF_COOLDOWN:
                        self._notif_sent["session_reset_soon"] = now
                        mins = int(remaining / 60)
                        self._send_notification(
                            title="🔄 Session Resetting Soon",
                            message=f"Session resets in {mins}m — usage will drop",
                        )
                if remaining <= 0:
                    self._prev_pct["session_was_high"] = False
            except Exception:
                pass

    @staticmethod
    def _send_notification(title: str, message: str):
        """Send a macOS notification via osascript."""
        try:
            script = (
                f'display notification "{message}" '
                f'with title "{title}" '
                f'sound name "Ping"'
            )
            subprocess.run(
                ["osascript", "-e", script],
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass

    # ── Button callbacks ───────────────────────────────────────────────────────

    def manual_refresh(self, _):
        """Force-refresh, bypassing rate limit."""
        self.last_fetch = 0
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def toggle_notifications(self, sender):
        self._notifications_enabled = not self._notifications_enabled
        state = "ON" if self._notifications_enabled else "OFF"
        sender.title = f"🔔 Notifications: {state}"
        # Clear cooldown history when re-enabling
        if self._notifications_enabled:
            self._notif_sent.clear()

    # ── Auto-refresh timer ─────────────────────────────────────────────────────

    @rumps.timer(REFRESH_INTERVAL)
    def auto_refresh(self, _):
        threading.Thread(target=self._do_refresh, daemon=True).start()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ClaudeUsageApp().run()
