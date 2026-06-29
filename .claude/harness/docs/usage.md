# ccusage 측정 가이드

ccusage는 Claude Code 세션의 토큰/비용 측정 도구다.
**측정 없는 최적화는 성공으로 간주하지 않는다.**

## 기본 명령

```bash
npx ccusage@latest
```

본 하네스는 ccusage를 글로벌 설치하지 않는다. `npx` 1회성 실행만 사용한다.

## 워크플로우

### 1. baseline 측정

optimization을 적용하기 **전에** 측정한다.

```bash
npx ccusage@latest > .claude/harness/logs/ccusage-baseline.txt
```

### 2. 변경 적용

- `--docs-mode digest` 도입
- `--headroom` 적용
- `--caveman-off` 또는 selective Caveman 적용
- HARNESS_DIGEST.md 도입

### 3. 비교 측정

여러 세션 후 다시 측정.

```bash
npx ccusage@latest > .claude/harness/logs/ccusage-after.txt
```

### 4. 비교 항목

| 항목 | 확인 |
|---|---|
| input tokens | 감소했는가 |
| output tokens | 감소했는가 |
| cache reads | 증가했는가 (좋은 신호) |
| cache writes | 비정상 증가하지 않았는가 |
| session cost | 감소했는가 |
| retry count | 감소했는가 |
| step count | 동일한가 |

## 의사결정 규칙

- 측정 전에 RTK / 추가 compression layer를 도입하지 않는다.
- ccusage 결과가 어떤 누수를 보여주는지 먼저 확인하고, 그 누수에 맞는 layer를 선택한다.
  - terminal output 비대 → 명령 사용 패턴 개선, RTK 검토
  - 반복적 long context → HARNESS_DIGEST 도입, Headroom 적용
  - 매 응답이 장황 → Caveman selective 적용
- optimization "성공"은 측정으로만 주장한다.

## package.json 통합 (선택)

`package.json`이 존재하는 프로젝트에서 사용자가 원하면 다음 스크립트를 추가할 수 있다.

```json
{
  "scripts": {
    "claude:usage": "npx ccusage@latest"
  }
}
```

본 하네스는 자동으로 추가하지 않는다.
