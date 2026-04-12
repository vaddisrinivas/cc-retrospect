"""Tests for tool call history — /api/toolcalls endpoint and script generation logic.

Exercises: real tool calls from the user's session cache + script generation
from selected calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cc_retrospect.models import ToolCall
from tests.conftest import make_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_session_with_calls(*call_specs, **overrides):
    """Build a SessionSummary with ToolCall objects.

    call_specs: dicts with keys: name, input_summary, output_snippet, is_error, ts
    """
    calls = [ToolCall(**{
        "name": spec.get("name", "Bash"),
        "input_summary": spec.get("input_summary", ""),
        "output_snippet": spec.get("output_snippet", ""),
        "is_error": spec.get("is_error", False),
        "ts": spec.get("ts", "2026-04-11T10:00:00Z"),
    }) for spec in call_specs]
    return make_summary(tool_calls=calls, **overrides)


# ---------------------------------------------------------------------------
# Unit: ToolCall model
# ---------------------------------------------------------------------------

class TestToolCallModel:
    def test_defaults(self):
        tc = ToolCall()
        assert tc.name == ""
        assert tc.is_error is False

    def test_fields_round_trip(self):
        tc = ToolCall(
            name="Edit",
            input_summary='{"file_path": "foo.py"}',
            output_snippet="ok",
            is_error=False,
            ts="2026-04-11T12:00:00Z",
        )
        d = tc.model_dump()
        assert d["name"] == "Edit"
        assert d["ts"] == "2026-04-11T12:00:00Z"

    def test_error_flag(self):
        tc = ToolCall(name="Bash", is_error=True)
        assert tc.is_error is True


# ---------------------------------------------------------------------------
# Unit: SessionSummary with tool_calls field
# ---------------------------------------------------------------------------

class TestSessionToolCalls:
    def test_session_carries_tool_calls(self):
        s = make_session_with_calls(
            {"name": "Bash", "input_summary": "git status"},
            {"name": "Edit", "input_summary": "fix typo"},
        )
        assert len(s.tool_calls) == 2
        assert s.tool_calls[0].name == "Bash"
        assert s.tool_calls[1].name == "Edit"

    def test_session_defaults_empty_tool_calls(self):
        s = make_summary()
        # tool_calls not in make_summary defaults — should be [] or None
        assert (s.tool_calls or []) == []

    def test_tool_calls_serializes(self):
        s = make_session_with_calls({"name": "Read", "input_summary": "main.py"})
        data = json.loads(s.model_dump_json())
        assert data["tool_calls"][0]["name"] == "Read"


# ---------------------------------------------------------------------------
# Unit: filter logic (mirrors /api/toolcalls endpoint)
# ---------------------------------------------------------------------------

def _collect_calls(sessions, tool_filter=None, error_only=False):
    """Mirror the server's _get_toolcalls filtering logic."""
    recent = sorted(
        [s for s in sessions if getattr(s, "tool_calls", None)],
        key=lambda s: s.start_ts or "", reverse=True,
    )[:200]
    all_calls = []
    for s in recent:
        for tc in (getattr(s, "tool_calls", None) or []):
            if tool_filter and tc.name != tool_filter:
                continue
            if error_only and not tc.is_error:
                continue
            all_calls.append({
                "name": tc.name,
                "input_summary": (tc.input_summary or "")[:200],
                "output_snippet": (tc.output_snippet or "")[:100],
                "is_error": tc.is_error,
                "ts": tc.ts,
                "session_id": s.session_id,
                "project": s.project,
            })
    all_calls.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return all_calls


