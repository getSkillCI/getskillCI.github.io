# SkillCI Log Analysis (Local, Private)

_Last updated: 2026-03-06_

This document is now the canonical internal log-analysis reference (moved from `log-analysis.html`).

## 1) Where the data lives

Claude Code transcripts are in:

- `~/.claude/projects/`
- one `.jsonl` file per session

## 2) Local parser script

Script path:

- `/Users/chloe/code/getskillCI.github.io/scripts/parse_claude_logs.py`

Example runs:

```bash
python scripts/parse_claude_logs.py
python scripts/parse_claude_logs.py --days 14
python scripts/parse_claude_logs.py --project ~/.claude/projects/-Users-you-code-my-service
python scripts/parse_claude_logs.py --out metrics.json
```

## 3) Do we have actual analytics?

Yes — generated on 2026-03-06 from a fresh run (`--days 14`).

### Current snapshot

- Sessions analyzed: **3**
- Total input tokens: **2,067**
- Total output tokens: **19,635**
- Total cache-read tokens: **1,030,879**
- Weighted cache-hit ratio: **0.998**
- Tool calls: **34**
- Tool errors: **0**
- Overall tool error rate: **0.000**
- Total reprompt proxy count: **1**
- Total compaction events: **0**
- Median turns/session: **37**

### Top sessions by input tokens

1. `88f9385a-95f7-4748-9db1-cef9c0e9cf2b` (`-Users-chloe-code-getskillCI-github-io`) — input: 2013, tool error rate: 0.0, reprompt proxy: 1  
2. `de40b65e-8cee-4de0-ac36-d34a0f76176d` (`-Users-chloe--openclaw`) — input: 42, tool error rate: 0.0, reprompt proxy: 0  
3. `be7224db-e87f-4992-8808-0390ea24d051` (`-Users-chloe-code-chloe-homepage`) — input: 12, tool error rate: 0.0, reprompt proxy: 0

## 4) Interpretation (quick)

- We **do** have real analytics now.
- Sample size is still small (3 sessions), so this is an early baseline.
- The next useful step is to run this daily/weekly and append trend deltas (reprompts, error rate, cache behavior, token cost trajectory).

## 5) LLM vs no-LLM

- **No LLM needed** for baseline observability (counts, rates, trend lines).
- **LLM useful** for pattern diagnosis + drafting interventions (skills/CLAUDE.md updates).
