# Changelog

All notable changes to cc-retrospect.

## v3.0.0

### Added
- Agent Diary v2 dashboard: calendar filters, week/month summaries, richer daily notes, best session, avoid-tomorrow note, and share/export card.
- `/cc-retrospect:weekly`: weekly agent review with spend, time, habit signals, and three rules suitable for `CLAUDE.md` or `AGENTS.md`.
- `/cc-retrospect:doctor`: install and runtime health check for hooks, dashboard, config, cache, and command files.
- Tool call history browser and `/cc-retrospect:toolcalls`.
- Magic Create script generator from selected tool calls.
- STYLE.md live sync and configurable learning rules.
- Chain pattern analysis, command palette, profile card exports, and five themes.

### Changed
- Package version is now stable `3.0.0`.
- Dashboard status surfaces install confidence signals: dashboard URL, cache size, hook manifest, and Claude settings references.
- Core implementation is split into focused modules, with `core.py` kept as a compatibility shim.

### Docs
- README now highlights Agent Diary v2, Weekly Review, and Doctor.
- Old audit/refactor planning notes moved to `docs/archive/`.

## v2.x

- Token tracking and waste detection.
- Cost breakdowns by model and project.
- Daily digest and health checks.
- Compaction tracking.
- Weekly trends.
