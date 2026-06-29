# Project: {프로젝트명}

## Tech Stack
- {Framework (e.g. Next.js 15)}
- {Language (e.g. TypeScript strict mode)}
- {Styling (e.g. Tailwind CSS)}

## Architecture Rules
- CRITICAL: {절대 지켜야 할 규칙 1 (e.g. 모든 API 로직은 `app/api/` route handler에서만 처리)}
- CRITICAL: {절대 지켜야 할 규칙 2 (e.g. 클라이언트 컴포넌트에서 직접 외부 API를 호출하지 말 것)}
- {일반 규칙 (e.g. 컴포넌트는 `components/`, 타입은 `types/` 분리)}

## Development Process
- CRITICAL: 새 기능 구현 시 테스트를 먼저 작성하고 통과하는 구현을 작성한다 (TDD).
- 커밋 메시지는 Conventional Commits 형식 (`feat:`, `fix:`, `docs:`, `refactor:`).

## Commands
```
npm run dev      # 개발 서버
npm run build    # 프로덕션 빌드
npm run lint     # ESLint
npm run test     # 테스트
```

## Harness
이 저장소는 jha0313/harness_framework 기반 phase/step executor를 사용한다.
운영 정책은 `CLAUDE.local.md`의 `# Harness Policy` 섹션을 참조한다.
