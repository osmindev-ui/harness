#!/usr/bin/env node
/*
 * PostToolUse audit.
 * Appends a compact JSONL record to .claude/harness/logs/tool-audit.jsonl.
 * Never stores full tool output. Redacts likely secrets in the command string.
 *
 * No external dependencies.
 *
 * Activation: register in .claude/settings.local.json (see harness README).
 */
'use strict';

const fs = require('fs');
const path = require('path');

const LOG_DIR = path.join('.claude', 'harness', 'logs');
const LOG_FILE = path.join(LOG_DIR, 'tool-audit.jsonl');

function readStdin() {
  return new Promise((resolve) => {
    let buf = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (c) => { buf += c; });
    process.stdin.on('end', () => resolve(buf));
    process.stdin.on('error', () => resolve(buf));
    setTimeout(() => resolve(buf), 1500);
  });
}

function redact(text) {
  if (!text) return text;
  let s = String(text);
  // Authorization / Bearer headers
  s = s.replace(/(Authorization\s*[:=]\s*)(Bearer\s+)?[A-Za-z0-9._-]+/gi, '$1[REDACTED]');
  s = s.replace(/Bearer\s+[A-Za-z0-9._-]+/gi, 'Bearer [REDACTED]');
  // cookie / password / token / api key assignments
  s = s.replace(/(cookie|password|passwd|secret|token|api[_-]?key)\s*[:=]\s*([^\s'"&;|]+)/gi, '$1=[REDACTED]');
  // PEM block headers (don't store keys)
  s = s.replace(/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g, '[REDACTED PRIVATE KEY]');
  // long opaque tokens (>=32 chars, base64/hex-like)
  s = s.replace(/\b([A-Za-z0-9_-]{32,})\b/g, (m) => {
    if (/^[A-Za-z]+$/.test(m)) return m;
    return '[REDACTED:' + m.length + ']';
  });
  // .env style KEY=VALUE redaction
  s = s.replace(/(^|\s)([A-Z][A-Z0-9_]{2,})=([^\s'"&;|]+)/g, '$1$2=[REDACTED]');
  return s;
}

const RISKY = [
  /\brm\s+-/,
  /\bgit\s+(reset\s+--hard|clean\s+-|push\s+(--force|-f))/,
  /\bDROP\s+(TABLE|DATABASE)\b/i,
  /\bTRUNCATE\s+TABLE\b/i,
  /\bsudo\b/,
  /\bchmod\s+(-R\s+)?[0-7]*7[0-7]{2}\b/,
  /\bcurl\b[^\n;|&]*\|\s*(bash|sh|zsh)\b/,
  /\bwget\b[^\n;|&]*\|\s*(bash|sh|zsh)\b/,
];

function isRisky(cmd) {
  return RISKY.some((r) => r.test(cmd));
}

(async () => {
  const raw = await readStdin();
  let payload;
  try {
    payload = JSON.parse(raw || '{}');
  } catch {
    process.exit(0);
  }

  const toolName = payload.tool_name || payload.toolName || 'unknown';
  const input = payload.tool_input || payload.toolInput || {};
  const response = payload.tool_response || payload.toolResponse || {};

  const cmd = (input.command || '').toString();
  const stdout = (response.stdout || response.output || '').toString();
  const stderr = (response.stderr || '').toString();
  const outputSize = stdout.length + stderr.length;

  const record = {
    ts: new Date().toISOString(),
    tool: toolName,
    cmd_summary: redact(cmd).slice(0, 280),
    output_bytes: outputSize,
    large_output: outputSize >= 4000,
    risky: toolName === 'Bash' && isRisky(cmd),
    exit_code: typeof response.exit_code === 'number' ? response.exit_code : null,
  };

  try {
    fs.mkdirSync(LOG_DIR, { recursive: true });
    fs.appendFileSync(LOG_FILE, JSON.stringify(record) + '\n');
  } catch {
    // never fail the tool call because of audit
  }
  process.exit(0);
})();
