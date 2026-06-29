#!/usr/bin/env node
/*
 * PreToolUse Bash guard.
 * Reads hook payload JSON from stdin. If the Bash command matches a dangerous
 * or token-heavy pattern, exit 2 with a Korean explanation + safer English
 * alternative on stderr (Claude Code's standard deny path).
 *
 * No external dependencies.
 *
 * Activation: register in .claude/settings.local.json (see harness README).
 */
'use strict';

function readStdin() {
  return new Promise((resolve) => {
    let buf = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { buf += chunk; });
    process.stdin.on('end', () => resolve(buf));
    process.stdin.on('error', () => resolve(buf));
    setTimeout(() => resolve(buf), 1500);
  });
}

function deny(reason, suggestion) {
  process.stderr.write(`[harness:pre-bash-guard] BLOCK ${reason}\n`);
  if (suggestion) {
    process.stderr.write(`[harness:pre-bash-guard] 대안: ${suggestion}\n`);
  }
  process.exit(2);
}

const RULES = [
  {
    name: 'rm-rf',
    test: /\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b/,
    reason: '`rm -rf`는 되돌릴 수 없는 대량 삭제입니다.',
    suggest: '삭제 대상 경로를 명시하고 `ls`로 먼저 확인하세요.',
  },
  {
    name: 'git-reset-hard',
    test: /\bgit\s+reset\s+--hard\b/,
    reason: '`git reset --hard`는 working tree 변경을 파괴합니다.',
    suggest: '`git stash`로 백업 후 작업하거나 `git restore --source=<sha>`를 검토하세요.',
  },
  {
    name: 'git-clean-fd',
    test: /\bgit\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*d\b/,
    reason: '`git clean -fd`는 untracked 파일을 영구 삭제합니다.',
    suggest: '`git clean -nd`로 dry-run을 먼저 실행하세요.',
  },
  {
    name: 'git-push-force',
    test: /\bgit\s+push\s+(--force\b|-f\b|--force-with-lease=)/,
    reason: '`git push --force`는 원격 히스토리를 덮어씁니다.',
    suggest: '`git push --force-with-lease <remote> <branch>`로 안전성을 확인하세요.',
  },
  {
    name: 'sql-drop-table',
    test: /\bDROP\s+TABLE\b/i,
    reason: '`DROP TABLE`은 영구 데이터 손실 위험.',
    suggest: '먼저 backup/snapshot 후 staging 환경에서 검증.',
  },
  {
    name: 'sql-drop-database',
    test: /\bDROP\s+DATABASE\b/i,
    reason: '`DROP DATABASE`은 영구 데이터 손실 위험.',
    suggest: '먼저 dump 후 검증된 절차로 실행.',
  },
  {
    name: 'truncate-table',
    test: /\bTRUNCATE\s+TABLE\b/i,
    reason: '`TRUNCATE TABLE`은 트랜잭션 롤백이 어려울 수 있음.',
    suggest: '필요 시 `DELETE`와 트랜잭션을 검토.',
  },
  {
    name: 'env-secret-read',
    test: /\b(cat|less|more|head|tail|type)\s+[^\n;|&]*\.env(\.|\b)/,
    reason: '`.env` 파일은 시크릿 가능성. 출력 시 컨텍스트로 유입됨.',
    suggest: '`grep -E "^[A-Z_]+=" .env | sed "s/=.*$/=[REDACTED]/"`로 키만 확인.',
  },
  {
    name: 'cat-lockfile',
    test: /\b(cat|less|more|type)\s+[^\n;|&]*(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb|Cargo\.lock|poetry\.lock|Pipfile\.lock|composer\.lock|Gemfile\.lock)\b/,
    reason: 'lock 파일은 보통 매우 크고 컨텍스트 낭비.',
    suggest: '`wc -l <lockfile>` 또는 `grep -n "<dep>" <lockfile>`로 필요한 부분만 보세요.',
  },
  {
    name: 'cat-minified',
    test: /\b(cat|less|more|type)\s+[^\n;|&]*\.(min\.js|min\.css|map)\b/,
    reason: 'minified/source-map 파일은 사람에게 읽히지 않으며 토큰만 소모.',
    suggest: '원본 소스 파일을 읽으세요.',
  },
  {
    name: 'cat-huge-log',
    test: /\b(cat|less|more|type)\s+[^\n;|&]*\.(log|jsonl|csv|tsv|sql|dump)\b/,
    reason: '로그/덤프 파일은 보통 매우 큼.',
    suggest: '`tail -200 <file>` 또는 `grep -nE "ERROR|FAIL|WARN" <file>`',
  },
  {
    name: 'ls-recursive',
    test: /\bls\s+-[a-zA-Z]*R\b/,
    reason: '`ls -R`는 모든 하위 디렉토리를 평탄화 출력 → 토큰 폭발.',
    suggest: '`find . -maxdepth 3 -type f` 또는 `tree -L 3`',
  },
  {
    name: 'find-no-maxdepth',
    test: /\bfind\b/,
    extra: (cmd) => /\bfind\s+/.test(cmd) && !/-maxdepth\s+\d+/.test(cmd),
    reason: '`find`에 `-maxdepth`가 없어 전체 트리를 스캔.',
    suggest: '`find . -maxdepth 3 ...`로 깊이를 제한하세요.',
  },
  {
    name: 'grep-recursive-root',
    test: /\bgrep\s+-[a-zA-Z]*R\b/,
    extra: (cmd) => /\bgrep\s+-[a-zA-Z]*R\b/.test(cmd) && !/--(include|exclude|exclude-dir)\b/.test(cmd),
    reason: '`grep -R`을 include/exclude 없이 실행하면 node_modules 등까지 스캔.',
    suggest: '`grep -Rn --include="*.ts" --exclude-dir=node_modules <pat> <path>` (또는 Grep 도구 사용)',
  },
  {
    name: 'tree-no-limit',
    test: /\btree\b/,
    extra: (cmd) => /\btree\b/.test(cmd) && !/-L\s+\d+/.test(cmd),
    reason: '`tree`에 `-L` 깊이 제한이 없음.',
    suggest: '`tree -L 3` 또는 `tree -L 2`',
  },
  {
    name: 'docker-logs-no-tail',
    test: /\bdocker\s+logs\b/,
    extra: (cmd) => /\bdocker\s+logs\b/.test(cmd) && !/--tail(\s+|=)\d+/.test(cmd),
    reason: '`docker logs`에 `--tail`이 없어 전체 로그 출력.',
    suggest: '`docker logs --tail 200 <container>`',
  },
  {
    name: 'kubectl-logs-no-tail',
    test: /\bkubectl\s+logs\b/,
    extra: (cmd) => /\bkubectl\s+logs\b/.test(cmd) && !/--tail(\s+|=)\d+/.test(cmd),
    reason: '`kubectl logs`에 `--tail`이 없어 전체 로그 출력.',
    suggest: '`kubectl logs --tail=200 <pod>`',
  },
  {
    name: 'journalctl-no-limit',
    test: /\bjournalctl\b/,
    extra: (cmd) => /\bjournalctl\b/.test(cmd) && !/(-n\s+\d+|--lines(\s+|=)\d+|--since\b)/.test(cmd),
    reason: '`journalctl`에 라인/시간 제한이 없음.',
    suggest: '`journalctl -n 200 -u <unit>` 또는 `journalctl --since "10 min ago"`',
  },
];

(async () => {
  const raw = await readStdin();
  let payload;
  try {
    payload = JSON.parse(raw || '{}');
  } catch {
    process.exit(0);
  }

  const toolName = payload.tool_name || payload.toolName;
  if (toolName !== 'Bash') process.exit(0);

  const input = payload.tool_input || payload.toolInput || {};
  const cmd = (input.command || '').toString();
  if (!cmd) process.exit(0);

  for (const rule of RULES) {
    let hit = rule.test.test(cmd);
    if (hit && typeof rule.extra === 'function') hit = rule.extra(cmd);
    if (hit) {
      deny(`[${rule.name}] ${rule.reason}`, rule.suggest);
    }
  }
  process.exit(0);
})();
