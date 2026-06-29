# /harness

jha0313/harness_framework 스타일 phase/step 워크플로우를 실행하는 명령. 본 명령은 호출 시 다음 순서대로 작업한다.

---

## 0. 사전 확인

- 사용자에게 **신규 phase 생성**인지 **기존 phase 계속 진행**인지 묻는다.
- 신규 phase면 task name(kebab-case)을 묻는다. 예: `0-mvp`, `auth-flow`.
- 작업 디렉토리에 `phases/`, `docs/`, `scripts/execute.py`가 존재하는지 확인한다. 없으면 하네스 부트스트랩이 누락된 것.

## A. 탐색

`docs/HARNESS_DIGEST.md`(존재 시) 또는 `docs/*.md`를 읽고 프로젝트 의도를 파악한다. 필요 시 Explore 에이전트를 병렬로 사용한다.

## B. 논의

구현 전 기술적으로 결정해야 할 사항이 있으면 AskUserQuestion으로 사용자와 논의한다. 구현에 들어가기 전에 모호한 부분을 남기지 않는다.

## C. Step 설계

여러 step으로 나뉜 초안을 작성해 사용자 피드백을 받는다.

**설계 원칙**

1. **Scope 최소화** — 하나의 step에서 하나의 레이어 또는 모듈만 다룬다.
2. **자기완결성** — 각 step 파일은 독립된 Claude 세션에서 실행된다. "이전 대화" 참조 금지.
3. **사전 준비 강제** — 관련 docs 경로와 이전 step 산출 파일 경로를 명시한다.
4. **시그니처 수준 지시** — 인터페이스만 제시. 단, 멱등성/보안/데이터 무결성 등 핵심 규칙은 명시.
5. **AC는 실행 가능한 커맨드** — `npm run build && npm test`처럼 실제 실행 가능한 verification command.
6. **주의사항은 구체적으로** — "X를 하지 마라. 이유: Y" 형식.
7. **네이밍** — step name은 kebab-case.

## D. 파일 생성

사용자가 승인하면 다음 파일을 생성한다.

### D-1. `phases/index.json` (전체 현황)

```json
{
  "phases": [
    { "dir": "0-mvp", "status": "pending" }
  ]
}
```

- `dir`: task 디렉토리명.
- `status`: `pending` | `completed` | `error` | `blocked`. execute.py가 자동 갱신.

### D-2. `phases/{task-name}/index.json` (task 상세)

```json
{
  "project": "<프로젝트명>",
  "phase": "<task-name>",
  "steps": [
    { "step": 0, "name": "project-setup", "status": "pending", "risk_level": "low" },
    { "step": 1, "name": "core-types", "status": "pending", "risk_level": "low" }
  ]
}
```

| 필드 | 규칙 |
|---|---|
| `steps[].step` | 0부터 시작. |
| `steps[].name` | kebab-case slug. |
| `steps[].status` | 초기 `pending`. |
| `steps[].risk_level` | `low` / `medium` / `high`. high는 Caveman style brevity 자동 비활성. |
| `steps[].summary` | 완료 시 한 줄 요약 (Claude 세션이 기록). |
| `steps[].verification_command` | (선택) `--verify-mode=targeted`에서 실행. |

상태 전이 시 execute.py가 timestamp(`started_at`, `completed_at`, `failed_at`, `blocked_at`)와 status를 자동 기록한다.

### D-3. `phases/{task-name}/step{N}.md` (각 step)

`phases/_template/step0.md`를 복제해 사용. 다음 헤딩은 **반드시** 영어 그대로 유지(스크립트가 의존):

- `## Goal`
- `## Scope`
- `## Out of scope`
- `## Files likely involved`
- `## Acceptance Criteria`
- `## Verification Command`
- `## Rollback Notes`
- `## Risk Level`
- `## Docs`

각 헤딩 아래 본문은 한국어로 작성. 단, 명령/경로/식별자는 영어 그대로.

### Risk Level 가이드

| risk | 설명 | 영향 |
|---|---|---|
| `low` | 단순 기능 추가/스타일/문서 | Caveman 사용 가능 |
| `medium` | 비-시크릿 비-스키마 로직 변경 | 신중한 검토 |
| `high` | auth/payment/security/permission/migration/schema/destructive | Caveman/Headroom output shaping 비활성 |

## E. 실행

```bash
python scripts/execute.py {task-name}                   # 기본 (docs-mode=digest, verify-mode=targeted)
python scripts/execute.py {task-name} --dry-run         # 실제 실행 없이 검증만
python scripts/execute.py {task-name} --headroom        # Headroom 래퍼 사용 (설치된 경우만)
python scripts/execute.py {task-name} --docs-mode full  # CLAUDE.md + docs/*.md 전체 주입
python scripts/execute.py {task-name} --no-branch       # 브랜치 분기 없이 실행
python scripts/execute.py {task-name} --push            # 완료 후 원격 push
```

자세한 플래그는 `python scripts/execute.py --help`.

## 경고

- `--unsafe-skip-permissions`는 신뢰된 환경에서만 사용한다. step-output.json에 `unsafe_permissions: true`로 기록된다.
- `high` risk step에서는 Caveman/Headroom output shaping을 사용하지 않는다.
- 보안/스키마/마이그레이션 step은 정확한 error/test name/stack trace/file path를 보존해야 한다.
- 기본 `--docs-mode=digest`. `full`은 토큰 비용이 크므로 release/architecture review에만 사용한다.
