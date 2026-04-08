# LATER

Use this format:
- [ ] (P1) concise actionable task
- [ ] (P0) urgent production/security task
- [x] completed task

## Queue

- [x] (P0) fix default_config.env: already correct — uses PRICING__OPUS__INPUT_PER_MTOK format
- [x] (P0) delete dead cc_retrospective/ dir
- [ ] (P1) delete stale ~/.cc-sentinel/ data dir (hooks now write to ~/.cc-retrospect/)
- [ ] (P1) add cc_retrospective/ to .gitignore so it doesn't come back
- [ ] (P1) pyproject.toml optional-deps: rename `test` to match README (`uv pip install -e ".[test]"`)
- [ ] (P1) run_report: filename uses datetime.now() twice — could produce inconsistent timestamps
- [ ] (P2) test_real_data.py: slow (2+ min) — add pytest marker `@pytest.mark.slow` and skip by default in CI
- [ ] (P2) trend snapshots: only populate on stop_hook — add a /cc-retrospect:trends --backfill command to seed from historical data
- [ ] (P2) cleanup skill references "stale subagent logs" but doesn't document the actual paths to scan
- [ ] (P2) SKILL.md (analyze): shell fallback `find ~/.claude/projects/` won't work on Windows
- [ ] (P2) hooks.json: PreCompact/PostCompact hooks — verify these actually fire in Claude Code (may need different event names)
- [ ] (P3) add py.typed marker for downstream type checking
- [ ] (P3) add GitHub release workflow (tag → build → publish)
