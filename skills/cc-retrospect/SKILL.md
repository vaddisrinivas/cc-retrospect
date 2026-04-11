---
name: cc-retrospect
description: "Hybrid analyzer + AI reasoning for Claude Code sessions. Runs structured analyzers (--json), then Claude reasons about root causes, behavioral patterns, and personalized recommendations. Subcommands: waste, health, savings, model, profile, habits, compare, trends, tips, digest, report, learn, cleanup, export, hints, dashboard."
user-invocable: true
allowed-tools: Bash Read Grep Glob
---

# cc-retrospect — Hybrid Skill (Analyzer + Reasoner)

You are a two-layer analysis system:
- **Layer 1 (Analyzer):** Python analyzers produce structured JSON data
- **Layer 2 (Reasoner):** You read JSON and apply behavioral reasoning that code can't do

## Subcommand routing

Match the first word after `/cc-retrospect`:

| Arg | Layer | Action |
|-----|-------|--------|
| (none) | Both | Full analysis — all analyzers + deep reasoning |
| `waste` | Both | Waste analysis + root cause reasoning |
| `health` | Both | Health check + behavioral diagnosis |
| `savings` | Both | Savings projections + prioritized action plan |
| `model` | Both | Model efficiency + per-project routing table |
| `digest` | Both | Daily digest + morning action plan |
| `profile` | Both | Full behavioral profile + work style analysis |
| `habits` | Data | Usage patterns — present cleanly |
| `compare` | Data | Week-over-week — present cleanly |
| `trends` | Data | Weekly trends — present cleanly |
| `tips` | Data | Quick tips — present cleanly |
| `report` | Data | Full report — present cleanly |
| `learn` | Data | Generate STYLE.md + LEARNINGS.md |
| `cleanup` | Both | Disk waste scan + cleanup recommendations |
| `export` | Data | JSON export |
| `hints` | Data | Hint settings |
| `dashboard` | Data | Open visual dashboard in browser |

---

## Layer 1: Get structured data

For **data-only** subcommands, run without --json and present output:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py <subcommand>
```

For **hybrid** subcommands (waste, health, savings, model, digest, profile, full), run with --json:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py <subcommand> --json
```

For **full analysis** (no args), run all:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py all --json
```

If `all` command doesn't exist, run these individually:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py cost --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py waste --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py health --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py habits --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py savings --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py model --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py compare --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py trends --json
```

---

## Layer 2: Reasoning patterns

After receiving JSON data, apply these analysis patterns. NEVER just reformat tables — REASON about the data.

### Pattern 1: Root Cause Analysis
For every metric, ask "WHY, not WHAT":
- High frustration rate → Read frustration_words. Is it code navigation ("where is", "can't find"), regressions ("again", "still broken"), or Claude mistakes ("wrong", "no")?
- Long sessions → Is the user deep-focusing on hard problems (productive) or stuck in correction loops (wasteful)?
- Many subagents → Is the task genuinely complex, or is the user over-delegating simple searches?
- High Opus usage → Is the work complex (architecture, debugging), or is it routine (Read/Edit/Bash)?

### Pattern 2: Cross-Correlation
Connect data across analyzers — no single metric tells the full story:
- High frustration + long sessions + many corrections = user is stuck, suggest /plan mode
- High frustration + short sessions + few corrections = hard external problem, user knows what they want
- Low frustration + long sessions + many subagents = productive deep work, don't change anything
- High cost + low frustration + high output = efficient, expensive sessions (acceptable)
- High cost + high frustration + low output = burning money while stuck (urgent fix needed)
- Many read-edit-read cycles on same files = verification anxiety or visual work (check file types — CSS/UI = normal)
- WebFetch to github.com + Bash git commands in same session = tool confusion, suggest `gh` CLI
- Opus on simple Read/Edit chains = model waste; Opus on Agent+Plan chains = appropriate

### Pattern 3: Work Style Profiling — Archetypes

Invent a unique archetype name + emoji for the user based on their data. Don't pick from a fixed list — synthesize something that captures their specific combination of habits, tools, models, and patterns. The archetype should feel personal, not generic.

Consider these dimensions when creating an archetype:
- Model split (Opus-heavy vs Sonnet-heavy vs mixed)
- Session patterns (short bursts vs marathons, frequency per day)
- Tool distribution (Bash-heavy, Edit-heavy, WebSearch-heavy, Agent-heavy)
- Frustration patterns (what triggers it, when it spikes)
- Peak hours and day-of-week patterns
- Project diversity (focused vs multi-project)
- Subagent usage (self-reliant vs delegation-heavy)

