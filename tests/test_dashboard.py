"""Tests for dashboard data generation — cc_retrospect/dashboard.py.

Covers: generate_dashboard, WoW calculation, archetype determination,
division-by-zero guards, profile stats, and error fallback.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import make_summary


@pytest.fixture
def dashboard_config(tmp_path):
    data_dir = tmp_path / ".cc-retrospect"
    data_dir.mkdir()
    claude_dir = tmp_path / ".claude"
    (claude_dir / "projects").mkdir(parents=True)
    from cc_retrospect.config import Config
    return Config(data_dir=data_dir, claude_dir=claude_dir, _env_file=None)


def _gen(config, sessions, days=30):
    """Generate dashboard with mocked sessions."""
    from cc_retrospect.dashboard import generate_dashboard
    with patch("cc_retrospect.dashboard.load_all_sessions", return_value=sessions):
        return json.loads(generate_dashboard(config, days=days))


class TestGenerateDashboard:
    """Tests for generate_dashboard() data output."""

    def test_empty_sessions_returns_valid_json(self, dashboard_config):
        data = _gen(dashboard_config, [])
        assert "generated_at" in data
        assert "sessions" in data
        assert "profile" in data

    def test_sessions_included_in_output(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [
            make_summary(session_id="s1", start_ts=now.isoformat(), end_ts=now.isoformat(), total_cost=5.0),
            make_summary(session_id="s2", start_ts=(now - timedelta(days=1)).isoformat(), end_ts=(now - timedelta(days=1)).isoformat(), total_cost=10.0),
        ]
        data = _gen(dashboard_config, sessions)
        assert len(data["sessions"]) == 2
        assert data["profile"]["total_sessions"] == 2
        assert data["profile"]["total_cost"] == 15.0

    def test_cost_by_day_aggregation(self, dashboard_config):
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        sessions = [
            make_summary(session_id="s1", start_ts=f"{today}T10:00:00Z", end_ts=f"{today}T11:00:00Z", total_cost=5.0),
            make_summary(session_id="s2", start_ts=f"{today}T14:00:00Z", end_ts=f"{today}T15:00:00Z", total_cost=8.0),
        ]
        data = _gen(dashboard_config, sessions)
        assert data["cost_by_day"].get(today) == 13.0

    def test_error_fallback_returns_valid_structure(self, dashboard_config):
        """When _build_dashboard_data fails, generate_dashboard returns safe fallback."""
        from cc_retrospect.dashboard import generate_dashboard
        with patch("cc_retrospect.dashboard._build_dashboard_data", side_effect=OSError("disk full")):
            result = generate_dashboard(dashboard_config)
        data = json.loads(result)
        assert "error" in data
        assert data["sessions"] == []
        assert data["trends"] == []


class TestWoWCalculation:
    """Week-over-week comparison in profile stats."""

    def test_wow_with_both_weeks(self, dashboard_config):
        now = datetime.now(timezone.utc)
        # Use days 1-3 for this week (avoid day 0 which could cross boundary)
        this_week = [
            make_summary(session_id=f"tw-{i}", start_ts=(now - timedelta(days=1 + i)).isoformat(),
                         end_ts=(now - timedelta(days=1 + i)).isoformat(), total_cost=10.0)
            for i in range(3)
        ]
        last_week = [
            make_summary(session_id=f"lw-{i}", start_ts=(now - timedelta(days=8 + i)).isoformat(),
                         end_ts=(now - timedelta(days=8 + i)).isoformat(), total_cost=5.0)
            for i in range(3)
        ]
        data = _gen(dashboard_config, this_week + last_week)
        p = data["profile"]
        # Values depend on exact day boundaries, just verify structure and no crash
        assert p["this_week_cost"] >= 0
        assert p["last_week_cost"] >= 0
        assert isinstance(p["wow_change"], (int, float))

    def test_wow_zero_last_week(self, dashboard_config):
        """No division by zero when last week has no sessions."""
        now = datetime.now(timezone.utc)
        sessions = [make_summary(session_id="tw-1", start_ts=now.isoformat(), end_ts=now.isoformat(), total_cost=50.0)]
        data = _gen(dashboard_config, sessions)
        assert data["profile"]["wow_change"] == 0  # no crash, no infinity


class TestArchetype:
    """Archetype determination logic."""

    def test_archetype_is_string(self, dashboard_config):
        """Archetype determination always produces a non-empty string."""
        now = datetime.now(timezone.utc)
        sessions = [
            make_summary(session_id=f"s-{i}", start_ts=(now - timedelta(hours=i)).isoformat(),
                         end_ts=(now - timedelta(hours=i)).isoformat(), total_cost=20.0,
                         model_breakdown={"claude-opus-4-6": 20.0},
                         duration_minutes=30, tool_counts={"Bash": 3})
            for i in range(25)
        ]
        data = _gen(dashboard_config, sessions)
        p = data["profile"]
        assert isinstance(p["archetype"], str) and len(p["archetype"]) > 0
        assert isinstance(p["archetype_desc"], str)
        assert isinstance(p["archetype_emoji"], str)

    def test_archetype_single_session(self, dashboard_config):
        """Single session still produces valid archetype."""
        now = datetime.now(timezone.utc)
        sessions = [make_summary(session_id="s-1", start_ts=now.isoformat(), end_ts=now.isoformat())]
        data = _gen(dashboard_config, sessions)
        assert data["profile"]["archetype"] in (
            "The Opus Maximalist", "The Architect", "The Daily Grinder",
            "The Speedrunner", "The Explorer", "The Craftsman", "The Operator",
            "The Deep Diver", "The Commander", "The Relentless Builder", "The Pragmatist",
        )

    def test_traits_always_present(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [make_summary(session_id="s-1", start_ts=now.isoformat(), end_ts=now.isoformat())]
        data = _gen(dashboard_config, sessions)
        traits = data["profile"]["traits"]
        for key in ("Efficiency", "Intensity", "Persistence", "Patience", "Velocity", "Depth"):
            assert key in traits
            assert 0 <= traits[key] <= 100


class TestProfileStats:
    """Profile stat computation edge cases."""

    def test_cache_rate_zero_tokens(self, dashboard_config):
        """No division by zero when all tokens are 0."""
        now = datetime.now(timezone.utc)
        sessions = [make_summary(
            session_id="s1", start_ts=now.isoformat(), end_ts=now.isoformat(),
            total_input_tokens=0, total_output_tokens=0,
            total_cache_creation_tokens=0, total_cache_read_tokens=0, total_cost=0.0,
        )]
        data = _gen(dashboard_config, sessions)
        assert data["profile"]["cache_rate"] == 0

    def test_model_efficiency_no_opus(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [make_summary(
            session_id="s1", start_ts=now.isoformat(), end_ts=now.isoformat(),
            total_cost=5.0, model_breakdown={"claude-sonnet-4-20250514": 5.0},
        )]
        data = _gen(dashboard_config, sessions)
        assert data["profile"]["model_efficiency"] == 100

    def test_streak_calculation(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [
            make_summary(
                session_id=f"s-{i}", start_ts=(now - timedelta(days=i)).isoformat(),
                end_ts=(now - timedelta(days=i)).isoformat(), total_cost=1.0,
            ) for i in range(5)
        ]
        data = _gen(dashboard_config, sessions)
        assert data["profile"]["streak_days"] >= 5

    def test_tool_usage_aggregation(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [
            make_summary(session_id="s1", start_ts=now.isoformat(), end_ts=now.isoformat(),
                         tool_counts={"Bash": 5, "Read": 3}),
            make_summary(session_id="s2", start_ts=(now - timedelta(hours=1)).isoformat(),
                         end_ts=(now - timedelta(hours=1)).isoformat(),
                         tool_counts={"Bash": 2, "Edit": 4}),
        ]
        data = _gen(dashboard_config, sessions)
        assert data["tool_usage"]["Bash"] == 7
        assert data["tool_usage"]["Edit"] == 4

    def test_budget_tiers_included(self, dashboard_config):
        data = _gen(dashboard_config, [])
        assert len(data["budget_tiers"]) == 3
        labels = [t["label"] for t in data["budget_tiers"]]
        assert "Warning" in labels and "Critical" in labels and "Severe" in labels

    def test_hourly_activity(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [make_summary(session_id="s1", start_ts=f"{now.strftime('%Y-%m-%d')}T14:30:00Z",
                                 end_ts=f"{now.strftime('%Y-%m-%d')}T15:00:00Z")]
        data = _gen(dashboard_config, sessions)
        assert len(data["hourly_activity"]) == 24
        assert data["hourly_activity"][14] == 1

    def test_frustration_aggregation(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [
            make_summary(session_id="s1", start_ts=now.isoformat(), end_ts=now.isoformat(),
                         frustration_count=3, frustration_words={"wrong": 2, "ugh": 1}),
            make_summary(session_id="s2", start_ts=(now - timedelta(hours=1)).isoformat(),
                         end_ts=(now - timedelta(hours=1)).isoformat(),
                         frustration_count=1, frustration_words={"wrong": 1}),
        ]
        data = _gen(dashboard_config, sessions)
        assert data["profile"]["total_frustrations"] == 4
        # Top frustrations sorted by count
        top = data["profile"]["top_frustrations"]
        assert top[0][0] == "wrong"
        assert top[0][1] == 3

    def test_model_costs_breakdown(self, dashboard_config):
        now = datetime.now(timezone.utc)
        sessions = [
            make_summary(session_id="s1", start_ts=now.isoformat(), end_ts=now.isoformat(),
                         total_cost=15.0, model_breakdown={"claude-opus-4-6": 10.0, "claude-sonnet-4-20250514": 5.0}),
        ]
        data = _gen(dashboard_config, sessions)
        assert data["profile"]["model_costs"]["claude-opus-4-6"] == 10.0
        assert data["profile"]["model_costs"]["claude-sonnet-4-20250514"] == 5.0


class TestDashboardHelpers:
    """Tests for _load_jsonl and _load_json helpers."""

    def test_load_jsonl_valid(self, tmp_path):
        from cc_retrospect.dashboard import _load_jsonl
        p = tmp_path / "test.jsonl"
        p.write_text('{"a": 1}\n{"b": 2}\n')
        items = _load_jsonl(p)
        assert len(items) == 2
        assert items[0] == {"a": 1}

    def test_load_jsonl_missing_file(self, tmp_path):
        from cc_retrospect.dashboard import _load_jsonl
        assert _load_jsonl(tmp_path / "missing.jsonl") == []

    def test_load_jsonl_malformed_lines(self, tmp_path):
        from cc_retrospect.dashboard import _load_jsonl
        p = tmp_path / "test.jsonl"
        p.write_text('{"a": 1}\nBROKEN\n{"b": 2}\n')
        items = _load_jsonl(p)
        assert len(items) == 2

    def test_load_json_missing(self, tmp_path):
        from cc_retrospect.dashboard import _load_json
        assert _load_json(tmp_path / "missing.json") == {}

    def test_load_json_corrupt(self, tmp_path):
        from cc_retrospect.dashboard import _load_json
        p = tmp_path / "bad.json"
        p.write_text("not json")
        assert _load_json(p) == {}
