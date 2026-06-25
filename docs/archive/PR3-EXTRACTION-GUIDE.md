# PR 3: Monolith Split — Detailed Extraction Guide

**Objective:** Split 2112-line core.py into 9 focused modules while maintaining 100% backward compatibility.

**Key Constraint:** All 309 tests must pass with ZERO modifications.

---

## Module Creation Order (Dependency Order)

Follow this order to avoid circular imports:

1. **config.py** (160 LOC)
2. **models.py** (120 LOC)
3. **parsers.py** (200 LOC)
4. **utils.py** (60 LOC)
5. **cache.py** (80 LOC)
6. **analyzers.py** (370 LOC)
7. **commands.py** (360 LOC)
8. **learn.py** (400 LOC)
9. **hooks.py** (360 LOC)
10. **core.py** (shim) — re-export shim only (~50 LOC)

---

## Detailed Module Extraction

### 1. config.py (160 LOC)

**Source:** Lines 49-174 of core.py

```python
# Extract these classes:
- PricingConfig (line 52)
- ModelPricing (line 59)
- ThresholdsConfig (line 65)
- HintsConfig (line 84)
- MessagesConfig (line 95)
- FilterConfig (line 142)
- Config (line 149)

# Extract these functions:
- load_config() (line 166)
- default_config() (line 173)

# Import requirements:
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
```

**No internal dependencies** ✅

---

### 2. models.py (120 LOC)

**Source:** Lines 216-441, 867-911, 1685-1757 (scattered across core.py)

```python
# Extract these classes:
- UsageRecord (line 216)
- SessionSummary (line 300)
- Section (line 404)
- Recommendation (line 409)
- AnalysisResult (line 415) — includes render_markdown(), render_text(), render_json() methods
- CompactionEvent (line 867)
- LiveSessionState (line 876) — includes __getitem__, __setitem__, get() methods
- UserProfile (line 1685)
- Analyzer (Protocol at line 667)

# Import requirements:
from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable
```

**No internal dependencies** ✅

---

### 3. parsers.py (200 LOC)

**Source:** Lines 178-400+ (scattered)

```python
# Extract these functions:
- iter_jsonl(path: Path) (line 178)
- iter_project_sessions(claude_dir: Path) (line 195)
- extract_usage(entry: dict) (line 223)
- _pricing_for_model(model_str: str, pricing: ModelPricing) (line 243)
- compute_cost(rec: UsageRecord, pricing: ModelPricing) (line 263)
- analyze_session(jsonl_path: Path, proj_name: str, config: Config) (line 314)

# Import requirements:
from __future__ import annotations
import json
import logging
import re
from pathlib import Path
from typing import Iterator
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from cc_retrospect.config import Config, ModelPricing
from cc_retrospect.models import UsageRecord, SessionSummary

# Create module logger:
logger = logging.getLogger("cc_retrospect")
```

**Internal dependencies:** config, models ✅

---

### 4. utils.py (60 LOC)

**Source:** Lines 270-296, 444-458, 918-948 (scattered)

```python
# Extract these constants:
- _PROJECT_PREFIX_RE = re.compile(r"^/Users/[^/]+/Projects/") (line 272)

# Extract these functions:
- display_project(proj_path: str) (line 275)
- _fmt_tokens(t: int) (line 280)
- _fmt_cost(c: float) (line 287)
- _fmt_duration(minutes: int) (line 293)
- _group(items, key_fn) (line 444)
- _top(counter: Counter, limit: int = 10) (line 450)
- _union(items, fn) (line 454)
- _filter_sessions(sessions, project, days, config) (line 918)
- _render(analyzer_cls, payload, *, config, sessions) (line 938)

# Import requirements:
from __future__ import annotations
import re
from collections import Counter, defaultdict
from cc_retrospect.config import Config
from cc_retrospect.models import SessionSummary
```

**Internal dependencies:** config, models ✅

---

### 5. cache.py (80 LOC)