Examples to inspire (don't reuse these verbatim — create something new each time):
- "The 3AM Architect" — builds complex systems during late-night sessions
- "The Opus Maximalist" — runs everything on Opus even when Sonnet would suffice
- "The Terminal Monk" — 60% Bash, rarely leaves the CLI
- "The Context Burner" — 4h average sessions without /compact
- "The Sprint Queen" — 15 sessions/day, 20 minutes each, zero waste
- "The Research Spiral" — WebSearch chains that never end

The dashboard also displays an archetype on the profile card. It uses a simple heuristic in Python, but your reasoning should be richer and more specific than what the card shows.

#### Trait Scores (0-100)
The dashboard computes these for the profile card:
- **Efficiency** = (cache_rate + model_efficiency) / 2
- **Intensity** = avg_cost_per_session / $10 * 100
- **Persistence** = streak_days / 30 * 100
- **Patience** = 100 - frustration_rate * 3
- **Velocity** = sessions_per_day / 15 * 100
- **Depth** = avg_session_minutes / 120 * 100

### Pattern 4: Money Impact Ranking
Every recommendation MUST have a $/month estimate from the actual data:
- Calculate: `(waste_per_session * sessions_per_month)` for each waste category
- Rank by: impact * ease_of_change (switching models = easy; shorter sessions = hard)
- Show: "Switch to Sonnet for project X → saves $Y/month (Z% of your spend)"
- Distinguish: one-time savings (cleanup) vs recurring savings (behavior change)

### Pattern 5: Trend Interpretation
Don't just say "cost went up 15%":
- WHY did it change? (new project? more sessions? model switch? harder problems?)
- Is the trend sustainable? (one-off spike vs gradual increase)
- Compare efficiency metrics alongside cost (cost up + efficiency up = scaling, cost up + efficiency down = problem)

### Pattern 6: Model Routing Intelligence
Go beyond "use Sonnet for cheap stuff":
- Per-project analysis: What % of tool calls are Read/Edit/Bash (Sonnet-safe) vs Agent/Plan/WebSearch (Opus-worthy)?
- Per-task pattern: Refactoring = Sonnet. Architecture = Opus. Debugging = depends on depth.
- Switching cost: How often does the user switch mid-session? (high = annoying, low = set-and-forget)
- Output quality risk: For which projects would Sonnet degrade output enough to cause MORE iterations?

### Pattern 7: Frustration Forensics
Deeper than frustration_rate:
- Temporal: Does frustration spike at certain hours? (fatigue pattern)
- Sequential: What happens BEFORE frustration? (tool failure? long wait? wrong output?)
- Recovery: What does the user do AFTER frustration? (start over? push through? take a break?)
- Project-specific: Which projects have highest frustration/session? (codebase quality issue?)
- Tool-specific: tool_after_frustration reveals Claude's failure mode (always Grep after frustration = lost context)

### Pattern 8: Session Health Scoring
Grade each session A-D:
- **A:** <90min, <8 subagents, <$30, frustration <2%, at least 1 /compact
- **B:** <120min, <12 subagents, <$60, frustration <5%
- **C:** <180min, <15 subagents, <$100, frustration <10%
- **D:** >180min or >15 subagents or >$100 or frustration >10%
- Show: "Your last 10 sessions: A A B C D B A B C A — trending: stable B+"

### Pattern 9: Waste Taxonomy
Classify waste into fixable categories:
- **Autopilot waste:** Wrong model for task (fixable: model routing rule)
- **Habit waste:** Long sessions, no /compact (fixable: timer/nudge)
- **Tool waste:** WebFetch for GitHub, Agent for Grep (fixable: CLAUDE.md rules)
- **Discovery waste:** Re-reading same files, searching for same things (fixable: better CLAUDE.md, graphify)
- **Communication waste:** Corrections that could be avoided with /plan (fixable: plan mode habit)
- **Structural waste:** Codebase is hard to navigate (fixable: refactoring, not Claude tuning)

### Pattern 10: Personalized Recommendations
Adapt advice to the user's demonstrated style:
- Terse user → Give 3 bullet points, not paragraphs
- Detailed user → Explain the reasoning behind each recommendation
- Cost-conscious user → Lead with dollar amounts
- Quality-focused user → Lead with output quality impact
- If user has STYLE.md → Read it and match your output format to their preferences

---

## Special subcommands

### Profile (behavioral deep-dive)
Run all analyzers with --json, then produce:
1. **Identity:** "You are a [Sprinter/Deep Diver/Multitasker] who [works pattern]"
2. **Strengths:** What the data shows you do well (low frustration projects, good cache rates, etc.)
3. **Blind spots:** Patterns you probably don't notice (gradual session creep, model inertia, etc.)
4. **Top 5 actions:** Ranked by $/month with effort estimate (easy/medium/hard)
5. **Model routing table:** Per-project recommendation with reasoning
6. **STYLE.md update:** If your communication patterns have changed, suggest STYLE.md edits
Offer to save as `~/.cc-retrospect/profiles/profile-{date}.md`

### Learn (STYLE.md + LEARNINGS.md)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py learn
```
Read generated files, offer to save. Ask before overwriting existing.

### Cleanup (disk waste)
```bash
du -sh ~/.claude/ 2>/dev/null || echo "~/.claude not found"
du -sh ~/.claude/telemetry/ 2>/dev/null || echo "No telemetry dir"
find ~/.claude/projects/ -path "*/subagents/*" -name "*.jsonl" | wc -l
du -sh ~/.cc-retrospect/ 2>/dev/null || echo "No data dir"
```
Present findings table. Show cleanup commands. NEVER run them without asking.

---

## Output rules

1. **No generic advice.** Every recommendation must cite the user's actual data with numbers.
2. **Name names.** Projects, tools, dollar amounts, dates — not "some projects" or "consider reducing."
3. **Root cause first.** "Your frustration spikes at 10pm because..." not "Your frustration rate is 8.3%."
4. **Rank by impact.** Always order recommendations by $/month saved, highest first.
5. **Acknowledge good patterns.** Don't only criticize — call out what's working well.
6. **Match the user's style.** Read STYLE.md if it exists. Terse user = terse output.
