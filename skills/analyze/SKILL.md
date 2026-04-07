---
name: analyze
description: Analyze Claude Code session data for costs, habits, health issues, and waste.
---

# cc-sentinel

Analyze your Claude Code usage to understand costs, detect waste, and improve your workflow.

## Commands

| Command | What it does |
|---|---|
| `/cc-sentinel:cost` | Cost breakdown by project, model, time period. What-if scenarios (Sonnet vs Opus). |
| `/cc-sentinel:habits` | Session lengths, peak hours, tool usage, frustration signals, prompt patterns. |
| `/cc-sentinel:health` | Health checks: long sessions, subagent overuse, config issues, cost velocity. |
| `/cc-sentinel:tips` | 1-3 actionable tips based on your recent session patterns. |
| `/cc-sentinel:report` | Full markdown report saved to `~/.cc-sentinel/reports/`. |
| `/cc-sentinel:compare` | This week vs last week comparison. |
| `/cc-sentinel:waste` | Detect wasted tokens: WebFetch to GitHub, tool chains, mega prompts, model mismatch. |

## How it works

- **Stop hook**: After each session, computes and caches a session summary to `~/.cc-sentinel/sessions.jsonl`
- **SessionStart hook**: Injects a brief summary of your last session (cost, duration, subagents) — only shown when starting a session in the same project folder
- **First run**: Scans all historical JSONL files (may take 10-30s) and builds the cache
- **Subsequent runs**: Reads from cache, only analyzes new sessions

## Data sources

All data is read locally from `~/.claude/projects/`. No network calls, no telemetry.

## Configuration

Create `~/.cc-sentinel/config.env` to override defaults:

```env
# Override pricing ($/MTok)
PRICING_OPUS_INPUT_PER_MTOK=15.0
PRICING_SONNET_INPUT_PER_MTOK=3.0

# Override thresholds
THRESHOLD_LONG_SESSION_MINUTES=120
THRESHOLD_MEGA_PROMPT_CHARS=1000
THRESHOLD_DAILY_COST_WARNING=500

# Add waste domains
WASTE_WEBFETCH_DOMAINS=github.com,api.github.com,stackoverflow.com
```

## Custom analyzers

Drop a `.py` file in `~/.cc-sentinel/analyzers/` implementing the Analyzer protocol:

```python
class MyAnalyzer:
    name = "my-check"
    description = "My custom analysis"

    def analyze(self, sessions, config):
        # sessions: list[SessionSummary]
        # Return AnalysisResult(title, sections, recommendations)
        ...
```

It will be auto-discovered and included in `/cc-sentinel:report`.
