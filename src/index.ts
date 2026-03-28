#!/usr/bin/env tsx
import { execSync } from 'child_process';
import chalk from 'chalk';

// ─── Types ────────────────────────────────────────────────────────────────────

interface UsageWindow {
  utilization: number;
  resets_at: string;
}

interface UsageResponse {
  five_hour: UsageWindow;
  seven_day: UsageWindow;
  seven_day_sonnet: UsageWindow;
  extra_usage: { is_enabled: boolean };
}

interface ParsedUsage {
  session: { pct: number; resetsIn: string };
  weekly: { pct: number; resetsIn: string };
  sonnet: { pct: number; resetsIn: string };
  extraUsage: boolean;
  fetchedAt: Date;
}

// ─── Keychain ─────────────────────────────────────────────────────────────────

function getAccessToken(): string {
  try {
    const tokenJson = execSync(
      'security find-generic-password -s "Claude Code-credentials" -w',
      { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }
    ).trim();
    const parsed = JSON.parse(tokenJson);
    const token = parsed?.claudeAiOauth?.accessToken;
    if (!token) throw new Error('accessToken not found in keychain entry');
    return token;
  } catch (err: any) {
    throw new Error(`Failed to read token from Keychain: ${err.message}`);
  }
}

// ─── API ──────────────────────────────────────────────────────────────────────

