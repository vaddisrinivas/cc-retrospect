# Configuration

## Config file

Create `~/.cc-retrospect/config.env` to override defaults. Keys use `__` as the nested field delimiter:

```env
# Pricing ($/MTok) — update when Anthropic changes rates
PRICING__OPUS__INPUT_PER_MTOK=15.0
PRICING__OPUS__OUTPUT_PER_MTOK=75.0
PRICING__OPUS__CACHE_CREATE_PER_MTOK=18.75
PRICING__OPUS__CACHE_READ_PER_MTOK=1.50

PRICING__SONNET__INPUT_PER_MTOK=3.0
PRICING__SONNET__OUTPUT_PER_MTOK=15.0

PRICING__HAIKU__INPUT_PER_MTOK=0.80
PRICING__HAIKU__OUTPUT_PER_MTOK=4.0

# Thresholds
THRESHOLDS__LONG_SESSION_MINUTES=120
THRESHOLDS__LONG_SESSION_MESSAGES=200
THRESHOLDS__MEGA_PROMPT_CHARS=1000
THRESHOLDS__MAX_SUBAGENTS_PER_SESSION=10
THRESHOLDS__DAILY_COST_WARNING=500
THRESHOLDS__COMPACT_NUDGE_FIRST=150
THRESHOLDS__COMPACT_NUDGE_SECOND=300

# Inline hints (true/false)
HINTS__SESSION_START=true
HINTS__PRE_TOOL=true
HINTS__POST_TOOL=true
HINTS__USER_PROMPT=true
HINTS__DAILY_HEALTH=true
HINTS__DAILY_DIGEST=true
HINTS__WASTE_ON_STOP=true
HINTS__AUTO_LEARN=true
```

Run `/cc-retrospect:config` to verify your overrides are loading. See `scripts/default_config.env` for the full reference with all available keys.

## Verify config

```
/cc-retrospect:config
/cc-retrospect:config --json
```

## Logging

For internal diagnostics on stderr:

```env
CC_RETROSPECT_LOG_LEVEL=DEBUG
```

## Custom analyzers

Drop a `.py` file in `~/.cc-retrospect/analyzers/`:

```python
class MyAnalyzer:
    name = "my-check"
    description = "Flag sessions over budget"

    def analyze(self, sessions, config):
        from cc_retrospect.core import AnalysisResult, Recommendation
        over = [s for s in sessions if s.total_cost > 200]
        recs = [Recommendation(severity="warning", description=f"{len(over)} sessions over $200")]
        return AnalysisResult(title="Budget", recommendations=recs)
```

Auto-discovered and included in `/cc-retrospect:report`.

## Message strings

All user-facing strings are configurable via `MESSAGES__<KEY>` in config.env. Run `/cc-retrospect:config --json` and look at the `messages` section to see all available keys and their defaults.
