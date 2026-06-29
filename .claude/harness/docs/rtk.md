# RTK 정책 (문서 전용)

RTK는 본 하네스에서 **자동 설치하지 않는다**. 본 문서는 사용 정책만 명시한다.

## 허용 사용

- 매우 긴 terminal output 압축이 ccusage로 입증된 경우

## 금지 사용

- 명령 silent rewrite (사용자 명령을 임의로 바꾸는 자동화는 금지)
- 정밀한 소스 코드 reading
- auth / payment / security / migration 파일 처리
- Headroom의 aggressive compression과 동시 사용

## 적용 조건

1. `npx ccusage@latest`로 측정한 baseline에서 terminal output(특히 long log)이 토큰 누수의 주요 원인으로 식별되었을 때만 적용 검토.
2. 적용 시 explicit한 wrapper 명령으로만 사용하고, 사용자 입력을 silent하게 변환하지 않는다.
3. 적용 후 다시 ccusage로 효과 측정.

## 결합 금지

| 조합 | 정책 |
|---|---|
| RTK + Headroom output shaping | 금지 (이중 손실 위험) |
| RTK + Caveman (high risk step) | 금지 |
| RTK + auth/migration step | 금지 |

## 설치

본 하네스는 RTK 설치 명령을 실행하지 않는다.
공식 문서에 따라 사용자가 수동으로 설치하고, 본 정책에 따라 사용한다.
