#!/usr/bin/env python3
"""
parse_claude_logs.py — SkillCI Pass 1 local heuristics

Scans ~/.claude/projects/**/*.jsonl and outputs session-level metrics JSON.
No network, no LLM, no external dependencies (stdlib only).

Usage:
    python scripts/parse_claude_logs.py
    python scripts/parse_claude_logs.py --project ~/.claude/projects/-Users-you-code-myrepo
    python scripts/parse_claude_logs.py --out metrics.json
    python scripts/parse_claude_logs.py --days 7
    python scripts/parse_claude_logs.py --pretty false
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def parse_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def extract_metrics(records: list[dict], session_id: str, project: str, file_path: str) -> dict:
    turns = 0
    user_turns = 0
    assistant_turns = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_read_tokens = 0
    tool_calls = 0
    tool_errors = 0
    compaction_events = 0
    skills_in_system_prompt = 0
    timestamps = []

    prev_role = None
    reprompt_count_proxy = 0

    for rec in records:
        rec_type = rec.get("type", "")
        ts = rec.get("timestamp") or rec.get("ts")
        if ts:
            try:
                timestamps.append(ts)
            except Exception:
                pass

        if rec_type == "system":
            # Count skill references in the system prompt
            content = rec.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                )
            skills_in_system_prompt = len(
                re.findall(r"SKILL\.md|\.claude/skills/|<skill\b", content, re.IGNORECASE)
            )

        elif rec_type == "user":
            user_turns += 1
            turns += 1
            # Reprompt proxy: user turn immediately following another user turn
            if prev_role == "user":
                reprompt_count_proxy += 1
            prev_role = "user"

        elif rec_type == "assistant":
            assistant_turns += 1
            turns += 1
            prev_role = "assistant"

            msg = rec.get("message", {})
            usage = msg.get("usage", {})
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
            total_cache_read_tokens += usage.get("cache_read_input_tokens", 0)

            # Count tool_use blocks within assistant content
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls += 1

        elif rec_type == "tool_result":
            if rec.get("isError") or rec.get("is_error"):
                tool_errors += 1
            # Also handle tool_result with error content
            content = rec.get("content", "")
            if isinstance(content, str) and "error" in content.lower() and not rec.get("isError"):
                pass  # Only count explicit isError flags

        elif rec_type == "summary":
            compaction_events += 1
            prev_role = None  # reset after compaction

    # Timestamps
    first_ts = min(timestamps) if timestamps else None
    last_ts = max(timestamps) if timestamps else None
    duration_seconds = None
    if first_ts and last_ts and first_ts != last_ts:
        try:
            fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
            t0 = datetime.strptime(first_ts[:26].rstrip("Z") + "Z", fmt).replace(tzinfo=timezone.utc)
            t1 = datetime.strptime(last_ts[:26].rstrip("Z") + "Z", fmt).replace(tzinfo=timezone.utc)
            duration_seconds = int((t1 - t0).total_seconds())
        except Exception:
            pass

    # cache_hit_ratio expresses share of prompt tokens served from cache
    # denominator is (new input + cache reads), bounded to [0,1]
    cache_hit_ratio = None
    denom = total_input_tokens + total_cache_read_tokens
    if denom > 0:
        cache_hit_ratio = round(total_cache_read_tokens / denom, 3)

    tool_error_rate = None
    if tool_calls > 0:
        tool_error_rate = round(tool_errors / tool_calls, 3)

    return {
        "session_id": session_id,
        "project": project,
        "file": file_path,
        "turns": turns,
        "user_turns": user_turns,
        "assistant_turns": assistant_turns,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cache_read_tokens": total_cache_read_tokens,
        "cache_hit_ratio": cache_hit_ratio,
        "tool_calls": tool_calls,
        "tool_errors": tool_errors,
        "tool_error_rate": tool_error_rate,
        "compaction_events": compaction_events,
        "reprompt_count_proxy": reprompt_count_proxy,
        "skills_in_system_prompt": skills_in_system_prompt,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "duration_seconds": duration_seconds,
    }


def collect_jsonl_files(base_dir: Path) -> list[tuple[Path, str, str]]:
    """Return list of (path, project_name, session_id)."""
    results = []
    if not base_dir.exists():
        return results
    for jsonl in sorted(base_dir.glob("**/*.jsonl")):
        project = jsonl.parent.name
        session_id = jsonl.stem
        results.append((jsonl, project, session_id))
    return results


def cutoff_from_days(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def main():
    parser = argparse.ArgumentParser(description="Parse Claude Code JSONL session logs into metrics JSON.")
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Scan a specific project directory instead of all projects",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path.home() / ".claude" / "projects",
        help="Base directory for projects (default: ~/.claude/projects)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON output to this file (default: stdout)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Only include sessions with first_ts newer than N days ago",
    )
    parser.add_argument(
        "--pretty",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Pretty-print JSON output (default: true)",
    )
    args = parser.parse_args()

    base_dir = args.project if args.project else args.base
    files = collect_jsonl_files(base_dir)

    if not files:
        print(f"No .jsonl files found under {base_dir}", file=sys.stderr)
        sys.exit(1)

    cutoff = cutoff_from_days(args.days) if args.days else None

    sessions = []
    for path, project, session_id in files:
        records = parse_jsonl(path)
        if not records:
            continue
        metrics = extract_metrics(records, session_id, project, str(path))
        if cutoff and metrics.get("first_ts") and metrics["first_ts"] < cutoff:
            continue
        sessions.append(metrics)

    indent = 2 if args.pretty == "true" else None
    output = json.dumps(sessions, indent=indent)

    if args.out:
        args.out.write_text(output, encoding="utf-8")
        print(f"Wrote {len(sessions)} sessions to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
