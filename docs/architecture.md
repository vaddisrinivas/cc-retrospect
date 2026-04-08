# Architecture

## File structure

```
cc_retrospect/
  core.py              — all business logic (~1900 LOC)
  __init__.py           — version + public API exports
  py.typed              — PEP 561 marker
scripts/
  dispatch.py           — stdin/argv router (25 routes)
  default_config.env    — full config reference
commands/*.md           — 18 slash commands (single bash block each)
skills/*/SKILL.md       — 8 skills (3 standalone + 5 hybrid)
hooks/hooks.json        — 7 hook definitions
tests/                  — 277+ tests
```

## Three layers

### Precision layer (Python)

Exact numbers. Deterministic. Fast.

`core.py` contains all analyzers: `CostAnalyzer`, `WasteAnalyzer`, `HabitsAnalyzer`, `HealthAnalyzer`, `TipsAnalyzer`, `CompareAnalyzer`, `SavingsAnalyzer`, `ModelAnalyzer`, `TrendAnalyzer`.

Each follows the same protocol:
```python
class Analyzer(Protocol):
    name: str
    description: str
    def analyze(self, sessions: list[SessionSummary], config: Config) -> AnalysisResult: ...
```

### Behavioral layer (Skills)

Claude reasons about patterns. Non-deterministic. Deep.

Skills run the precision commands first (`dispatch.py cost --json`), then interpret the output — naming specific projects, explaining correlations, spotting patterns Python can't.

### Action layer (Hooks)

Automatic. Silent unless there's something to warn about.

Hook flow:
```
SessionStart → load state.json → show recap/digest/health → init live state
PreToolUse   → check WebFetch/Agent/Bash patterns → warn if wasteful
PostToolUse  → increment counters → nudge compact at thresholds
UserPromptSubmit → check prompt size → warn on oversized pastes
PreCompact   → log compaction event
PostCompact  → log tokens freed
Stop         → analyze session → cache summary → update budget → refresh trends
```

## Data flow

```
~/.claude/projects/**/*.jsonl  ←  Claude Code writes these
         ↓
    analyze_session()          ←  parse JSONL, extract tokens/tools/frustration
         ↓
~/.cc-retrospect/sessions.jsonl ← cached summaries (append-only)
         ↓
    load_all_sessions()        ←  disk scan + cache merge
         ↓
    Analyzers                  ←  compute metrics
         ↓
    AnalysisResult             ←  sections + recommendations
         ↓
    render_markdown() / render_json()
```

## Config system

Uses pydantic-settings. Config loaded from (in priority order):
1. Environment variables (e.g. `PRICING__OPUS__INPUT_PER_MTOK=20`)
2. Config file at `~/.cc-retrospect/config.env`
3. Defaults in `Config(BaseSettings)`

All config fields are nested with `__` delimiter. No prefix needed.
