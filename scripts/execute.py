#!/usr/bin/env python3
"""
Harness Step Executor — jha0313/harness_framework 기반.

원본 패턴(phase/step 순차 실행, retry, summary 컨텍스트 누적, branch-per-phase,
2단계 commit, CLAUDE.md+docs 가드레일 주입)을 보존하면서 다음을 확장한다.

확장:
- --dangerously-skip-permissions 기본 OFF (--unsafe-skip-permissions로 opt-in)
- --no-commit / --no-branch / --dry-run
- --headroom (shutil.which 검출 시 wrapper 사용)
- --caveman-off (프롬프트에 명시)
- --max-retries N (기본 3)
- --docs-mode full|digest|step (기본 digest)
- --verify-mode none|targeted|full (기본 targeted, 프롬프트에 명시)
- --timeout-seconds N (기본 1800)
- --push (기본 비활성)
- CLAUDE_BIN env로 claude 경로 override
- stepN-summary.md 자동 작성 (한국어, 영어 evidence 보존)

Usage:
    python scripts/execute.py <phase-dir> [flags]
    python scripts/execute.py --help
"""

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import types
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent


@contextlib.contextmanager
def progress_indicator(label: str):
    """터미널 진행 표시기."""
    frames = "|/-\\"
    stop = threading.Event()
    t0 = time.monotonic()

    def _animate():
        idx = 0
        while not stop.wait(0.15):
            sec = int(time.monotonic() - t0)
            try:
                sys.stderr.write(f"\r{frames[idx % len(frames)]} {label} [{sec}s]")
                sys.stderr.flush()
            except Exception:
                pass
            idx += 1
        try:
            sys.stderr.write("\r" + " " * (len(label) + 20) + "\r")
            sys.stderr.flush()
        except Exception:
            pass

    th = threading.Thread(target=_animate, daemon=True)
    th.start()
    info = types.SimpleNamespace(elapsed=0.0)
    try:
        yield info
    finally:
        stop.set()
        th.join()
        info.elapsed = time.monotonic() - t0


HIGH_RISK_GUIDANCE = (
    "## 안전 정책 (Claude 세션 준수 필수)\n\n"
    "- 실패한 test name, stack trace, error message, file path, "
    "migration/schema/security/auth/payment 세부는 임의로 요약하거나 한국어로 번역하지 마라. "
    "원문(영어)을 보존하라.\n"
    "- 사용자가 명시한 식별자(함수명, 클래스명, 환경변수, 명령, 경로, "
    "DB 테이블/컬럼명, enum 값, hook 이름)는 변경하지 마라.\n"
    "- Acceptance Criteria가 검증되지 않은 step은 `completed`로 기록하지 마라.\n"
    "- 의심스러운 자동 정리/리팩토링은 하지 마라. 이 step의 Scope에만 집중하라.\n"
)


