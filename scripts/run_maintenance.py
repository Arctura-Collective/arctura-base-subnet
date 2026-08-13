#!/usr/bin/env python3
"""Deterministic Arctura subnet maintenance checks.

This script performs one maintenance mode at a time and writes a concise report to
standard output. The calling agent is responsible for posting that report to Slack.
It never invokes btcli, signs a transaction, or moves funds.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


DEFAULT_REPO_DIR = Path("/home/ubuntu/arctura-base-subnet")
LOG_NAMES = ("burn_cost.log", "validator.log")


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def run_command(command: list[str], repo_dir: Path) -> tuple[int, str, str]:
    result = subprocess.run(command, cwd=repo_dir, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def summarize_log(log_path: Path, now: dt.datetime) -> str:
    if not log_path.exists():
        return f"{log_path.name}: MISSING — no health conclusion available."

    modified_at = dt.datetime.fromtimestamp(log_path.stat().st_mtime, tz=dt.UTC)
    age = now - modified_at
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    latest = lines[-1].strip() if lines else "empty"
    freshness = "current" if age <= dt.timedelta(hours=24) else "STALE"
    return (
        f"{log_path.name}: {freshness}; modified {age.total_seconds() / 3600:.1f}h ago; "
        f"latest entry: {latest[:240] or 'empty'}"
    )


def daily_health_report(repo_dir: Path) -> str:
    now = utc_now()
    summaries = [summarize_log(repo_dir / name, now) for name in LOG_NAMES]
    return "\n".join(
        [
            "ARCTURA DAILY HEALTH",
            f"Timestamp: {now.isoformat()}",
            *[f"- {summary}" for summary in summaries],
            "Safety: no on-chain action attempted.",
        ]
    )


def create_security_issue(repo_dir: Path, audit_output: str) -> str:
    title = f"[Security Audit] Dependency advisory detected — {utc_now().date().isoformat()}"
    body = (
        "The scheduled Arctura dependency audit exited non-zero.\n\n"
        f"```text\n{audit_output[-3500:]}\n```\n\n"
        "Review dependency declarations and remediation status before the next deployment."
    )
    command = [
        "gh",
        "issue",
        "create",
        "--repo",
        "bittensaur/arctura-base-subnet",
        "--title",
        title,
        "--body",
        body,
    ]
    code, stdout, stderr = run_command(command, repo_dir)
    if code == 0:
        return f"GitHub issue created: {stdout}"
    return f"GitHub issue creation failed: {stderr or stdout}"


def weekly_security_report(repo_dir: Path, create_issues: bool) -> str:
    code, stdout, stderr = run_command(
        [sys.executable, "scripts/dependency_audit.py"], repo_dir
    )
    audit_output = "\n".join(part for part in (stdout, stderr) if part)
    if code == 0:
        issue_status = "No GitHub issue created; audit passed."
        status = "PASSED"
    elif create_issues:
        issue_status = create_security_issue(repo_dir, audit_output)
        status = "FAILED — issue workflow invoked"
    else:
        issue_status = "FAILED — issue creation disabled for this run."
        status = "FAILED"
    return "\n".join(
        [
            "ARCTURA WEEKLY SECURITY AUDIT",
            f"Status: {status}",
            f"Issue action: {issue_status}",
            "Audit output:",
            audit_output[-1200:] or "No audit output.",
            "Safety: no on-chain action attempted.",
        ]
    )


def preflight_report(repo_dir: Path) -> str:
    code, stdout, stderr = run_command([sys.executable, "-m", "pytest", "tests/", "-v"], repo_dir)
    checklist = repo_dir / "docs" / "GO_NO_GO_CHECKLIST.md"
    test_status = "PASSED" if code == 0 else "FAILED"
    return "\n".join(
        [
            "ARCTURA FINNEY PRE-FLIGHT",
            f"Test suite: {test_status}",
            f"Checklist file: {'present' if checklist.exists() else 'MISSING'}",
            "Capital, burn cost, network reachability, and multisig approvals: manual owner verification required.",
            "Registration command: NOT RUN. No transaction broadcast.",
            "Test output:",
            (stdout or stderr)[-1200:] if (stdout or stderr) else "No test output.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Arctura subnet maintenance checks.")
    parser.add_argument("--mode", choices=("daily", "weekly", "preflight"), required=True)
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--create-issues", action="store_true")
    args = parser.parse_args()

    repo_dir = args.repo_dir.resolve()
    if not repo_dir.exists():
        print(f"Repository directory does not exist: {repo_dir}", file=sys.stderr)
        return 2

    if args.mode == "daily":
        print(daily_health_report(repo_dir))
    elif args.mode == "weekly":
        print(weekly_security_report(repo_dir, args.create_issues))
    else:
        print(preflight_report(repo_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
