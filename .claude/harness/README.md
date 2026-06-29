# .claude/harness — 하네스 운영 가이드

이 하네스는 [jha0313/harness_framework](https://github.com/jha0313/harness_framework)의 phase/step 실행 모델을 보존하면서 약점을 보강한 것이다.

## 보존된 것

- `phases/index.json` (top-level)
- `phases/{task}/index.json` (task 상세)
- `phases/{task}/stepN.md` (각 step)
- 순차 step 실행 + retry (기본 3회)
- 이전 step `summary` 컨텍스트 누적
- `CLAUDE.md` + `docs/*.md` 가드레일 주입 (기본은 digest 모드)
- branch-per-phase (`feat-{phase}`)
- 2단계 commit (`feat({phase}): ...` + `chore({phase}): ...`)
- `created_at` / `started_at` / `completed_at` / `failed_at` / `blocked_at` 자동 기록
- status enum: `pending` / `completed` / `error` / `blocked`

## 개선된 것

- `--dangerously-skip-permissions` **기본 OFF**. `--unsafe-skip-permissions`로 명시 opt-in.
- CLI 플래그 확장: `--no-commit` / `--no-branch` / `--dry-run` / `--headroom` / `--caveman-off` / `--max-retries N` / `--docs-mode {full|digest|step}` / `--verify-mode {none|targeted|full}` / `--timeout-seconds N` / `--push`
- `docs-mode` 도입 — 매 step에 모든 docs를 주입하지 않음.
- Korean `step{N}-summary.md` 자동 작성 (영어 evidence 보존).
- Headroom optional wrapper 통합.
- Caveman selective (high risk step에서 자동 비활성).
- PreToolUse Bash guard / PostToolUse audit (Node, no deps).
- HARNESS_DIGEST 생성기 (`scripts/generate_harness_digest.py`).

## 디렉토리 구조

```
.claude/
  commands/
    harness.md         # /harness 명령
    review.md          # /review 명령
  harness/
    README.md          # 이 파일
    bin/
      pre-bash-guard.js
      post-tool-audit.js
    docs/
      headroom.md
      caveman.md
      superpowers.md
      usage.md
      rtk.md
    logs/              # tool-audit.jsonl 등 (gitignore)
scripts/
  execute.py
  generate_harness_digest.py
docs/
  HARNESS_DIGEST.md    # generate_harness_digest.py로 갱신
phases/
  index.json
  _template/
    index.json
    step0.md
```

## 안전 hook 등록 (수동 작성 필요)

`.claude/settings.local.json`을 사용자가 직접 생성한다.
hook 등록은 Claude Code Auto Mode의 self-modification 보호로 자동 작성이 차단된다.

다음 JSON을 `.claude/settings.local.json`에 저장:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "node .claude/harness/bin/pre-bash-guard.js"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "node .claude/harness/bin/post-tool-audit.js"
          }
        ]
      }
    ]
  }
}
```

`.gitignore`에 `.claude/settings.local.json`이 이미 등록되어 있으므로 commit되지 않는다.
Stop hook은 의도적으로 **추가하지 않는다** (full lint/build/test 자동 실행 금지 정책).

## 사용 흐름

### 1. phase 생성

`/harness` 명령을 사용하거나 직접 작성.

- `phases/{task}/index.json` 생성
- `phases/{task}/stepN.md` 작성 (`_template/step0.md` 참고)
- `phases/index.json`의 `phases` 배열에 항목 추가

### 2. 실행

```bash
python scripts/execute.py {task} --dry-run     # 검증만
python scripts/execute.py {task}               # 실제 실행 (기본 docs-mode=digest, verify-mode=targeted)
python scripts/execute.py {task} --headroom    # Headroom 래퍼 사용 (설치된 경우)
python scripts/execute.py {task} --push        # 완료 후 push
```

### 3. Headroom과 함께

`headroom`이 PATH에 있으면 `--headroom`이 `headroom wrap claude ...`로 래핑.
없으면 경고 후 일반 `claude` 사용. 자동 설치 없음.

### 4. Caveman 비활성

- `--caveman-off`로 프롬프트에 명시.
- step의 `risk_level`이 `high`면 executor가 자동으로 비활성 지침 추가.

### 5. 리뷰

```bash
# /review 명령으로 변경사항 + verification + 보안 체크
```

### 6. 측정

```bash
npx ccusage@latest
```

## 안전 경고

- `--unsafe-skip-permissions`는 신뢰 환경에서만. 사용 시 step-output.json에 `unsafe_permissions: true` 기록.
- 명령을 silent rewrite하지 않는다. 위험 명령은 차단 후 한국어 사유와 영어 대안을 제시.
- Headroom output shaping과 Caveman을 동시에 활성하지 않는다.
- `high` risk step에서는 Caveman/Headroom output shaping을 끈다.

## 언어 정책

- Markdown 본문: 한국어
- 명령/경로/CLI 플래그/환경변수/JSON 키/enum 값/식별자/error message/stack trace/test name/migration name: **영어 보존**
- 보존이 필수인 식별자 예: `Superpowers`, `Headroom`, `Caveman`, `ccusage`, `RTK`, `Claude Code`, `PreToolUse`, `PostToolUse`, `Stop hook`, `Bash`, `CLAUDE.md`, `CLAUDE.local.md`, `settings.json`, `execute.py`, `Acceptance Criteria`, `Verification Command`, `Rollback Notes`, `Risk Level`, `Docs`, `Goal`, `Scope`, `Out of scope`, `Files likely involved`, `pending`, `completed`, `error`, `blocked`, `low`, `medium`, `high`, `full`, `digest`, `step`, `targeted`
