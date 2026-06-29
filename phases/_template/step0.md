# Step 0: example-step

이 파일은 `phases/{task}/stepN.md`의 템플릿입니다. 새 phase를 만들 때 복제해서 사용하세요.

다음 헤딩은 **반드시 영어 그대로** 유지하세요. executor와 review 스크립트가 이 이름에 의존합니다.
각 헤딩 아래 본문은 한국어로 작성하되, 명령/경로/함수명/식별자/error message/test name 등은 영어 원문을 보존합니다.

## Goal

이 step이 달성해야 할 단일 목적을 한 문장으로 작성하세요.
예: "RTK 도입 없이 베이스라인 ccusage를 기록한다."

## Scope

이 step에서 다루는 모듈/레이어/파일 범위를 명시합니다.
- 다루는 파일/디렉토리 목록
- 영향을 받는 모듈/패키지

## Out of scope

이 step에서 **하지 않는** 것을 명시합니다. 자동 리팩토링 방지를 위해 중요합니다.
- 예: "다른 페이지의 스타일은 손대지 마라"
- 예: "보안 hook 설정은 변경하지 마라"

## Files likely involved

작업 전에 반드시 읽어야 할 파일과 수정 예정 파일을 나열합니다.
- `docs/HARNESS_DIGEST.md`
- `src/example.ts`

## Acceptance Criteria

실행 가능한 검증 기준을 bullet으로 작성합니다.
- `npm run build`가 에러 없이 완료된다.
- `npm test -- --filter=<step name>`가 통과한다.
- (해당 시) 새로 추가된 함수의 시그니처가 명세와 일치한다.

## Verification Command

`--verify-mode=targeted`에서 실제 실행되는 명령. 가능한 한 빠르고 정확한 명령으로.
```bash
npm test -- src/example.test.ts
```

## Rollback Notes

이 step이 실패하거나 결과가 부적절할 때 되돌리는 방법:
- `git revert <commit>` 또는 `git restore --staged --worktree -- <path>`
- (해당 시) DB migration rollback 명령

## Risk Level

`low` | `medium` | `high` 중 하나.
- `high`이면 executor가 Caveman style brevity를 자동 비활성합니다.
- auth/payment/migration/security/permission 변경은 `high`입니다.

## Docs

`--docs-mode=step`에서 가드레일로 주입할 docs 경로 목록. 줄당 하나, 백틱 포함 가능.
- `docs/HARNESS_DIGEST.md`
- `docs/ARCHITECTURE.md`
