"""Shared fixtures and helpers for cc-retrospect tests.

Consolidates duplicated helpers from test_core_detectors, test_new_features,
test_full_coverage, and test_integration into a single source of truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

def make_summary(**overrides):
    """Create a SessionSummary with sensible defaults. Override any field via kwargs."""
    from cc_retrospect.core import SessionSummary
    defaults = dict(
        session_id="test-sess",
        project="testproj",
        start_ts="2026-04-05T10:00:00Z",
        end_ts="2026-04-05T11:00:00Z",
        duration_minutes=60.0,
        message_count=50,
        user_message_count=20,
        assistant_message_count=30,
        total_input_tokens=100_000,
        total_output_tokens=50_000,
        total_cache_creation_tokens=500_000,
        total_cache_read_tokens=5_000_000,
        total_cost=10.0,
        model_breakdown={"claude-opus-4-6": 10.0},
        tool_counts={"Bash": 5},
        tool_chains=[],
        subagent_count=0,
        mega_prompt_count=0,
        frustration_count=0,
        frustration_words={},
        webfetch_domains={},
        entrypoint="claude-desktop",
        cwd="/test",
        git_branch="main",
    )
    defaults.update(overrides)
    return SessionSummary(**defaults)


# ---------------------------------------------------------------------------
# JSONL message builders (for integration tests)
# ---------------------------------------------------------------------------

def build_assistant_msg(session_id: str, ts: str, model: str = "claude-opus-4-6",
                        input_tokens: int = 1000, output_tokens: int = 100,
                        tool_name: str | None = None) -> str:
    """Build a JSON string for an assistant message in a JSONL session file."""
    content = [{"type": "text", "text": "ok"}]
    if tool_name:
        content = [{"type": "tool_use", "id": "tu1", "name": tool_name, "input": {}}]
    return json.dumps({
        "type": "assistant",
        "sessionId": session_id,
        "timestamp": ts,
        "entrypoint": "claude-desktop",
        "cwd": "/test",
        "gitBranch": "main",
        "message": {
            "model": model,
            "id": "msg_x",
            "role": "assistant",
            "content": content,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    })


def build_user_msg(session_id: str, ts: str, text: str) -> str:
    """Build a JSON string for a user message in a JSONL session file."""
    return json.dumps({
        "type": "user",
        "sessionId": session_id,
        "timestamp": ts,
        "message": {"role": "user", "content": text},
    })


# ---------------------------------------------------------------------------
# Directory builders
# ---------------------------------------------------------------------------

def build_claude_dir(base: Path) -> Path:
    """Create a simulated ~/.claude directory under *base*."""
    d = base / ".claude"
    (d / "projects").mkdir(parents=True)
    return d


def write_session(projects_dir: Path, proj_name: str, session_id: str, lines: list[str]) -> Path:
    """Write a JSONL session file and return its path."""
    proj_dir = projects_dir / proj_name
    proj_dir.mkdir(parents=True, exist_ok=True)
    path = proj_dir / f"{session_id}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data dir for cc-retrospect state."""
    d = tmp_path / ".cc-retrospect"
    d.mkdir()
    return d


@pytest.fixture
def tmp_claude_dir(tmp_path):
    """Create a simulated ~/.claude directory."""
    return build_claude_dir(tmp_path)


@pytest.fixture
def config(tmp_data_dir):
    """Config pointing at a temporary data dir (no env file)."""
    from cc_retrospect.core import Config
    return Config(data_dir=tmp_data_dir, _env_file=None)


@pytest.fixture
def tmp_env(tmp_path):
    """Complete test environment: data_dir + claude_dir + config."""
    data_dir = tmp_path / ".cc-retrospect"
    data_dir.mkdir()
    claude_dir = build_claude_dir(tmp_path)
    from cc_retrospect.core import Config
    cfg = Config(data_dir=data_dir, claude_dir=claude_dir, _env_file=None)
    return {"data_dir": data_dir, "claude_dir": claude_dir, "config": cfg}
