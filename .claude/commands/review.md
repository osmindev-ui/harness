# /review

현재 변경사항을 jha0313 phase/step 산출물 + Superpowers + 안전 정책 관점으로 리뷰한다.

---

## 0. 입력 수집

다음을 수집한다.

- `git diff --stat` (변경 규모)
- `git diff` 또는 PR diff (변경 본문)
- 활성 phase의 `phases/{phase}/index.json`과 `step{N}.md`, `step{N}-summary.md`
- `docs/HARNESS_DIGEST.md` 또는 관련 `docs/*.md`
- 보안/마이그레이션 관련 파일 직접 확인

## Review 체크리스트

각 항목에 ✅ / ❌ / N/A 표시.

### A. 변경 정합성

- 변경된 파일 목록과 phase step 설계의 일치
- 아키텍처 규칙 준수 (CLAUDE.md CRITICAL)
- 프로젝트 instruction 준수
- 명세에 없는 추가 기능/리팩토링 여부

### B. Superpowers compliance

- 설계 reasoning이 어디엔가 기록되어 있는가
- 구현 전 plan이 있는가
- TDD 또는 verification strategy가 명시되었는가
- review findings가 있는가
- blocker 설명이 충분한가
- 테스트 evidence가 있는가

### C. 검증

- `verification_command`가 실제 실행되었는가 (`step{N}-summary.md` 또는 `step{N}-output.json`에서 evidence 확인)
- 테스트가 실제로 통과했는가 (출력 발췌 영어 보존)
- full verification이 필요한가 (release/architecture/schema 변경 시 필수)

### D. 보안/위험

- secret 노출 (commit 내용 grep)
- migration / schema 변경의 rollback 경로
- auth / payment / permission 로직 변경 시 reviewer 추가 필요

### E. 토큰/컨텍스트 낭비

- Caveman을 비활성화해야 했던 high-risk step에서 brevity가 강요되지 않았는가
- Headroom이 stack trace/test name/migration detail을 숨기지 않았는가
- 다음 항목이 누락되지 않았는지: failing test name, exact error message, exact file path

## Output format

다음 한국어 헤딩으로 출력. 본문은 한국어, 기술 evidence는 영어 보존.

```
## Summary
한두 문장으로 변경 요지.

## Critical issues
- ...

## Non-critical issues
- ...

## Verification run
- 실행한 명령
- 결과 (영어 발췌)

## Missing verification
- 미실행 검증

## Recommended next action
- 다음 단계
```

## 종료 조건

- Critical issue가 0이고 verification이 통과했을 때만 ✅ ready
- 그 외에는 ❌ blocked + 다음 액션 명시
