# Headroom 통합 가이드

Headroom은 **context/input/tool-output compression layer**다. 본 하네스에서는 optional wrapper로만 사용한다.

## 허용 사용

- 긴 로그 압축
- 노이즈가 많은 tool output 압축
- 반복되는 큰 context 압축
- 정밀 판단이 필요한 경우 original context retrieve

## 금지 사용

- Caveman이 active일 때 Headroom **output shaping** 사용
- `CLAUDE.md` 자동 수정
- 다음 항목을 제거/요약하는 것:
  - stack trace
  - failing test name
  - exact error message
  - migration detail
  - schema change
  - auth/payment/security/permission logic
  - file path

## Wrapper 모드 사용

```bash
python scripts/execute.py <phase> --headroom
```

executor는 `shutil.which("headroom")`로 설치 여부를 확인한다.
- 설치되어 있으면 `headroom wrap <CLAUDE_BIN> ...`로 래핑.
- 설치되어 있지 않으면 stderr에 경고를 출력하고 일반 `claude` 호출로 fallback.

본 하네스는 Headroom을 자동 설치하지 않는다.

## 환경 변수 정책

| 변수 | 권장값 | 의미 |
|---|---|---|
| `HEADROOM_OUTPUT_SHAPER` | `0` | output shaping 비활성. Caveman과 충돌 방지. |
| `HEADROOM_LEARN_TARGET` | `CLAUDE.local.md` | `learn` 결과는 local 파일에만. CLAUDE.md 자동 수정 금지. |
| `HEADROOM_REQUIRE_DIFF_BEFORE_LEARN` | `1` | learn 적용 전 diff 노출 강제. |
| `HEADROOM_PRESERVE_FAILURES` | `1` | 실패/에러/스택트레이스 보존. |
| `HEADROOM_PRESERVE_SECURITY_CONTEXT` | `1` | 보안 컨텍스트 보존. |
| `HEADROOM_PRESERVE_MIGRATIONS` | `1` | 마이그레이션/스키마 변경 보존. |

설정 예 (사용자가 직접):

```bash
export HEADROOM_OUTPUT_SHAPER=0
export HEADROOM_LEARN_TARGET=CLAUDE.local.md
export HEADROOM_REQUIRE_DIFF_BEFORE_LEARN=1
export HEADROOM_PRESERVE_FAILURES=1
export HEADROOM_PRESERVE_SECURITY_CONTEXT=1
export HEADROOM_PRESERVE_MIGRATIONS=1
```

## 설치

본 하네스는 Headroom 설치 명령을 자동 실행하지 않는다.
Headroom 공식 README 또는 검출된 설치 방식을 따라 사용자가 직접 설치한다.
