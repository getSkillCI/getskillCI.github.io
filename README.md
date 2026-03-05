# skillCI — getskillCI.github.io

Marketing site for [skillci.com](https://skillci.com).

Serves on GitHub Pages from the `main` branch. Custom domain configured via `CNAME`.

## Structure

```
index.html          — Main landing page
docs/
  log-analysis.html — Local log analysis explainer
scripts/
  parse_claude_logs.py — Pass 1 JSONL metrics extractor
assets/
  wordmark.svg
  skillCI-icon-*.png
  skillCI-*-lockup.jpg
CNAME               — skillci.com
```

## Local Log Analysis

`scripts/parse_claude_logs.py` scans `~/.claude/projects/**/*.jsonl` and outputs session-level metrics as JSON. Requires Python 3.9+, no external dependencies.

```bash
# Scan all Claude Code projects, pretty-print to stdout
python scripts/parse_claude_logs.py

# Single project directory
python scripts/parse_claude_logs.py --project ~/.claude/projects/-Users-you-code-my-service

# Last 7 days only
python scripts/parse_claude_logs.py --days 7

# Write output to file
python scripts/parse_claude_logs.py --out metrics.json

# Compact JSON (no indentation)
python scripts/parse_claude_logs.py --pretty false
```

### Output fields (per session)

| Field | Description |
|---|---|
| `session_id` | JSONL filename stem |
| `project` | Parent directory name |
| `turns` | Total message turns |
| `user_turns` / `assistant_turns` | Counts by role |
| `total_input_tokens` | Sum of `usage.input_tokens` across assistant turns |
| `total_output_tokens` | Sum of `usage.output_tokens` |
| `total_cache_read_tokens` | Tokens served from cache |
| `cache_hit_ratio` | `cache_read / input` — higher is cheaper |
| `tool_calls` | Tool use blocks in assistant turns |
| `tool_errors` | `tool_result` records with `isError: true` |
| `tool_error_rate` | `tool_errors / tool_calls` |
| `compaction_events` | Count of `summary` records (context pressure events) |
| `reprompt_count_proxy` | User turns with no assistant turn between them |
| `skills_in_system_prompt` | Skill references found in the `system` record |
| `first_ts` / `last_ts` | Session timestamp bounds |
| `duration_seconds` | Wall-clock session length |

### What to act on

- **`reprompt_count_proxy` > 3** — agent is missing context. Check for a missing skill or CLAUDE.md rule.
- **`tool_error_rate` > 0.2** — agent is navigating unfamiliar structure. Add a skill describing the project layout.
- **`compaction_events` > 1** — context pressure. Break tasks down or tighten the system prompt.
- **`cache_hit_ratio` < 0.4** — system prompt changes frequently between turns. Stable CLAUDE.md content improves this.
