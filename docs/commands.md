# Commands & Skills

## Automatic hooks

These fire silently — no commands needed.

| Hook | When | What it does |
|---|---|---|
| **Stop** | Session ends | Caches session summary (cost, tokens, tools, frustration) |
| **SessionStart** | Session begins | Shows last-session recap + daily digest on first session of new day |
| **PreToolUse** | Before WebFetch/Agent/Bash | Warns: GitHub URL → use `gh`, simple search → use Grep, Bash chain → combine |
| **PostToolUse** | After every tool | Nudges `/compact` at 150+ calls, warns on subagent overuse |
| **UserPromptSubmit** | Before prompt sent | Warns on oversized pastes (>1000 chars with high newline density) |
| **PreCompact** | Before compaction | Logs compaction event |
| **PostCompact** | After compaction | Logs tokens freed |

## Commands

All commands support `--json` for structured output, `--project NAME` to filter by project, and `--days N` to scope to recent days.

| Command | What it does |
|---|---|
| `/cc-retrospect:cost` | Cost by project, model, and time period. What-if Sonnet savings. |
| `/cc-retrospect:habits` | Session lengths, peak hours, tool usage, frustration signals |
| `/cc-retrospect:health` | Long sessions, subagent overuse, cost velocity, cache hit rate |
| `/cc-retrospect:waste` | WebFetch to GitHub, tool chains, oversized prompts, model mismatch |
| `/cc-retrospect:tips` | 1-3 actionable tips from your most recent session |
| `/cc-retrospect:compare` | This week vs last week |
| `/cc-retrospect:savings` | Per-habit savings projections with actual $/month from your data |
| `/cc-retrospect:model` | Model efficiency — which sessions wasted Opus on simple tasks |
| `/cc-retrospect:digest` | Yesterday's full digest with model + savings analysis |
| `/cc-retrospect:trends` | Weekly trend tracking. Use `--backfill` to seed from historical data. |
| `/cc-retrospect:learn` | Analyze your messages, generate STYLE.md + LEARNINGS.md |
| `/cc-retrospect:report` | Full markdown report saved to `~/.cc-retrospect/reports/` |
| `/cc-retrospect:export` | Dump all session data as JSON (pipeable) |
| `/cc-retrospect:status` | Plugin health check — verify install, data, dependencies |
| `/cc-retrospect:config` | Show current config values, verify overrides are loading |
| `/cc-retrospect:hints` | Show which inline hints are enabled and how to toggle them |
| `/cc-retrospect:reset` | Clear all cached data (sessions, state, trends). Forces full re-scan. |
| `/cc-retrospect:uninstall` | Remove hooks and plugin registration from settings.json |

### Flags

```bash
# JSON output (pipeable)
/cc-retrospect:cost --json

# Filter to one project
/cc-retrospect:waste --project myapp

# Last 7 days only
/cc-retrospect:savings --days 7

# Combine
/cc-retrospect:cost --project myapp --days 30 --json
```

## Skills

Skills use Claude's reasoning to analyze patterns that numbers alone can't capture.

| Skill | What it does |
|---|---|
| `/cc-retrospect:analyze` | Full retrospective: cost + habits + health + waste + model efficiency + plan mode opportunities + volatile hotspots |
| `/cc-retrospect:profile` | Behavioral analysis of your communication style. Generates a STYLE.md you can drop into `~/.claude/`. |
| `/cc-retrospect:cleanup` | Scans `~/.claude/` for disk waste (stale subagent logs, failed telemetry, old sessions). Asks before deleting. |

### Hybrid skills

These run the precision command first, then Claude interprets the results with project-specific reasoning:

| Skill | What it does |
|---|---|
| `/cc-retrospect:waste-analysis` | Deep waste analysis — names worst projects, explains why each pattern costs money |
| `/cc-retrospect:savings-analysis` | Prioritizes savings by impact, explains the math behind each recommendation |
| `/cc-retrospect:model-analysis` | Per-project model routing table — which projects need Opus vs Sonnet |
| `/cc-retrospect:health-analysis` | Correlates frustration with time of day, grades each project A-D |
| `/cc-retrospect:digest-analysis` | Morning briefing — was yesterday better or worse? One specific action for today. |