**Source:** Scattered + new functions

```python
# Extract from core.py:
- load_all_sessions(config: Config, project_filter: str | None) (line 838)
- _live_state_path(config: Config) (line 893)
- _init_live_state(config: Config) (line 897)
- _load_live_state(config: Config) (line 902)
- _save_live_state(config: Config, state) (line 910)

# Move from core.py helpers:
- _atomic_write_json(path: Path, data: dict) (line 31)
- _is_valid_session_id(session_id: str) (line 44)

# Import requirements:
from __future__ import annotations
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from cc_retrospect.config import Config
from cc_retrospect.models import SessionSummary, LiveSessionState
from cc_retrospect.parsers import iter_jsonl, analyze_session

logger = logging.getLogger("cc_retrospect")
```

**Internal dependencies:** config, models, parsers ✅

---

### 6. analyzers.py (370 LOC)

**Source:** Lines 460-834, 1089-1110

```python
# Extract these classes:
- CostAnalyzer (line 460)
- WasteAnalyzer (line 494)
- HabitsAnalyzer (line 531)
- HealthAnalyzer (line 572)
- TipsAnalyzer (line 609)
- CompareAnalyzer (line 634)
- SavingsAnalyzer (line 676)
- ModelAnalyzer (line 764)
- TrendAnalyzer (line 1089)

# Extract this function:
- get_analyzers(config: Config) (line 814)

# Extract this constant:
- _BUILTIN_ANALYZERS = [CostAnalyzer, WasteAnalyzer, ...] (line 811)

# Import requirements:
from __future__ import annotations
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cc_retrospect.config import Config
from cc_retrospect.models import SessionSummary, AnalysisResult, Section, Recommendation
from cc_retrospect.utils import display_project, _fmt_cost, _fmt_tokens, _fmt_duration, _group, _top

logger = logging.getLogger("cc_retrospect")
```

**Internal dependencies:** config, models, utils ✅

---

### 7. commands.py (360 LOC)

**Source:** Lines 950-1178

```python
# Extract these functions:
- run_cost(payload, *, config) (line 950)
- run_habits(payload, *, config) (line 951)
- run_health(payload, *, config) (line 952)
- run_tips(payload, *, config) (line 953)
- run_waste(payload, *, config) (line 954)
- run_compare(payload, *, config) (line 955)
- run_report(payload, *, config) (line 958)
- run_savings(payload, *, config) (line 976)
- run_model_efficiency(payload, *, config) (line 977)
- run_digest(payload, *, config) (line 980)
- run_hints(payload, *, config) (line 1022)
- run_status(payload, *, config) (line 1040)
- run_export(payload, *, config) (line 1081)
- run_trends(payload, *, config) (line 1123)
- run_reset(payload, *, config) (line 1131)
- run_config(payload, *, config) (line 1147)
- run_uninstall(payload, *, config) (line 1180)

# Import requirements:
from __future__ import annotations
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cc_retrospect.config import Config
from cc_retrospect.models import SessionSummary
from cc_retrospect.cache import load_all_sessions
from cc_retrospect.analyzers import get_analyzers
from cc_retrospect.utils import _render, _fmt_cost, _fmt_tokens
```

**Internal dependencies:** config, models, cache, analyzers, utils ✅

---

### 8. learn.py (400 LOC)

**Source:** Lines 1685-2095

```python
# Extract these functions:
- analyze_user_messages(sessions: list[SessionSummary], config: Config) (line 1711)
- generate_style(profile: UserProfile) (line 1948)
- generate_learnings(profile: UserProfile) (line 1986)
- run_learn(payload, *, config) (line 2058)

# Import requirements:
from __future__ import annotations
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from cc_retrospect.config import Config
from cc_retrospect.models import SessionSummary, UserProfile
from cc_retrospect.parsers import iter_project_sessions, iter_jsonl
from cc_retrospect.utils import display_project

logger = logging.getLogger("cc_retrospect")
```

