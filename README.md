# cc-retrospect

[![CI](https://github.com/vaddisrinivas/cc-retrospect/workflows/CI/badge.svg)](https://github.com/vaddisrinivas/cc-retrospect/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

**Stop burning tokens you can't see.**

Claude Code doesn't show what you're spending. No cost dashboard, no warning at 300 tool calls, no signal you used Opus for a task Sonnet could handle. cc-retrospect fixes that.

> **v3.0.0-rc** — Tool call history browser, Magic Create script generator (Claude-powered, structured JSON output), STYLE.md live sync, chain pattern analysis.

## Install

### Plugin (recommended)

In Claude Code:

```
/plugin marketplace add vaddisrinivas/cc-retrospect
/plugin install cc-retrospect@vaddisrinivas
/reload-plugins
```

### Git clone

```bash
git clone https://github.com/vaddisrinivas/cc-retrospect ~/.claude/plugins/cc-retrospect
cd ~/.claude/plugins/cc-retrospect
pip install -e .
```

Hooks are auto-discovered by Claude Code from the plugin directory.

### Update

```
/plugin update cc-retrospect@vaddisrinivas
/reload-plugins
```

Or via git:

```bash
cd ~/.claude/plugins/cc-retrospect
git pull
pip install -e .
```

---

## Dashboard

Live dashboard at `http://127.0.0.1:7731` — open it with:

```
/cc-retrospect:dashboard
```

The server starts once and persists across sessions. Refresh in-place with the ↺ button or `POST /api/reload`.

**What it shows:**
- Today's spend vs budget tiers (warning / critical / severe) with a 7-day cost sparkline
- Cost by project + daily stacked bar chart
- Session health grades (A–D) — searchable, filterable by grade, sortable by cost/duration/messages
- Tool usage bar chart — click any tool to filter sessions that used it
- Activity heatmap — sessions by hour-of-day × day-of-week
- Compaction event timeline
- Frustration word cloud
- Weekly trend table
- Saved report snapshots with open/load buttons
- Inline config editor for `~/.cc-retrospect/config.env`
- **Tool call history** — browse, filter, and search every tool call across your sessions
- **Chain patterns** — see which tools you chain most and how deep those chains run
- **STYLE.md sync** — view active vs generated style, trigger sync or regeneration

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `1`–`4` | Switch tabs |
| `/` | Focus session search |
| `↑` `↓` | Navigate sessions |
| `Enter` | Expand / collapse session |
| `Esc` | Clear search / close overlay |
| `d` | Toggle dark / light mode |
| `?` | Show all shortcuts |

**Export:** CSV and JSON buttons in the header. Reports tab saves timestamped snapshots.

**API endpoints** (all on `127.0.0.1:7731`):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/data.js` | GET | Current data payload |
| `/api/reload` | POST | Regenerate data from live sessions |
| `/api/config` | GET / POST | Read / write `config.env` |
| `/api/sessions` | GET | Last 100 sessions as JSON |
| `/api/health` | GET | Server health check |
| `/api/reports` | GET | List saved snapshots |
| `/reports/<name>` | GET | Serve a snapshot |
| `/api/toolcalls` | GET | Tool call history (filterable by tool name, error-only, limit) |
| `/api/chains` | GET | Aggregated tool chain patterns |
| `/api/style` | GET | Active STYLE.md content |
| `/api/style/sync` | POST | Sync generated STYLE.md → `~/.claude/STYLE.md` |
| `/api/style/generate` | POST | Regenerate STYLE.md from session history |
| `/api/magic-create` | POST | Generate a reusable script from selected tool calls |
| `/api/scripts` | GET | List saved generated scripts |

Port defaults to `7731`. Override with `CC_RETROSPECT_PORT=XXXX`.

---

## Magic Create

Select tool calls from your session history and turn them into a reusable, fully-commented bash script — powered by Claude.

**Scopes:**
- **Selected calls only** — script from exactly the rows you checked
- **This project** — script scoped to one project (uses `$PROJECT_ROOT`)
- **Cross-project** — portable script with `$1`/args instead of hardcoded paths

Generated scripts are saved to `~/.claude/plugins/generated_scripts/` (configurable) and a one-line entry is appended to `~/.claude/STYLE.md` under `## Generated Scripts` so Claude knows when to suggest them.

Claude returns a **structured JSON response** (`{"description", "when_to_use", "script"}`) — no fragile comment parsing, clean extraction every time.

**Configure in `~/.cc-retrospect/config.env`:**

```env
MAGIC_CREATE__SAVE_DIR=~/.claude/plugins/generated_scripts
MAGIC_CREATE__MODEL=claude-sonnet-4-6   # default: claude -p default
MAGIC_CREATE__TIMEOUT_SECONDS=120
MAGIC_CREATE__MAX_CALLS=60
```

---

## How it works

### Hooks (automatic, silent)

Hooks fire on every session with zero setup:

| Hook | Trigger | What it does |
|------|---------|-------------|
| **Session end** | Session closes | Cache cost/tokens/tools, track daily spend, log waste flags, update trends, auto-sync STYLE.md |
| **Session start** | Session opens | Show last-session recap, daily digest, tips if thresholds exceeded |
| **Pre-tool** | Before WebFetch/Agent/Bash | Warn on GitHub WebFetch (use `gh`), Agent for simple searches (use Grep), long Bash chains |
| **Post-tool** | After any tool | Nudge `/compact` at 150+ and 300+ tool calls; auto-compact at 300+ if `HINTS__AUTO_COMPACT=true`; suggest cheaper model if `HINTS__MODEL_NUDGE=true` |
| **User prompt** | Before prompt submit | Detect mega-pastes (>1000 chars) and very long prompts |
| **Compaction** | Before/after compact | Log compaction events with token counts |

### Commands (instant data, no AI)

Slash commands that run the Python analyzers directly — fast, no tokens spent on reasoning:

```
/cc-retrospect:dashboard   Open the live dashboard (starts server if needed)
/cc-retrospect:cost        Cost breakdown by project, model, time period
/cc-retrospect:status      Plugin health check — verify install, hooks, data
/cc-retrospect:config      Show current config values and overrides
/cc-retrospect:reset       Clear cached data, force full re-scan
/cc-retrospect:uninstall   Remove hooks from settings.json
```

All commands support `--json`, `--project NAME`, and `--days N` flags.

### Skill (AI-powered analysis)

One skill — Claude runs the analyzers and then reasons about root causes, behavioral patterns, and personalized recommendations:

```
/cc-retrospect              Full retrospective — cost + waste + health + habits + savings + model
/cc-retrospect waste        Deep waste analysis with root cause reasoning
/cc-retrospect health       Health deep-dive — session discipline, frustration patterns
/cc-retrospect savings      Prioritized savings recommendations with dollar amounts
/cc-retrospect model        Model efficiency — per-project routing table
/cc-retrospect profile      Full behavioral profile + work style analysis
/cc-retrospect digest       Morning briefing — yesterday's numbers vs baseline
/cc-retrospect habits       Usage patterns — session lengths, peak hours, tools
/cc-retrospect compare      This week vs last week
/cc-retrospect trends       Weekly trend tracking over time
/cc-retrospect tips         1-3 actionable tips from recent patterns
/cc-retrospect report       Full markdown report
/cc-retrospect learn        Generate STYLE.md + LEARNINGS.md from your history
/cc-retrospect cleanup      Disk waste scan + cleanup recommendations
/cc-retrospect export       JSON export of all session data
/cc-retrospect hints        Show/configure which inline hints are active
/cc-retrospect dashboard    Open the visual dashboard
```

---

## Configuration

Override defaults in `~/.cc-retrospect/config.env`:

```env
# Pricing ($/MTok) — auto-detected for claude-opus-4-6, sonnet-4-6, haiku-4-5
PRICING__OPUS__INPUT_PER_MTOK=15.0
PRICING__SONNET__INPUT_PER_MTOK=3.0

# Thresholds
THRESHOLDS__DAILY_COST_WARNING=500.0
THRESHOLDS__COMPACT_NUDGE_FIRST=150
THRESHOLDS__LONG_SESSION_MINUTES=120

# Toggle hooks on/off
HINTS__SESSION_START=true
HINTS__PRE_TOOL=true
HINTS__POST_TOOL=true
HINTS__AUTO_COMPACT=true        # auto-fire /compact at second nudge threshold
HINTS__MODEL_NUDGE=true         # suggest cheaper model mid-session
HINTS__DIGEST_ON_START=false    # show yesterday's digest on every session open
HINTS__WASTE_TO_LATER=false     # write waste flags to LATER.md (requires cc-later)

# Exclude projects/entrypoints from analysis
FILTER__EXCLUDE_ENTRYPOINTS=["cc-retrospect","cc-later"]

# Dashboard server port (default: 7731)
# CC_RETROSPECT_PORT=7731

# Magic Create script generator
MAGIC_CREATE__SAVE_DIR=~/.claude/plugins/generated_scripts
MAGIC_CREATE__MODEL=claude-sonnet-4-6
MAGIC_CREATE__TIMEOUT_SECONDS=120
MAGIC_CREATE__MAX_CALLS=60
```

Full config reference: [docs/configuration.md](docs/configuration.md)

---

## Architecture

```
cc_retrospect/
  config.py               Config models (Pydantic + pydantic-settings)
  models.py               Data models (SessionSummary, AnalysisResult, ToolCall, etc.)
  parsers.py              JSONL parsing, session analysis, cost computation
  cache.py                Session cache, atomic writes, live state
  analyzers.py            9 analyzers (Cost, Waste, Health, Habits, Tips, Compare, Savings, Model, Trend)
  hooks.py                7 hooks (stop, start, pre/post tool, prompt, pre/post compact)
  commands.py             17 command entry points
  dashboard.py            Dashboard HTML + data payload generation
  dashboard_server.py     Persistent HTTP daemon on 127.0.0.1:7731
  dashboard_template.html Dashboard UI (Chart.js, vanilla JS, dark/light theme)
  utils.py                Formatting, filtering, rendering
  learn.py                STYLE.md / LEARNINGS.md generation
  core.py                 Backward-compat re-export shim
```

Data payload sent to the dashboard (`D`):

```
D.state                Today's cost, per-project breakdown, budget alert state
D.sessions             All sessions in window (cost, tokens, tools, waste flags, grades)
D.trends               Weekly snapshots
D.compactions          Compaction events
D.budget_tiers         Warning / critical / severe thresholds
D.tool_usage           Aggregate tool counts across all sessions
D.hourly_activity      Sessions per hour of day (24 buckets)
D.cost_by_day          Daily cost totals
D.model_recommendation Haiku vs Sonnet advisory
D.reports              Saved snapshot list
D.chain_patterns       Top tool chain patterns by total length
```

## Data & Privacy

Reads `~/.claude/projects/` — the JSONL files Claude Code already writes. No network calls, no telemetry, no external services. Cache stored at `~/.cc-retrospect/`.

## Documentation

- [Commands & Analysis](docs/commands.md)
- [Configuration](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](CONTRIBUTING.md)
