#!/usr/bin/env python3
"""
HARNESS_DIGEST 생성기.

`CLAUDE.md`와 `docs/*.md`에서 핵심 섹션만 추려 `docs/HARNESS_DIGEST.md`를 작성한다.
원본 파일은 절대 수정하지 않는다.

추출 대상 (헤딩 일치 — 한국어/영어 모두 인식):
  - 프로젝트 개요 / Overview / Project
  - 아키텍처 / Architecture (CRITICAL 규칙 우선)
  - 기술 스택 / Tech Stack
  - 명령어 / Commands / Scripts
  - 테스트 / Testing / Test rules
  - 보안 / Security
  - ADR / Decisions

각 섹션이 30줄을 넘으면 헤딩과 첫 10줄만 발췌 + "...(이하 생략)".

Usage:
    python scripts/generate_harness_digest.py
"""

import re
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
CLAUDE_MD = ROOT / "CLAUDE.md"
OUT = DOCS_DIR / "HARNESS_DIGEST.md"

TZ = timezone(timedelta(hours=9))

SECTION_PATTERNS = [
    # 프로젝트 개요는 별도 로직 (H1 제목 + 첫 단락만)
    ("기술 스택", [r"^##\s+(기술\s*스택|Tech\s*Stack|Stack)\b"]),
    ("아키텍처 규칙", [r"^##\s+(아키텍처|Architecture)\b"]),
    ("개발 프로세스", [r"^##\s+(개발\s*프로세스|Development\s*Process|Process)\b"]),
    ("명령어", [r"^##\s+(명령어|Commands|Scripts)\b"]),
    ("테스트 규칙", [r"^##\s+(테스트|Testing|Test\s*rules?)\b"]),
    ("보안", [r"^##\s+(보안|Security)\b"]),
    ("ADR 요약", [r"^##\s+(ADR|Decisions|기술\s*결정)\b"]),
]

H1_TITLE_PATTERN = re.compile(r"^#\s+(Project|프로젝트|.+)\b")


def extract_h1_overview(text: str) -> str:
    """H1 제목과 그 다음 첫 H2 직전까지의 짧은 개요만 추출."""
    if not text:
        return ""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if H1_TITLE_PATTERN.match(line):
            body = [line]
            j = i + 1
            while j < len(lines) and not re.match(r"^##?\s", lines[j]):
                body.append(lines[j])
                j += 1
            return "\n".join(body).rstrip()
    return ""

MAX_LINES_PER_SECTION = 30
HEAD_LINES_WHEN_TRUNCATED = 10


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_section(text: str, header_patterns: list) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    matched = []
    for i, line in enumerate(lines):
        for pat in header_patterns:
            if re.match(pat, line):
                # 다음 동일 레벨 헤딩까지 수집
                level_m = re.match(r"^(#+)\s", line)
                if not level_m:
                    continue
                level = len(level_m.group(1))
                body = [line]
                j = i + 1
                while j < len(lines):
                    nxt = re.match(r"^(#+)\s", lines[j])
                    if nxt and len(nxt.group(1)) <= level:
                        break
                    body.append(lines[j])
                    j += 1
                matched.append("\n".join(body).rstrip())
                break
    if not matched:
        return ""
    out = "\n\n".join(matched)
    out_lines = out.splitlines()
    if len(out_lines) > MAX_LINES_PER_SECTION:
        head = "\n".join(out_lines[:HEAD_LINES_WHEN_TRUNCATED])
        out = head + "\n\n...(이하 생략 — 원본 파일 참조)"
    return out


def collect() -> str:
    chunks = []
    sources = [("CLAUDE.md", read(CLAUDE_MD))]
    if DOCS_DIR.is_dir():
        for p in sorted(DOCS_DIR.glob("*.md")):
            if p.name == "HARNESS_DIGEST.md":
                continue
            sources.append((p.name, read(p)))

    # 프로젝트 개요는 H1 제목 + 첫 단락만
    overview_parts = []
    for src_name, src_text in sources:
        overview = extract_h1_overview(src_text)
        if overview:
            overview_parts.append(f"<!-- from {src_name} -->\n{overview}")
    if overview_parts:
        chunks.append("## 프로젝트 개요\n\n" + "\n\n".join(overview_parts))

    for label, patterns in SECTION_PATTERNS:
        section_chunks = []
        for src_name, src_text in sources:
            extracted = extract_section(src_text, patterns)
            if extracted:
                section_chunks.append(f"<!-- from {src_name} -->\n{extracted}")
        if section_chunks:
            chunks.append(f"## {label}\n\n" + "\n\n".join(section_chunks))
    return "\n\n".join(chunks)


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    body = collect()
    ts = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
    header = (
        "# HARNESS DIGEST\n\n"
        "이 파일은 `scripts/generate_harness_digest.py`가 자동 생성한다. "
        "직접 편집하지 말고 원본(`CLAUDE.md`, `docs/*.md`)을 수정한 뒤 다시 실행하라.\n\n"
        f"- 생성 시각: {ts}\n"
        "- 본문은 한국어, 명령/경로/식별자는 영어 원문 보존.\n\n"
        "---\n\n"
    )
    if not body.strip():
        body = (
            "(원본 docs에서 추출 가능한 섹션이 없습니다. "
            "`CLAUDE.md`와 `docs/*.md`에 다음 헤딩을 추가하세요: "
            "`## Tech Stack`, `## Architecture Rules`, `## Commands`, `## Testing`, `## Security`, `## ADR`.)"
        )
    OUT.write_text(header + body + "\n", encoding="utf-8")
    print(f"[generate_harness_digest] wrote {OUT} ({len(body)} bytes)")


if __name__ == "__main__":
    sys.exit(main() or 0)