**Internal dependencies:** config, models, parsers, utils ✅

---

### 9. hooks.py (360 LOC)

**Source:** Lines 1232-1628

```python
# Extract these functions:
- _update_trends(config: Config) (line 1232)
- _backfill_trends(config: Config) (line 1271)
- run_stop_hook(payload, *, config) (line 1317)
- run_session_start_hook(payload, *, config) (line 1411)
- run_pre_tool_use(payload, *, config) (line 1531)
- run_post_tool_use(payload, *, config) (line 1568)
- run_user_prompt(payload, *, config) (line 1597)
- run_pre_compact(payload, *, config) (line 1646)
- run_post_compact(payload, *, config) (line 1665)
- _compactions_path(config: Config) (line 1632)
- _load_compactions(config: Config) (line 1636)
- _should_show_daily_digest(config: Config) (line 2100)

# Import requirements:
from __future__ import annotations
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cc_retrospect.config import Config
from cc_retrospect.models import SessionSummary, CompactionEvent
from cc_retrospect.parsers import analyze_session, iter_jsonl
from cc_retrospect.utils import display_project, _fmt_cost, _fmt_duration, _filter_sessions
from cc_retrospect.cache import load_all_sessions, _atomic_write_json, _load_live_state, _save_live_state
from cc_retrospect.analyzers import get_analyzers
from cc_retrospect.learn import analyze_user_messages, generate_style, generate_learnings

logger = logging.getLogger("cc_retrospect")
```

**Internal dependencies:** All other modules ✅

---

### 10. core.py (50 LOC) — Backward Compatibility Shim

**Replace entire file with:**

```python
"""cc-retrospect core — backward compatibility shim.

All functionality has been moved to submodules for better organization.
This file re-exports everything to maintain compatibility with existing code.
"""
from __future__ import annotations

import logging
import os
import sys

# Logger setup (same as original)
logger = logging.getLogger("cc_retrospect")
if not logger.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("[cc-retrospect] %(levelname)s %(message)s"))
    logger.addHandler(_h)
logger.setLevel(getattr(logging, os.environ.get("CC_RETROSPECT_LOG_LEVEL", "WARNING").upper(), logging.WARNING))

# Re-export all public APIs
from cc_retrospect.config import (
    Config, PricingConfig, ModelPricing, ThresholdsConfig,
    HintsConfig, MessagesConfig, FilterConfig,
    load_config, default_config,
)

from cc_retrospect.models import (
    UsageRecord, SessionSummary, Section, Recommendation, AnalysisResult,
    CompactionEvent, LiveSessionState, UserProfile, Analyzer,
)

from cc_retrospect.parsers import (
    iter_jsonl, iter_project_sessions, extract_usage,
    _pricing_for_model, compute_cost, analyze_session,
)

from cc_retrospect.utils import (
    display_project, _fmt_tokens, _fmt_cost, _fmt_duration,
    _group, _top, _union, _filter_sessions, _render,
)

from cc_retrospect.cache import (
    load_all_sessions, _atomic_write_json, _is_valid_session_id,
    _init_live_state, _load_live_state, _save_live_state, _live_state_path,
)

from cc_retrospect.analyzers import (
    CostAnalyzer, WasteAnalyzer, HealthAnalyzer, HabitsAnalyzer,
    TipsAnalyzer, CompareAnalyzer, SavingsAnalyzer, ModelAnalyzer,
    TrendAnalyzer, get_analyzers,
)

from cc_retrospect.commands import (
    run_cost, run_habits, run_health, run_tips, run_waste, run_compare,
    run_report, run_savings, run_model_efficiency, run_digest, run_hints,
    run_status, run_export, run_trends, run_reset, run_config, run_uninstall,
)

from cc_retrospect.hooks import (
    run_stop_hook, run_session_start_hook,
    run_pre_tool_use, run_post_tool_use,
    run_user_prompt, run_pre_compact, run_post_compact,
)

from cc_retrospect.learn import (
    analyze_user_messages, generate_style, generate_learnings, run_learn,
)

__all__ = [
    # Config
    'Config', 'load_config', 'default_config',
    'PricingConfig', 'ModelPricing', 'ThresholdsConfig',
    'HintsConfig', 'MessagesConfig', 'FilterConfig',
    # Models
    'UsageRecord', 'SessionSummary', 'Section', 'Recommendation', 'AnalysisResult',
    'CompactionEvent', 'LiveSessionState', 'UserProfile', 'Analyzer',
    # Parsers
    'iter_jsonl', 'iter_project_sessions', 'extract_usage',
    'analyze_session', 'compute_cost',
    # Utils
    'display_project', '_fmt_cost', '_fmt_tokens', '_fmt_duration',
    '_filter_sessions', '_render', '_group', '_top', '_union',
    # Cache
    'load_all_sessions', '_atomic_write_json', '_is_valid_session_id',
    '_init_live_state', '_load_live_state', '_save_live_state', '_live_state_path',
    # Analyzers
    'CostAnalyzer', 'WasteAnalyzer', 'HealthAnalyzer', 'HabitsAnalyzer',
    'TipsAnalyzer', 'CompareAnalyzer', 'SavingsAnalyzer', 'ModelAnalyzer',
    'TrendAnalyzer', 'get_analyzers',
    # Commands
    'run_cost', 'run_habits', 'run_health', 'run_tips', 'run_waste', 'run_compare',
    'run_report', 'run_savings', 'run_model_efficiency', 'run_digest', 'run_hints',
    'run_status', 'run_export', 'run_trends', 'run_reset', 'run_config', 'run_uninstall',
    # Hooks
    'run_stop_hook', 'run_session_start_hook',
    'run_pre_tool_use', 'run_post_tool_use',
    'run_user_prompt', 'run_pre_compact', 'run_post_compact',
    # Learn
    'analyze_user_messages', 'generate_style', 'generate_learnings', 'run_learn',
    # Logger
    'logger',
]
```

