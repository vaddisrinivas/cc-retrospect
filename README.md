# cc-sentinel

Proactive Claude Code guardian. Real-time waste interception, auto-compact nudges, session health tracking, cost analytics, and actionable tips.

## Features

- **Real-time hooks** — PreToolUse intercepts wasteful patterns (WebFetch to GitHub, excessive subagents, long tool chains) before they run
- **Auto-compact nudges** — PostToolUse warns at 150+ messages, strongly recommends `/compact` at 300+
- **Session summaries** — SessionStart shows last session cost, duration, and subagent count (project-scoped, no cross-project leakage)
- **Cost analytics** — breakdown by project, model, time period with what-if scenarios
- **Waste detection** — tool chains, mega prompts, model mismatch, WebFetch to GitHub
- **Custom analyzers** — drop a `.py` file in `~/.cc-sentinel/analyzers/` to extend

## Install

```bash
git clone https://github.com/vaddisrinivas/cc-sentinel ~/.claude/plugins/cc-sentinel
cd ~/.claude/plugins/cc-sentinel
pip install -e .
```

Then add the hooks to your Claude Code settings:

```bash
cat hooks/hooks.json
```

Copy the hook entries into `~/.claude/settings.json` under `"hooks"`.

## Commands

| Command | What it does |
|---|---|
| `/cc-sentinel:analyze` | Run full analysis (cost + habits + health + waste) |
| `/cc-sentinel:cost` | Cost breakdown by project, model, time period |
| `/cc-sentinel:habits` | Session lengths, peak hours, tool usage, frustration signals |
| `/cc-sentinel:health` | Health checks: long sessions, subagent overuse, config issues |
| `/cc-sentinel:tips` | 1-3 actionable tips from recent session patterns |
| `/cc-sentinel:report` | Full markdown report saved to `~/.cc-sentinel/reports/` |
| `/cc-sentinel:compare` | This week vs last week comparison |
| `/cc-sentinel:waste` | Detect wasted tokens: WebFetch to GitHub, tool chains, model mismatch |

## Configuration

Create `~/.cc-sentinel/config.env` to override defaults:

```env
# Pricing ($/MTok)
PRICING_OPUS_INPUT_PER_MTOK=15.0
PRICING_SONNET_INPUT_PER_MTOK=3.0

# Thresholds
THRESHOLD_LONG_SESSION_MINUTES=120
THRESHOLD_MEGA_PROMPT_CHARS=1000
THRESHOLD_DAILY_COST_WARNING=500

# Extra waste domains to flag on WebFetch
WASTE_WEBFETCH_DOMAINS=github.com,api.github.com,stackoverflow.com
```

## Custom analyzers

```python
# ~/.cc-sentinel/analyzers/my_check.py
class MyAnalyzer:
    name = "my-check"
    description = "My custom analysis"

    def analyze(self, sessions, config):
        # sessions: list[SessionSummary]
        # return AnalysisResult(title, sections, recommendations)
        ...
```

Auto-discovered and included in `/cc-sentinel:report`.

## Data

All data is read locally from `~/.claude/projects/`. No network calls, no telemetry.

Cache stored at `~/.cc-sentinel/sessions.jsonl`. Delete it to force a full re-scan.
