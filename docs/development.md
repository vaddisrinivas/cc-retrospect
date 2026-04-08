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
pyflakes cc_retrospect/core.py scripts/dispatch.py tests/
```

## Smoke test

```bash
python3 scripts/dispatch.py status
python3 scripts/dispatch.py cost
python3 scripts/dispatch.py hints
echo '{}' | python3 scripts/dispatch.py stop_hook
```

## Adding an analyzer

1. Add the class to `core.py` following the `Analyzer` protocol
2. Add to `_BUILTIN_ANALYZERS` list
3. Add `run_<name>()` entry point
4. Add route in `dispatch.py`
5. Add `commands/<name>.md`
6. Add tests
7. Update dispatch map assertions in `test_proactive.py` and `test_integration.py`

## Release

Tag and push to trigger the release workflow:

```bash
git tag v2.2.0
git push origin v2.2.0
```

This runs tests, builds the package, and creates a GitHub release with artifacts.
