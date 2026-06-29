# harness

Claude Code로 복잡한 작업을 **phase → step 단위로 쪼개서 자동 실행**하는 프레임워크입니다.
[jha0313/harness_framework](https://github.com/jha0313/harness_framework)의 실행 모델을 기반으로, 안전성·토큰 효율·검증 정책을 보강했습니다.

---

## 왜 이걸 쓰나요?

Claude Code에 "이것 다 해줘"라고 하면 중간에 길을 잃거나, 너무 많은 변경을 한꺼번에 해서 검토가 어렵습니다.
이 하네스는 작업을 **독립된 step 파일**로 미리 설계한 뒤, Python 스크립트가 하나씩 Claude에게 실행시킵니다.
각 step은 실패하면 자동 retry, 완료되면 commit, 요약까지 남깁니다.

---

## 필수 환경

| 도구 | 버전 | 용도 |
|------|------|------|
| Python | 3.10 이상 | `scripts/execute.py` 실행 |
| Node.js | 18 이상 | 안전 hook (`pre-bash-guard.js`, `post-tool-audit.js`) |
| Claude Code | 최신 | step 실행 주체 |
| Git | 2.x | branch/commit 자동화 |

---

## 디렉토리 구조

```
harness/
├── scripts/
│   ├── execute.py                  # phase 실행 스크립트 (핵심)
│   └── generate_harness_digest.py  # docs 요약본 생성
│
├── phases/
│   ├── index.json                  # 전체 phase 현황
│   └── _template/                  # 새 phase 만들 때 복사
│       ├── index.json
│       └── step0.md
│
├── docs/
│   └── HARNESS_DIGEST.md           # CLAUDE.md + docs 요약본 (자동 생성)
│
├── .claude/
│   ├── commands/
│   │   ├── harness.md              # /harness 슬래시 명령
│   │   └── review.md               # /review 슬래시 명령
│   ├── harness/
│   │   ├── README.md               # 하네스 운영 가이드 (상세)
│   │   ├── bin/
│   │   │   ├── pre-bash-guard.js   # 위험 명령 차단 hook
│   │   │   └── post-tool-audit.js  # 도구 사용 감사 로그
│   │   └── docs/                   # 각 레이어 설명 문서
│   └── settings.local.json         # hook 등록 (gitignore, 로컬 전용)
│
├── CLAUDE.md                       # 프로젝트별 규칙 (여기에 프로젝트 정보 작성)
├── CLAUDE.local.md                 # 하네스 운영 정책 (gitignore)
└── .gitignore
```

---

## 빠른 시작

### 1단계 — 이 저장소를 클론하거나 새 프로젝트에 복사

```bash
git clone https://github.com/osmindev-ui/harness.git my-project
cd my-project
```

### 2단계 — hook 파일 생성

`.claude/settings.local.json`을 아래 내용으로 생성합니다.
(이 파일은 `.gitignore`에 포함되어 있어 커밋되지 않습니다.)

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

### 3단계 — 프로젝트 정보 입력

`CLAUDE.md`를 열어 `{프로젝트명}`, `{Framework}` 등의 플레이스홀더를 실제 정보로 교체합니다.

```bash
# HARNESS_DIGEST.md도 최신화
python scripts/generate_harness_digest.py
```

### 4단계 — phase 설계 및 실행

Claude Code에서 `/harness`를 입력하면 대화식으로 phase와 step을 설계해줍니다.

```bash
# dry-run으로 먼저 검증 (실제 Claude 호출 없음)
python scripts/execute.py 0-mvp --dry-run

# 실제 실행
python scripts/execute.py 0-mvp
```

---

## phase / step 구조

### phase란?

하나의 큰 기능 단위입니다. 예: `0-mvp`, `auth-flow`, `payment-integration`

```
phases/
└── 0-mvp/
    ├── index.json      # step 목록 + 상태
    ├── step0.md        # step 0 명세
    ├── step1.md        # step 1 명세
    ├── step0-output.json    # Claude 실행 결과 (gitignore)
    └── step0-summary.md     # 한국어 요약 (자동 생성)
```

### index.json 예시

```json
{
  "project": "my-app",
  "phase": "0-mvp",
  "steps": [
    {
      "step": 0,
      "name": "project-setup",
      "status": "pending",
      "risk_level": "low",
      "verification_command": "npm run build"
    },
    {
      "step": 1,
      "name": "core-types",
      "status": "pending",
      "risk_level": "low",
      "verification_command": "npm test -- src/types"
    }
  ]
}
```

`execute.py`가 step을 실행하면 `status`, `started_at`, `completed_at`, `summary` 등을 자동으로 채워줍니다.

### step 상태

| status | 의미 |
|--------|------|
| `pending` | 아직 실행 전 |
| `completed` | Acceptance Criteria 통과, 한 줄 summary 기록됨 |
| `error` | 최대 retry 후에도 실패, `error_message` 기록됨 |
| `blocked` | 사람의 개입 필요, `blocked_reason` 기록됨 |

### step 파일 (step0.md) 구조

헤딩 이름은 **반드시 영어 그대로** 유지해야 합니다. 스크립트가 이 이름에 의존합니다.

```markdown
## Goal
이 step이 달성해야 할 단일 목적.

## Scope
다루는 파일/모듈 범위.

## Out of scope
이 step에서 하지 않는 것. (자동 리팩토링 방지에 중요)

## Files likely involved
- `src/index.ts`
- `package.json`

## Acceptance Criteria
- `npm run build`가 에러 없이 완료된다.
- `npm test`가 통과한다.

## Verification Command
\`\`\`bash
npm run build && npm test
\`\`\`

## Rollback Notes
- `git revert <commit>` 또는 `git restore --staged --worktree -- <path>`

## Risk Level
low

## Docs
- `docs/HARNESS_DIGEST.md`
```

### Risk Level 기준

| 레벨 | 해당하는 작업 | 특이사항 |
|------|-------------|---------|
| `low` | 기능 추가, 스타일, 문서 | 기본 동작 |
| `medium` | 로직 변경, 비민감 API | 신중한 검토 |
| `high` | auth, payment, 보안, migration, schema, 파괴적 변경 | Caveman/Headroom output shaping 자동 비활성 |

---

## execute.py 플래그 전체

```bash
python scripts/execute.py <phase-dir> [옵션]
```

| 플래그 | 기본값 | 설명 |
|--------|--------|------|
| `--dry-run` | off | Claude 호출 없이 step plan만 출력 |
| `--no-branch` | off | branch checkout 없이 현재 branch에서 실행 |
| `--no-commit` | off | git commit 건너뜀 |
| `--push` | off | phase 완료 후 원격 push |
| `--max-retries N` | 3 | step당 최대 재시도 횟수 |
| `--docs-mode` | `digest` | 가드레일 주입 방식 (`full` / `digest` / `step`) |
| `--verify-mode` | `targeted` | 검증 방식 (`none` / `targeted` / `full`) |
| `--timeout-seconds N` | 1800 | Claude subprocess timeout (초) |
| `--headroom` | off | Headroom 래퍼 사용 (설치된 경우만) |
| `--caveman-off` | off | 프롬프트에 Caveman brevity 사용 금지 명시 |
| `--unsafe-skip-permissions` | off | `--dangerously-skip-permissions` 전달 (신뢰 환경 전용) |

### docs-mode 설명

| 모드 | 동작 | 추천 상황 |
|------|------|-----------|
| `digest` | `docs/HARNESS_DIGEST.md`만 주입 | 일반 개발 (기본값, 토큰 효율적) |
| `full` | `CLAUDE.md` + `docs/*.md` 전체 주입 | release, architecture review |
| `step` | step 파일의 `## Docs` 섹션에 명시된 파일만 주입 | step별 최소 컨텍스트 |

---

## 슬래시 명령

Claude Code에서 직접 사용할 수 있는 명령입니다.

### `/harness`

phase와 step을 대화식으로 설계하고 파일을 생성해줍니다.

1. 신규 phase인지 기존 phase 계속 진행인지 선택
2. task name 결정 (kebab-case, 예: `0-mvp`, `auth-flow`)
3. step 설계 초안 작성 → 피드백 → 승인 후 파일 생성
4. 실행 명령 안내

### `/review`

현재 변경사항을 리뷰합니다. 체크 항목:

- 변경 파일이 phase 설계와 일치하는가
- Acceptance Criteria가 실제로 검증되었는가
- 보안/마이그레이션 위험 항목 여부
- 테스트 evidence 보존 여부

---

## 안전 hook

### pre-bash-guard

위험하거나 토큰을 낭비하는 Bash 명령을 자동으로 차단합니다.

| 차단 패턴 | 이유 | 대안 |
|-----------|------|------|
| `rm -rf` | 되돌릴 수 없는 삭제 | `ls`로 확인 후 경로 명시 |
| `git reset --hard` | working tree 파괴 | `git stash` 후 작업 |
| `git push --force` | 원격 히스토리 덮어쓰기 | `git push --force-with-lease` |
| `DROP TABLE` | 영구 데이터 손실 | backup 후 staging 검증 |
| `cat *.log` | 거대 파일 출력 | `tail -200 <file>` |
| `find .` (maxdepth 없음) | 전체 트리 스캔 | `find . -maxdepth 3` |
| `docker logs` (tail 없음) | 전체 로그 출력 | `docker logs --tail 200` |
| `cat .env` | 시크릿 컨텍스트 유입 | 키 이름만 확인 |

### post-tool-audit

모든 Bash 도구 사용을 `.claude/harness/logs/tool-audit.jsonl`에 기록합니다.
시크릿처럼 보이는 값은 자동으로 `[REDACTED]`로 처리됩니다.

---

## 선택적 최적화 레이어

### Headroom (context compression)

긴 로그나 반복 context를 압축해 input 토큰을 줄입니다.

```bash
python scripts/execute.py <phase> --headroom
```

- `headroom`이 PATH에 없으면 경고 후 일반 `claude`로 fallback합니다.
- `high` risk step에서는 output shaping이 자동 비활성됩니다.
- 자세한 환경 변수 설정은 `.claude/harness/docs/headroom.md` 참고.

### Caveman (output brevity)

Claude 응답을 간결하게 압축해 output 토큰을 줄입니다.

```bash
python scripts/execute.py <phase> --caveman-off  # 명시적으로 비활성
```

- `high` risk step에서는 executor가 자동으로 비활성 지침을 추가합니다.
- 설계 reasoning, test evidence, error 원문은 항상 보존됩니다.

### ccusage (토큰 측정)

최적화 적용 전후 효과를 반드시 측정합니다.

```bash
# 최적화 전 baseline 기록
npx ccusage@latest > .claude/harness/logs/ccusage-baseline.txt

# 최적화 후 비교
npx ccusage@latest > .claude/harness/logs/ccusage-after.txt
```

---

## 전형적인 워크플로우

```
1. /harness                          # step 설계
2. python scripts/execute.py 0-mvp --dry-run   # 구조 확인
3. python scripts/execute.py 0-mvp             # 실행
4. /review                           # 변경사항 리뷰
5. npx ccusage@latest                # 토큰 사용 확인
6. git push origin feat-0-mvp        # PR 생성
```

---

## 자주 묻는 질문

**Q. step이 `error` 상태가 됐어요.**

`phases/{task}/index.json`에서 해당 step의 `status`를 `"pending"`으로 되돌리고, `error_message`를 확인한 뒤 다시 실행하세요.

```bash
python scripts/execute.py <phase>
```

**Q. `blocked` 상태는 뭔가요?**

Claude가 사람의 결정 없이는 진행할 수 없다고 판단한 상태입니다.
`blocked_reason`을 읽고 필요한 조치를 취한 뒤 `status`를 `"pending"`으로 되돌리면 됩니다.

**Q. HARNESS_DIGEST.md는 언제 다시 생성하나요?**

`CLAUDE.md`나 `docs/*.md`를 수정했을 때 다시 실행합니다.

```bash
python scripts/generate_harness_digest.py
```

**Q. phase branch가 필요 없어요.**

```bash
python scripts/execute.py <phase> --no-branch
```

**Q. commit은 나중에 직접 하고 싶어요.**

```bash
python scripts/execute.py <phase> --no-commit
```

---

## 안전 원칙

- `--unsafe-skip-permissions`는 신뢰된 로컬 환경에서만 사용합니다. 사용 시 `step-output.json`에 `unsafe_permissions: true`로 기록됩니다.
- `CLAUDE.md`는 자동으로 수정되지 않습니다. 직접 편집하세요.
- `CLAUDE.local.md`와 `settings.local.json`은 gitignore에 포함되어 커밋되지 않습니다.
- Stop hook은 의도적으로 **등록하지 않습니다**. 매 step마다 full lint/build/test를 자동 실행하지 않습니다.

---

## 참고 문서

| 파일 | 내용 |
|------|------|
| `.claude/harness/README.md` | 하네스 운영 가이드 상세 |
| `.claude/harness/docs/headroom.md` | Headroom 통합 가이드 |
| `.claude/harness/docs/caveman.md` | Caveman 통합 가이드 |
| `.claude/harness/docs/superpowers.md` | Superpowers 통합 가이드 |
| `.claude/harness/docs/usage.md` | ccusage 측정 가이드 |
| `.claude/harness/docs/rtk.md` | RTK 사용 정책 |
| `phases/_template/step0.md` | step 파일 템플릿 |
