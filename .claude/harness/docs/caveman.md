# Caveman 통합 가이드

Caveman은 **output-token 절약 layer**다. 본 하네스에서는 selective 모드로만 사용한다.

## 허용 사용

- routine progress updates
- simple implementation loop summaries
- low-risk final summaries after verification

## 금지 사용

- architecture planning
- debugging root cause analysis
- test failure analysis
- security-sensitive changes
- auth/payment/permission logic
- database migrations
- schema changes
- review findings
- deployment steps
- irreversible operations

## Always-on 금지

Caveman을 모든 세션에서 default로 켜지 않는다.
phase의 `risk_level`이 `high`인 step에서는 자동 비활성한다 (executor가 프롬프트에 명시).

## Superpowers와의 관계

Caveman은 Superpowers discipline(설계 reasoning, 구현 plan, TDD, review findings, blocker 설명, 테스트 evidence)을 덮어쓰지 않는다.
brevity 때문에 verification evidence가 사라지면 그 step은 `completed`로 기록될 수 없다.

## 사용 방법

본 하네스는 Caveman 설치를 자동화하지 않는다.
사용자가 수동으로 enable/disable한다.

executor에 `--caveman-off`를 전달하면 프롬프트에 명시적으로 "Caveman style brevity 사용 금지" 지침이 포함된다 (Caveman 자체가 설치되어 있는지와 무관하게).

```bash
python scripts/execute.py <phase> --caveman-off
```

## 설치

본 하네스는 Caveman 설치 명령을 자동 실행하지 않는다.
공식 문서를 따라 사용자가 직접 설치 및 enable한다.
