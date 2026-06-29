# Superpowers 통합 가이드

Superpowers는 본 하네스의 **주요 개발 방법론 레이어**다.
jha0313 phase executor는 **실행 레이어**다.

| 레이어 | 역할 |
|---|---|
| Project-specific instructions | 도메인 규칙 (CLAUDE.md) |
| jha0313 phase/step harness | step 분해/실행/검증 (이 저장소) |
| Superpowers | design/TDD/review/verification 방법론 |
| Safety hooks | PreToolUse/PostToolUse |
| Headroom | context compression (optional) |
| Caveman | output brevity (optional, selective) |

## 보존되어야 할 Superpowers discipline

토큰 절약을 이유로 다음을 제거하지 않는다.

- design reasoning
- implementation plan
- TDD / verification strategy
- review findings
- blocker explanation
- test evidence

## 우선순위

Superpowers는 Caveman/Headroom보다 priority가 높다.
Caveman/Headroom이 Superpowers의 reasoning/evidence를 압축으로 제거하려 한다면, 해당 step은 `high` risk로 처리하고 Caveman/Headroom output shaping을 비활성한다.

## 설치 (참고)

본 하네스는 Superpowers를 자동 설치하지 않는다.
Claude Code plugin marketplace를 사용한다면 아래 명령은 **사용자가 직접 입력**해야 한다.

```
/plugin install superpowers@claude-plugins-official
```

또는

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

승인 없이 자동 설치하지 않는다.
