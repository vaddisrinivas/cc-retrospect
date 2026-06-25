# Development

## Setup

```bash
git clone https://github.com/vaddisrinivas/cc-retrospect
cd cc-retrospect
uv pip install -e ".[test]"
```

## Tests

```bash
pytest                    # all tests (fast, ~60s)
pytest --cov              # with coverage
pytest tests/test_real_data.py  # real data integration (requires ~/.claude, ~2 min)
```

Real data tests auto-skip on CI and machines without Claude Code session data.

## Lint

```bash
ruff check cc_retrospect/ scripts/ tests/
pyright --pythonpath ./.venv/bin/python cc_retrospect/ scripts/
```

## Smoke test

```bash
python3 scripts/dispatch.py status
python3 scripts/dispatch.py cost
python3 scripts/dispatch.py hints
echo '{}' | python3 scripts/dispatch.py stop_hook
```

## Adding an analyzer

1. Add the class to `cc_retrospect/analyzers.py` following the `Analyzer` protocol.
2. Add it to `_BUILTIN_ANALYZERS` when it should appear in full reports.
3. Add a `run_<name>()` entry point in `cc_retrospect/commands.py`.
4. Re-export from `cc_retrospect/core.py`.
5. Add the route in `scripts/dispatch.py`.
6. Add `commands/<name>.md`.
7. Add tests and update dispatch map assertions in `test_proactive.py` and `test_integration.py`.

## Release

Tag and push to trigger the release workflow:

```bash
git tag v3.0.0
git push origin v3.0.0
```

This runs tests, builds the package, and creates a GitHub release with artifacts.