class StepExecutor:
    """Phase 디렉토리의 step들을 순차 실행하는 하네스."""

    FEAT_MSG = "feat({phase}): step {num} — {name}"
    CHORE_MSG = "chore({phase}): step {num} output"
    TZ = timezone(timedelta(hours=9))

    def __init__(
        self,
        phase_dir_name: str,
        *,
        auto_push: bool = False,
        unsafe_skip: bool = False,
        no_commit: bool = False,
        no_branch: bool = False,
        dry_run: bool = False,
        use_headroom: bool = False,
        caveman_off: bool = False,
        max_retries: int = 3,
        docs_mode: str = "digest",
        verify_mode: str = "targeted",
        timeout_seconds: int = 1800,
    ):
        self._root = str(ROOT)
        self._phases_dir = ROOT / "phases"
        self._phase_dir = self._phases_dir / phase_dir_name
        self._phase_dir_name = phase_dir_name
        self._top_index_file = self._phases_dir / "index.json"

        self._auto_push = auto_push
        self._unsafe_skip = unsafe_skip
        self._no_commit = no_commit
        self._no_branch = no_branch
        self._dry_run = dry_run
        self._use_headroom = use_headroom
        self._caveman_off = caveman_off
        self._max_retries = max(1, int(max_retries))
        self._docs_mode = docs_mode
        self._verify_mode = verify_mode
        self._timeout = max(60, int(timeout_seconds))

        self._claude_bin = os.environ.get("CLAUDE_BIN", "claude")
        self._headroom_available = bool(shutil.which("headroom"))
        if self._use_headroom and not self._headroom_available:
            sys.stderr.write(
                "[harness] WARN: --headroom requested but `headroom` not on PATH. "
                "Falling back to plain claude.\n"
            )

        if not self._phase_dir.is_dir():
            print(f"ERROR: {self._phase_dir} not found")
            sys.exit(1)

        self._index_file = self._phase_dir / "index.json"
        if not self._index_file.exists():
            print(f"ERROR: {self._index_file} not found")
            sys.exit(1)

        idx = self._read_json(self._index_file)
        self._project = idx.get("project", "project")
        self._phase_name = idx.get("phase", phase_dir_name)
        self._total = len(idx["steps"])

    # ---- entry ----

    def run(self):
        self._print_header()
        self._check_blockers()
        if self._dry_run:
            self._dry_run_report()
            return
        if not self._no_branch:
            self._checkout_branch()
        guardrails = self._load_guardrails()
        self._ensure_created_at()
        self._execute_all_steps(guardrails)
        self._finalize()

    # ---- timestamps ----

    def _stamp(self) -> str:
        return datetime.now(self.TZ).strftime("%Y-%m-%dT%H:%M:%S%z")

    # ---- JSON I/O ----

    @staticmethod
    def _read_json(p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(p: Path, data: dict):
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- git ----

    def _run_git(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(["git"] + list(args), cwd=self._root, capture_output=True, text=True)

    def _checkout_branch(self):
        branch = f"feat-{self._phase_name}"
        r = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if r.returncode != 0:
            print("  ERROR: git을 사용할 수 없거나 git repo가 아닙니다.")
            print(f"  {r.stderr.strip()}")
            sys.exit(1)
        if r.stdout.strip() == branch:
            return
        r = self._run_git("rev-parse", "--verify", branch)
        r = self._run_git("checkout", branch) if r.returncode == 0 else self._run_git("checkout", "-b", branch)
        if r.returncode != 0:
            print(f"  ERROR: 브랜치 '{branch}' checkout 실패.")
            print(f"  {r.stderr.strip()}")
            print("  Hint: 변경사항을 stash 또는 commit한 후 다시 시도하세요.")
            sys.exit(1)
        print(f"  Branch: {branch}")

    def _commit_step(self, step_num: int, step_name: str):
        if self._no_commit:
            return
        output_rel = f"phases/{self._phase_dir_name}/step{step_num}-output.json"
        index_rel = f"phases/{self._phase_dir_name}/index.json"
        self._run_git("add", "-A")
        self._run_git("reset", "HEAD", "--", output_rel)
        self._run_git("reset", "HEAD", "--", index_rel)
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.FEAT_MSG.format(phase=self._phase_name, num=step_num, name=step_name)
            r = self._run_git("commit", "-m", msg)
            if r.returncode == 0:
                print(f"  Commit: {msg}")
            else:
                print(f"  WARN: 코드 commit 실패: {r.stderr.strip()}")
        self._run_git("add", "-A")
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.CHORE_MSG.format(phase=self._phase_name, num=step_num)
            r = self._run_git("commit", "-m", msg)
            if r.returncode != 0:
                print(f"  WARN: housekeeping commit 실패: {r.stderr.strip()}")

    # ---- top-level index ----

    def _update_top_index(self, status: str):
        if not self._top_index_file.exists():
            return
        top = self._read_json(self._top_index_file)
        ts = self._stamp()
        for phase in top.get("phases", []):
            if phase.get("dir") == self._phase_dir_name:
                phase["status"] = status
                ts_key = {"completed": "completed_at", "error": "failed_at", "blocked": "blocked_at"}.get(status)
                if ts_key:
                    phase[ts_key] = ts
                break
        self._write_json(self._top_index_file, top)

    # ---- guardrails ----

    @staticmethod
    def _read_text(p: Path) -> str:
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _parse_step_docs(self, step_file: Path) -> list:
        """step{N}.md의 `## Docs` 섹션에서 경로 목록을 추출."""
        text = self._read_text(step_file)
        if not text:
            return []
        m = re.search(r"^##\s+Docs\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.MULTILINE)
        if not m:
            return []
        block = m.group(1)
        paths = []
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            m2 = re.match(r"^[-*]\s+`?([^`\s]+)`?", line)
            if m2:
                paths.append(m2.group(1))
        return paths

    def _load_guardrails(self, step_file: Optional[Path] = None) -> str:
        sections = []
        claude_md = ROOT / "CLAUDE.md"
        if claude_md.exists():
            sections.append(f"## 프로젝트 규칙 (CLAUDE.md)\n\n{self._read_text(claude_md)}")
        claude_local = ROOT / "CLAUDE.local.md"
        if claude_local.exists():
            sections.append(f"## 로컬 정책 (CLAUDE.local.md)\n\n{self._read_text(claude_local)}")

        docs_dir = ROOT / "docs"
        if self._docs_mode == "full":
            if docs_dir.is_dir():
                for doc in sorted(docs_dir.glob("*.md")):
                    sections.append(f"## {doc.stem}\n\n{self._read_text(doc)}")
        elif self._docs_mode == "digest":
            digest = docs_dir / "HARNESS_DIGEST.md"
            if digest.exists():
                sections.append(f"## HARNESS_DIGEST\n\n{self._read_text(digest)}")
            else:
                sections.append(
                    "## HARNESS_DIGEST\n\n"
                    "(`docs/HARNESS_DIGEST.md` 미존재. "
                    "`python scripts/generate_harness_digest.py`로 생성하라.)"
                )
        elif self._docs_mode == "step":
            if step_file is not None:
                for rel in self._parse_step_docs(step_file):
                    p = (ROOT / rel).resolve()
                    if p.exists() and p.is_file():
                        sections.append(f"## {p.name}\n\n{self._read_text(p)}")
        return "\n\n---\n\n".join(sections) if sections else ""

    @staticmethod
    def _build_step_context(index: dict) -> str:
        lines = [
            f"- Step {s['step']} ({s['name']}): {s['summary']}"
            for s in index["steps"]
            if s["status"] == "completed" and s.get("summary")
        ]
        if not lines:
            return ""
        return "## 이전 Step 산출물\n\n" + "\n".join(lines) + "\n\n"

    def _build_preamble(
        self,
        guardrails: str,
        step_context: str,
        risk_level: str,
        prev_error: Optional[str] = None,
    ) -> str:
        commit_example = self.FEAT_MSG.format(phase=self._phase_name, num="N", name="<step-name>")
        retry_section = ""
        if prev_error:
            retry_section = (
                "\n## 이전 시도 실패 — 아래 에러를 반드시 참고하여 수정하라\n\n"
                f"{prev_error}\n\n---\n\n"
            )

        verify_directive = {
            "none": "검증은 건너뛴다.",
            "targeted": "`## Verification Command` 섹션의 명령만 실행한다. 프로젝트 전체 lint/build/test는 실행하지 마라.",
            "full": "프로젝트의 전체 lint/build/test를 실행하여 회귀를 점검한다.",
        }.get(self._verify_mode, "targeted verification")

        caveman_directive = ""
        if self._caveman_off or risk_level == "high":
            caveman_directive = (
                "- 이 step은 Caveman style brevity를 사용하지 않는다. "
                "design reasoning, evidence, error 원문을 충분히 남겨라.\n"
            )

        commit_directive = (
            "" if self._no_commit
            else "6. 모든 변경사항을 commit하라:\n"
                 f"   {commit_example}\n"
        )

        return (
            f"당신은 {self._project} 프로젝트의 개발자입니다. 아래 step을 수행하세요.\n\n"
            f"{guardrails}\n\n---\n\n"
            f"{step_context}{retry_section}"
            f"{HIGH_RISK_GUIDANCE}\n"
            f"## 작업 규칙\n\n"
            f"1. 이전 step에서 작성된 코드를 확인하고 일관성을 유지하라.\n"
            f"2. 이 step에 명시된 작업만 수행하라. 추가 기능이나 파일을 만들지 마라.\n"
            f"3. 기존 테스트를 깨뜨리지 마라.\n"
            f"4. Verification: {verify_directive}\n"
            f"5. `/phases/{self._phase_dir_name}/index.json`의 해당 step status를 업데이트하라:\n"
            f"   - AC 통과 → `completed` + `summary` 필드에 한 줄 요약 (한국어 가능, 식별자는 영어)\n"
            f"   - {self._max_retries}회 시도 후에도 실패 → `error` + `error_message` (영어 원문 보존)\n"
            f"   - 사용자 개입 필요 → `blocked` + `blocked_reason` 후 즉시 중단\n"
            f"{commit_directive}"
            f"{caveman_directive}"
            "\n---\n\n"
        )

    # ---- Claude 호출 ----

    def _build_claude_command(self, prompt: str) -> list:
        cmd = [self._claude_bin, "-p", "--output-format", "json"]
        if self._unsafe_skip:
            cmd.append("--dangerously-skip-permissions")
        cmd.append(prompt)
        if self._use_headroom and self._headroom_available:
            return ["headroom", "wrap"] + cmd
        return cmd

    def _invoke_claude(self, step: dict, preamble: str) -> dict:
        step_num, step_name = step["step"], step["name"]
        step_file = self._phase_dir / f"step{step_num}.md"

        if not step_file.exists():
            print(f"  ERROR: {step_file} not found")
            sys.exit(1)

        prompt = preamble + self._read_text(step_file)
        cmd = self._build_claude_command(prompt)

        if self._unsafe_skip:
            sys.stderr.write(
                "\n" + "!" * 70 + "\n"
                "! WARNING: --dangerously-skip-permissions ACTIVE\n"
                "! step-output.json에 unsafe_permissions=true로 기록됩니다.\n"
                + "!" * 70 + "\n\n"
            )

        result = subprocess.run(
            cmd, cwd=self._root, capture_output=True, text=True, timeout=self._timeout
        )

        if result.returncode != 0:
            print(f"\n  WARN: Claude 비정상 종료 (code {result.returncode})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")

        output = {
            "step": step_num,
            "name": step_name,
            "exitCode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "meta": {
                "unsafe_permissions": self._unsafe_skip,
                "headroom_used": self._use_headroom and self._headroom_available,
                "caveman_off": self._caveman_off,
                "docs_mode": self._docs_mode,
                "verify_mode": self._verify_mode,
                "max_retries": self._max_retries,
                "timeout_seconds": self._timeout,
                "claude_bin": self._claude_bin,
            },
        }
        out_path = self._phase_dir / f"step{step_num}-output.json"
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        return output

    def _write_step_summary(self, step: dict, status: str, elapsed: int, attempts: int):
        step_num = step["step"]
        step_name = step["name"]
        out_path = self._phase_dir / f"step{step_num}-output.json"
        index = self._read_json(self._index_file)
        idx_step = next((s for s in index["steps"] if s["step"] == step_num), {})

        stdout_tail = ""
        stderr_tail = ""
        if out_path.exists():
            try:
                data = json.loads(out_path.read_text(encoding="utf-8"))
                stdout = data.get("stdout", "") or ""
                stderr = data.get("stderr", "") or ""
                stdout_tail = stdout[-2000:] if stdout else ""
                stderr_tail = stderr[-1000:] if stderr else ""
            except Exception:
                pass

        summary_text = idx_step.get("summary", "")
        error_text = idx_step.get("error_message", "")
        blocked_text = idx_step.get("blocked_reason", "")

        md = []
        md.append(f"# Step {step_num} 요약 — {step_name}\n")
        md.append("## 결과\n")
        md.append(f"- status: `{status}`\n")
        md.append(f"- elapsed: {elapsed}s\n")
        md.append(f"- attempts: {attempts}\n")
        md.append(f"- docs_mode: `{self._docs_mode}` / verify_mode: `{self._verify_mode}`\n")
        if self._unsafe_skip:
            md.append("- unsafe_permissions: `true`\n")
        md.append("")
        md.append("## 산출물\n")
        md.append(f"{summary_text if summary_text else '(요약 없음)'}\n")
        if error_text:
            md.append("\n## Error message (영어 원문 보존)\n")
            md.append("```\n" + error_text + "\n```\n")
        if blocked_text:
            md.append("\n## Blocked reason\n")
            md.append(blocked_text + "\n")
        if stdout_tail.strip():
            md.append("\n## stdout 발췌 (영어 원문 보존)\n")
            md.append("```\n" + stdout_tail + "\n```\n")
        if stderr_tail.strip():
            md.append("\n## stderr 발췌 (영어 원문 보존)\n")
            md.append("```\n" + stderr_tail + "\n```\n")

        summary_path = self._phase_dir / f"step{step_num}-summary.md"
        summary_path.write_text("\n".join(md), encoding="utf-8")

    # ---- 헤더 & 검증 ----

    def _print_header(self):
        print(f"\n{'='*60}")
        print("  Harness Step Executor (jha0313 base + safety/token-aware)")
        print(f"  Phase: {self._phase_name} | Steps: {self._total}")
        print(f"  docs-mode: {self._docs_mode} | verify-mode: {self._verify_mode}")
        print(f"  max-retries: {self._max_retries} | timeout: {self._timeout}s")
        if self._dry_run:
            print("  Dry-run: ENABLED (no claude calls, no commits, no branch)")
        if self._unsafe_skip:
            print("  Unsafe-permissions: ENABLED (--dangerously-skip-permissions)")
        if self._use_headroom:
            print(f"  Headroom: requested (available={self._headroom_available})")
        if self._caveman_off:
            print("  Caveman: explicitly off in prompts")
        if self._no_branch:
            print("  No branch")
        if self._no_commit:
            print("  No commit")
        if self._auto_push:
            print("  Auto-push: enabled")
        print("=" * 60)

    def _check_blockers(self):
        index = self._read_json(self._index_file)
        for s in reversed(index["steps"]):
            if s["status"] == "error":
                print(f"\n  Step {s['step']} ({s['name']}) failed.")
                print(f"  Error: {s.get('error_message', 'unknown')}")
                print("  Fix and reset status to 'pending' to retry.")
                sys.exit(1)
            if s["status"] == "blocked":
                print(f"\n  Step {s['step']} ({s['name']}) blocked.")
                print(f"  Reason: {s.get('blocked_reason', 'unknown')}")
                print("  Resolve and reset status to 'pending' to retry.")
                sys.exit(2)
            if s["status"] != "pending":
                break

    def _ensure_created_at(self):
        index = self._read_json(self._index_file)
        if "created_at" not in index:
            index["created_at"] = self._stamp()
            self._write_json(self._index_file, index)

    def _dry_run_report(self):
        index = self._read_json(self._index_file)
        print("\n[dry-run] step plan:")
        for s in index["steps"]:
            step_file = self._phase_dir / f"step{s['step']}.md"
            exists = "OK" if step_file.exists() else "MISSING"
            risk = s.get("risk_level", "low")
            vcmd = s.get("verification_command", "(none)")
            print(
                f"  - step {s['step']:>2} [{s['status']:<9}] risk={risk:<6} "
                f"name={s['name']} file={exists} verify={vcmd}"
            )
        print("\n[dry-run] guardrails preview (docs-mode={}):".format(self._docs_mode))
        first_step_file = self._phase_dir / f"step{index['steps'][0]['step']}.md" if index["steps"] else None
        gr = self._load_guardrails(first_step_file)
        sample = gr[:800] + ("..." if len(gr) > 800 else "")
        print(sample if sample else "  (empty)")
        print("\n[dry-run] no Claude call, no commit, no branch change.")

    # ---- 실행 루프 ----

    def _execute_single_step(self, step: dict, guardrails_default: str) -> bool:
        step_num, step_name = step["step"], step["name"]
        risk_level = step.get("risk_level", "low")
        done = sum(1 for s in self._read_json(self._index_file)["steps"] if s["status"] == "completed")
        prev_error = None

        step_file = self._phase_dir / f"step{step_num}.md"
        guardrails = self._load_guardrails(step_file) if self._docs_mode == "step" else guardrails_default

        for attempt in range(1, self._max_retries + 1):
            index = self._read_json(self._index_file)
            step_context = self._build_step_context(index)
            preamble = self._build_preamble(guardrails, step_context, risk_level, prev_error)

            tag = f"Step {step_num}/{self._total - 1} ({done} done): {step_name}"
            if attempt > 1:
                tag += f" [retry {attempt}/{self._max_retries}]"

            with progress_indicator(tag) as pi:
                self._invoke_claude(step, preamble)
                elapsed = int(pi.elapsed)

            index = self._read_json(self._index_file)
            status = next((s.get("status", "pending") for s in index["steps"] if s["step"] == step_num), "pending")
            ts = self._stamp()

            if status == "completed":
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["completed_at"] = ts
                self._write_json(self._index_file, index)
                self._write_step_summary(step, status, elapsed, attempt)
                self._commit_step(step_num, step_name)
                print(f"  OK Step {step_num}: {step_name} [{elapsed}s]")
                return True

            if status == "blocked":
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["blocked_at"] = ts
                self._write_json(self._index_file, index)
                reason = next((s.get("blocked_reason", "") for s in index["steps"] if s["step"] == step_num), "")
                print(f"  BLOCKED Step {step_num}: {step_name} [{elapsed}s]")
                print(f"    Reason: {reason}")
                self._write_step_summary(step, status, elapsed, attempt)
                self._update_top_index("blocked")
                sys.exit(2)

            err_msg = next(
                (s.get("error_message", "Step did not update status") for s in index["steps"] if s["step"] == step_num),
                "Step did not update status",
            )

            if attempt < self._max_retries:
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["status"] = "pending"
                        s.pop("error_message", None)
                self._write_json(self._index_file, index)
                prev_error = err_msg
                print(f"  RETRY Step {step_num}: {attempt}/{self._max_retries} — {err_msg}")
            else:
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["status"] = "error"
                        s["error_message"] = f"[{self._max_retries}회 시도 후 실패] {err_msg}"
                        s["failed_at"] = ts
                self._write_json(self._index_file, index)
                self._write_step_summary(step, "error", elapsed, attempt)
                self._commit_step(step_num, step_name)
                print(f"  FAIL Step {step_num}: {step_name} after {self._max_retries} attempts [{elapsed}s]")
                print(f"    Error: {err_msg}")
                self._update_top_index("error")
                sys.exit(1)

        return False  # unreachable

    def _execute_all_steps(self, guardrails: str):
        while True:
            index = self._read_json(self._index_file)
            pending = next((s for s in index["steps"] if s["status"] == "pending"), None)
            if pending is None:
                print("\n  All steps completed!")
                return

            step_num = pending["step"]
            for s in index["steps"]:
                if s["step"] == step_num and "started_at" not in s:
                    s["started_at"] = self._stamp()
                    self._write_json(self._index_file, index)
                    break

            self._execute_single_step(pending, guardrails)

    def _finalize(self):
        index = self._read_json(self._index_file)
        index["completed_at"] = self._stamp()
        self._write_json(self._index_file, index)
        self._update_top_index("completed")

        if not self._no_commit:
            self._run_git("add", "-A")
            if self._run_git("diff", "--cached", "--quiet").returncode != 0:
                msg = f"chore({self._phase_name}): mark phase completed"
                r = self._run_git("commit", "-m", msg)
                if r.returncode == 0:
                    print(f"  OK {msg}")

        if self._auto_push:
            branch = f"feat-{self._phase_name}"
            r = self._run_git("push", "-u", "origin", branch)
            if r.returncode != 0:
                print(f"\n  ERROR: git push 실패: {r.stderr.strip()}")
                sys.exit(1)
            print(f"  OK Pushed to origin/{branch}")

        completed = sum(1 for s in index["steps"] if s["status"] == "completed")
        blocked = sum(1 for s in index["steps"] if s["status"] == "blocked")
        errored = sum(1 for s in index["steps"] if s["status"] == "error")

        print(f"\n{'='*60}")
        print(f"  Phase '{self._phase_name}' 완료 리포트")
        print(f"{'='*60}")
        print(f"  completed: {completed} / blocked: {blocked} / error: {errored}")
        print(f"  verify-mode: {self._verify_mode}")
        print(f"  docs-mode: {self._docs_mode}")
        print(f"  headroom 사용: {self._use_headroom and self._headroom_available}")
        print(f"  caveman 비활성 지침: {self._caveman_off}")
        print(f"  unsafe-permissions 사용: {self._unsafe_skip}")
        print()
        print("  다음 명령으로 토큰 사용량 측정:")
        print("    npx ccusage@latest")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Harness Step Executor (jha0313 base + safety/token-aware)")
    parser.add_argument("phase_dir", help="phase directory name (예: 0-mvp)")
    parser.add_argument("--push", action="store_true", help="phase 완료 후 원격 push")
    parser.add_argument("--unsafe-skip-permissions", action="store_true",
                        help="--dangerously-skip-permissions를 claude에 전달 (신뢰 환경 전용)")
    parser.add_argument("--no-commit", action="store_true", help="git commit 건너뛰기")
    parser.add_argument("--no-branch", action="store_true", help="branch checkout 건너뛰기")
    parser.add_argument("--dry-run", action="store_true", help="claude 호출 없이 step plan만 출력")
    parser.add_argument("--headroom", action="store_true", help="headroom 검출 시 wrapper로 호출")
    parser.add_argument("--caveman-off", action="store_true", help="프롬프트에 Caveman brevity 사용 금지 명시")
    parser.add_argument("--max-retries", type=int, default=3, help="step당 최대 재시도 (기본 3)")
    parser.add_argument("--docs-mode", choices=["full", "digest", "step"], default="digest",
                        help="가드레일 docs 주입 모드 (기본 digest)")
    parser.add_argument("--verify-mode", choices=["none", "targeted", "full"], default="targeted",
                        help="step 종료 시 검증 모드 (기본 targeted; full lint/build/test 자동 실행 안 함)")
    parser.add_argument("--timeout-seconds", type=int, default=1800,
                        help="claude subprocess timeout (기본 1800)")
    args = parser.parse_args()

    StepExecutor(
        args.phase_dir,
        auto_push=args.push,
        unsafe_skip=args.unsafe_skip_permissions,
        no_commit=args.no_commit,
        no_branch=args.no_branch,
        dry_run=args.dry_run,
        use_headroom=args.headroom,
        caveman_off=args.caveman_off,
        max_retries=args.max_retries,
        docs_mode=args.docs_mode,
        verify_mode=args.verify_mode,
        timeout_seconds=args.timeout_seconds,
    ).run()


if __name__ == "__main__":
    main()