class TestToolCallFiltering:
    def setup_method(self):
        self.sessions = [
            make_session_with_calls(
                {"name": "Bash", "input_summary": "make test", "ts": "2026-04-11T09:00:00Z"},
                {"name": "Edit", "input_summary": "fix.py", "ts": "2026-04-11T09:01:00Z"},
                session_id="s1", start_ts="2026-04-11T09:00:00Z",
            ),
            make_session_with_calls(
                {"name": "Bash", "input_summary": "git push", "ts": "2026-04-10T08:00:00Z"},
                {"name": "Read", "input_summary": "readme.md", "is_error": True, "ts": "2026-04-10T08:01:00Z"},
                session_id="s2", start_ts="2026-04-10T08:00:00Z",
            ),
        ]

    def test_no_filter_returns_all(self):
        calls = _collect_calls(self.sessions)
        assert len(calls) == 4

    def test_tool_filter_by_name(self):
        calls = _collect_calls(self.sessions, tool_filter="Bash")
        assert all(c["name"] == "Bash" for c in calls)
        assert len(calls) == 2

    def test_error_only_filter(self):
        calls = _collect_calls(self.sessions, error_only=True)
        assert len(calls) == 1
        assert calls[0]["is_error"] is True
        assert calls[0]["name"] == "Read"

    def test_sorted_by_ts_desc(self):
        calls = _collect_calls(self.sessions)
        ts_list = [c["ts"] for c in calls]
        assert ts_list == sorted(ts_list, reverse=True)

    def test_project_attached(self):
        calls = _collect_calls(self.sessions)
        projects = {c["project"] for c in calls}
        assert "testproj" in projects

    def test_input_truncated(self):
        long_input = "x" * 300
        sessions = [make_session_with_calls(
            {"name": "Bash", "input_summary": long_input}
        )]
        calls = _collect_calls(sessions)
        assert len(calls[0]["input_summary"]) <= 200


# ---------------------------------------------------------------------------
# Unit: script generation (mirrors generateScriptLocally JS logic in Python)
# ---------------------------------------------------------------------------

def generate_script_from_calls(calls: list[dict], user_prompt: str = "") -> str:
    """Python port of the JS generateScriptLocally() for testing."""
    lines = [
        "#!/usr/bin/env bash",
        "# Auto-generated by cc-retrospect Magic Create",
        f"# calls: {len(calls)}",
        "",
        "set -euo pipefail",
        "",
    ]

    bash_calls = [c for c in calls if c["name"] == "Bash"]
    edit_calls = [c for c in calls if c["name"] == "Edit"]
    read_calls = [c for c in calls if c["name"] == "Read"]

    if bash_calls:
        lines.append("# === Bash Commands ===")
        for c in bash_calls:
            cmd = (c["input_summary"] or "").replace("command: ", "", 1)
            if cmd:
                lines.append(cmd)
        lines.append("")

    if read_calls:
        lines.append("# === Files Referenced ===")
        for c in read_calls:
            lines.append("# " + (c["input_summary"] or "")[:100])
        lines.append("")

    if edit_calls:
        lines.append("# === Edits Applied ===")
        for c in edit_calls:
            lines.append("# " + (c["input_summary"] or "")[:100])
        lines.append("")

    if not bash_calls and not edit_calls and not read_calls:
        lines.append("# Tool calls:")
        for c in calls:
            lines.append(f"# {c['name']}: {(c['input_summary'] or '')[:80]}")

    lines.append('echo "Done."')
    return "\n".join(lines)


class TestScriptGeneration:
    def test_bash_commands_included(self):
        calls = [{"name": "Bash", "input_summary": "make test"}]
        script = generate_script_from_calls(calls)
        assert "make test" in script
        assert "#!/usr/bin/env bash" in script

    def test_shebang_and_set_e(self):
        calls = [{"name": "Bash", "input_summary": "echo hi"}]
        script = generate_script_from_calls(calls)
        assert script.startswith("#!/usr/bin/env bash")
        assert "set -euo pipefail" in script

    def test_edit_calls_as_comments(self):
        calls = [{"name": "Edit", "input_summary": "fix auth.py"}]
        script = generate_script_from_calls(calls)
        assert "# fix auth.py" in script
        assert "Edits Applied" in script

    def test_read_calls_as_comments(self):
        calls = [{"name": "Read", "input_summary": "config.yaml"}]
        script = generate_script_from_calls(calls)
        assert "# config.yaml" in script
        assert "Files Referenced" in script

    def test_unknown_tool_falls_back(self):
        calls = [{"name": "WebFetch", "input_summary": "https://example.com"}]
        script = generate_script_from_calls(calls)
        assert "WebFetch" in script
        assert "Tool calls" in script

    def test_empty_calls(self):
        script = generate_script_from_calls([])
        assert "#!/usr/bin/env bash" in script
        assert 'echo "Done."' in script

    def test_mixed_calls_ordering(self):
        calls = [
            {"name": "Read", "input_summary": "setup.py"},
            {"name": "Bash", "input_summary": "pip install -e ."},
            {"name": "Edit", "input_summary": "fix import"},
        ]
        script = generate_script_from_calls(calls)
        bash_pos = script.index("pip install -e .")
        read_pos = script.index("# setup.py")
        edit_pos = script.index("# fix import")
        # Bash section first, then Read, then Edit
        assert bash_pos < read_pos < edit_pos

    def test_call_count_in_header(self):
        calls = [
            {"name": "Bash", "input_summary": "cmd1"},
            {"name": "Bash", "input_summary": "cmd2"},
            {"name": "Edit", "input_summary": "f.py"},
        ]
        script = generate_script_from_calls(calls)
        assert "calls: 3" in script