async function fetchUsage(token: string): Promise<UsageResponse> {
  const res = await fetch('https://api.anthropic.com/api/oauth/usage', {
    headers: {
      Authorization: `Bearer ${token}`,
      'anthropic-beta': 'oauth-2025-04-20',
    },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<UsageResponse>;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeUntil(isoDate: string): string {
  const diff = new Date(isoDate).getTime() - Date.now();
  if (diff <= 0) return 'now';
  const h = Math.floor(diff / 3_600_000);
  const d = Math.floor(h / 24);
  if (d >= 2) return `${d}d`;
  if (h >= 1) return `${h}h`;
  const m = Math.floor(diff / 60_000);
  return `${m}m`;
}

function parseResponse(data: UsageResponse): ParsedUsage {
  return {
    session: {
      pct: Math.round(data.five_hour.utilization),
      resetsIn: timeUntil(data.five_hour.resets_at),
    },
    weekly: {
      pct: Math.round(data.seven_day.utilization),
      resetsIn: timeUntil(data.seven_day.resets_at),
    },
    sonnet: {
      pct: Math.round(data.seven_day_sonnet.utilization),
      resetsIn: timeUntil(data.seven_day_sonnet.resets_at),
    },
    extraUsage: data.extra_usage.is_enabled,
    fetchedAt: new Date(),
  };
}

// ─── Rendering ────────────────────────────────────────────────────────────────

const BOX_WIDTH = 44; // inner content width (between │ and │)

function colorize(pct: number, text: string): string {
  if (pct >= 80) return chalk.red(text);
  if (pct >= 60) return chalk.yellow(text);
  return chalk.green(text);
}

function progressBar(pct: number, width = 20): string {
  const filled = Math.round((pct / 100) * width);
  const empty = width - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);
  return colorize(pct, bar);
}

function pad(text: string, width: number): string {
  // strips ANSI escape codes for length calculation
  const ansiRe = /\x1B\[[0-9;]*m/g;
  const visible = text.replace(ansiRe, '');
  const spaces = Math.max(0, width - visible.length);
  return text + ' '.repeat(spaces);
}

function row(content: string): string {
  const ansiRe = /\x1B\[[0-9;]*m/g;
  const visible = content.replace(ansiRe, '');
  const spaces = Math.max(0, BOX_WIDTH - visible.length);
  return `│ ${content}${' '.repeat(spaces)} │`;
}

function emptyRow(): string {
  return `│${' '.repeat(BOX_WIDTH + 2)}│`;
}

function metricRows(icon: string, label: string, pct: number, resetsIn: string): string[] {
  const pctStr = colorize(pct, `${pct}%`);
  const headerLine = `${icon}  ${chalk.bold(label.padEnd(18))}${pctStr}`;
  const barLine = `   ${progressBar(pct)}  ${chalk.dim(`resets ${resetsIn}`)}`;
  return [row(headerLine), row(barLine)];
}

function renderBox(usage: ParsedUsage): string {
  const top =    `╭${'─'.repeat(BOX_WIDTH + 2)}╮`;
  const bottom = `╰${'─'.repeat(BOX_WIDTH + 2)}╯`;
  const divider = `├${'─'.repeat(BOX_WIDTH + 2)}┤`;

  const title = chalk.bold.cyan('Claude Code Usage Monitor');
  const titlePad = Math.floor((BOX_WIDTH - 25) / 2); // 25 = visible length of title
  const titleRow = `│${' '.repeat(titlePad + 1)}${title}${' '.repeat(BOX_WIDTH - titlePad - 25 + 1)}│`;

  const timeStr = usage.fetchedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const checkedLine = `${chalk.dim('Last checked:')} ${chalk.white(timeStr)}`;

  const extraLine = usage.extraUsage
    ? row(`${chalk.green('✓')}  ${chalk.dim('Extra usage enabled')}`)
    : '';

  const lines = [
    top,
    titleRow,
    divider,
    emptyRow(),
    ...metricRows('⏱', 'Session (5h)', usage.session.pct, usage.session.resetsIn),
    emptyRow(),
    ...metricRows('📊', 'Weekly (All)', usage.weekly.pct, usage.weekly.resetsIn),
    emptyRow(),
    ...metricRows('🎯', 'Sonnet Only', usage.sonnet.pct, usage.sonnet.resetsIn),
    emptyRow(),
    ...(extraLine ? [extraLine, emptyRow()] : []),
    row(checkedLine),
    bottom,
  ];

  return lines.join('\n');
}

// ─── Output modes ─────────────────────────────────────────────────────────────

function outputJson(usage: ParsedUsage): void {
  console.log(JSON.stringify({
    session_pct: usage.session.pct,
    session_resets_in: usage.session.resetsIn,
    weekly_pct: usage.weekly.pct,
    weekly_resets_in: usage.weekly.resetsIn,
    sonnet_pct: usage.sonnet.pct,
    sonnet_resets_in: usage.sonnet.resetsIn,
    extra_usage: usage.extraUsage,
    fetched_at: usage.fetchedAt.toISOString(),
    max_pct: Math.max(usage.session.pct, usage.weekly.pct, usage.sonnet.pct),
  }, null, 2));
}

const THRESHOLD = 80;

function checkThresholds(usage: ParsedUsage): boolean {
  const issues: string[] = [];
  if (usage.session.pct >= THRESHOLD) issues.push(`Session at ${usage.session.pct}%`);
  if (usage.weekly.pct >= THRESHOLD) issues.push(`Weekly at ${usage.weekly.pct}%`);
  if (usage.sonnet.pct >= THRESHOLD) issues.push(`Sonnet at ${usage.sonnet.pct}%`);
  if (issues.length) {
    console.error(chalk.red(`⚠️  Usage threshold exceeded: ${issues.join(', ')}`));
    return true;
  }
  return false;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const jsonMode = args.includes('--json');
  const checkMode = args.includes('--check');

  let token: string;
  try {
    token = getAccessToken();
  } catch (err: any) {
    if (jsonMode) {
      console.error(JSON.stringify({ error: err.message }));
    } else {
      console.error(chalk.red(`✗ ${err.message}`));
    }
    process.exit(2);
  }

  let data: UsageResponse;
  try {
    data = await fetchUsage(token);
  } catch (err: any) {
    if (jsonMode) {
      console.error(JSON.stringify({ error: err.message }));
    } else {
      console.error(chalk.red(`✗ ${err.message}`));
    }
    process.exit(2);
  }

  const usage = parseResponse(data);

  if (jsonMode) {
    outputJson(usage);
    return;
  }

  console.log();
  console.log(renderBox(usage));
  console.log();

  if (checkMode && checkThresholds(usage)) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(chalk.red(`Fatal: ${err.message}`));
  process.exit(2);
});
