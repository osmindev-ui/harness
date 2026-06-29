# HARNESS DIGEST

이 파일은 `scripts/generate_harness_digest.py`가 자동 생성한다. 직접 편집하지 말고 원본(`CLAUDE.md`, `docs/*.md`)을 수정한 뒤 다시 실행하라.

- 생성 시각: 2026-06-29T16:56:17+0900
- 본문은 한국어, 명령/경로/식별자는 영어 원문 보존.

---

## 프로젝트 개요

<!-- from CLAUDE.md -->
# Project: {프로젝트명}

## 기술 스택

<!-- from CLAUDE.md -->
## Tech Stack
- {Framework (e.g. Next.js 15)}
- {Language (e.g. TypeScript strict mode)}
- {Styling (e.g. Tailwind CSS)}

## 아키텍처 규칙

<!-- from CLAUDE.md -->
## Architecture Rules
- CRITICAL: {절대 지켜야 할 규칙 1 (e.g. 모든 API 로직은 `app/api/` route handler에서만 처리)}
- CRITICAL: {절대 지켜야 할 규칙 2 (e.g. 클라이언트 컴포넌트에서 직접 외부 API를 호출하지 말 것)}
- {일반 규칙 (e.g. 컴포넌트는 `components/`, 타입은 `types/` 분리)}

## 개발 프로세스

<!-- from CLAUDE.md -->
## Development Process
- CRITICAL: 새 기능 구현 시 테스트를 먼저 작성하고 통과하는 구현을 작성한다 (TDD).
- 커밋 메시지는 Conventional Commits 형식 (`feat:`, `fix:`, `docs:`, `refactor:`).

## 명령어

<!-- from CLAUDE.md -->
## Commands
```
npm run dev      # 개발 서버
npm run build    # 프로덕션 빌드
npm run lint     # ESLint
npm run test     # 테스트
```