# ---------------------------------------------------------------------------
# Integration: real session cache → script
# ---------------------------------------------------------------------------

class TestRealDataScriptGeneration:
    """Uses actual session data from the user's cache."""

    def test_real_bash_calls_produce_script(self):
        from cc_retrospect.config import load_config
        from cc_retrospect.cache import load_all_sessions

        cfg = load_config()
        sessions = load_all_sessions(cfg)
        # Grab first session with bash tool calls
        bash_sessions = [
            s for s in sessions
            if any(tc.name == "Bash" for tc in (getattr(s, "tool_calls", None) or []))
        ]
        if not bash_sessions:
            pytest.skip("No sessions with Bash tool calls in cache")

        s = bash_sessions[0]
        bash_calls = [
            {"name": tc.name, "input_summary": tc.input_summary}
            for tc in s.tool_calls if tc.name == "Bash"
        ][:5]

        script = generate_script_from_calls(bash_calls)
        assert "#!/usr/bin/env bash" in script
        assert "Bash Commands" in script
        assert 'echo "Done."' in script
        # At least one bash command from the actual session
        assert any(c["input_summary"][:20] in script for c in bash_calls if c["input_summary"])

    def test_real_mixed_calls_produce_script(self):
        from cc_retrospect.config import load_config
        from cc_retrospect.cache import load_all_sessions

        cfg = load_config()
        sessions = load_all_sessions(cfg)

        # Find a session with both Bash + Edit calls
        mixed = [
            s for s in sessions
            if (
                any(tc.name == "Bash" for tc in (getattr(s, "tool_calls", None) or []))
                and any(tc.name == "Edit" for tc in (getattr(s, "tool_calls", None) or []))
            )
        ]
        if not mixed:
            pytest.skip("No sessions with both Bash + Edit in cache")

        s = mixed[0]
        calls = [
            {"name": tc.name, "input_summary": tc.input_summary, "output_snippet": tc.output_snippet}
            for tc in s.tool_calls[:10]
        ]

        script = generate_script_from_calls(calls)
        assert "#!/usr/bin/env bash" in script
        assert 'echo "Done."' in script
        print(f"\n--- Script from session {s.session_id[:12]} ({s.project}) ---")
        print(script[:600])

    def test_filter_then_generate(self):
        """Full pipeline: load real sessions → filter to Bash only → generate script."""
        from cc_retrospect.config import load_config
        from cc_retrospect.cache import load_all_sessions

        cfg = load_config()
        sessions = load_all_sessions(cfg)
        calls = _collect_calls(sessions, tool_filter="Bash")[:10]

        if not calls:
            pytest.skip("No Bash calls in cache")

        script = generate_script_from_calls(calls)
        assert "#!/usr/bin/env bash" in script
        assert "Bash Commands" in script
        # Every Bash input should appear in script
        for c in calls[:3]:
            if c["input_summary"]:
                snippet = c["input_summary"][:20]
                assert snippet in script, f"Expected '{snippet}' in script"