---

## Verification Steps

After creating all modules:

```bash
# 1. Run all tests (should pass with ZERO modifications)
pytest tests/ -v --tb=short

# 2. Verify backward compatibility
python3 -c "
from cc_retrospect.core import (
    Config, load_all_sessions, run_cost,
    SessionSummary, CostAnalyzer, run_stop_hook
)
print('✅ All imports working')
"

# 3. Test smoke
python3 scripts/dispatch.py status
python3 scripts/dispatch.py cost

# 4. Check module imports work independently
python3 -c "from cc_retrospect.config import Config; print('✅ config.py works')"
python3 -c "from cc_retrospect.models import SessionSummary; print('✅ models.py works')"
# ... etc for each module
```

---

## Common Pitfalls to Avoid

1. **Circular imports:**
   - parsers.py cannot import from utils.py if utils.py imports from parsers.py
   - Solution: Resolve at creation time, use TYPE_CHECKING for type hints if needed

2. **Missing logger:**
   - Each module that uses logger must import it or setup will fail
   - Solution: `logger = logging.getLogger("cc_retrospect")` in each module

3. **Private functions:**
   - Functions starting with `_` are private but still need to be accessible
   - Solution: Include in `__all__` and re-export from core.py shim

4. **Constants:**
   - `_PROJECT_PREFIX_RE`, `_BUILTIN_ANALYZERS` must be accessible
   - Solution: Define in the module where they're used, re-export from shim

5. **Test imports:**
   - Tests import from `cc_retrospect.core` — must continue working
   - Solution: The shim in core.py guarantees this

---

## Rollback Strategy

If something breaks:
1. Keep the original core.py as backup
2. Comment out problematic imports in the shim
3. Verify tests one module at a time
4. Debug the circular dependency

The shim approach allows for gradual rollout — you can incrementally add exports as you verify each module works.
