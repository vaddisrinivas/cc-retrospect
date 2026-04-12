"""Tests for cc_retrospect/utils.py — formatting, filtering, and rendering helpers."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import make_summary


class TestFmtTokens:
    def test_billions(self):
        from cc_retrospect.utils import _fmt_tokens
        assert _fmt_tokens(2_500_000_000) == "2.50B"

    def test_millions(self):
        from cc_retrospect.utils import _fmt_tokens
        assert _fmt_tokens(1_500_000) == "1.5M"

    def test_thousands(self):
        from cc_retrospect.utils import _fmt_tokens
        assert _fmt_tokens(50_000) == "50.0K"

    def test_small(self):
        from cc_retrospect.utils import _fmt_tokens
        assert _fmt_tokens(999) == "999"

    def test_zero(self):
        from cc_retrospect.utils import _fmt_tokens
        assert _fmt_tokens(0) == "0"


class TestFmtCost:
    def test_thousands(self):
        from cc_retrospect.utils import _fmt_cost
        assert _fmt_cost(1234.56) == "$1,235"

    def test_dollars(self):
        from cc_retrospect.utils import _fmt_cost
        assert _fmt_cost(12.50) == "$12.50"

    def test_cents(self):
        from cc_retrospect.utils import _fmt_cost
        assert _fmt_cost(0.0042) == "$0.0042"

    def test_zero(self):
        from cc_retrospect.utils import _fmt_cost
        assert _fmt_cost(0) == "$0.0000"


class TestFmtDuration:
    def test_hours(self):
        from cc_retrospect.utils import _fmt_duration
        assert _fmt_duration(125) == "2h 5m"

    def test_minutes(self):
        from cc_retrospect.utils import _fmt_duration
        assert _fmt_duration(45) == "45m"

    def test_zero(self):
        from cc_retrospect.utils import _fmt_duration
        assert _fmt_duration(0) == "0m"


class TestDisplayProject:
    def test_strips_prefix(self):
        from cc_retrospect.utils import display_project
        assert display_project("-Users-test-Projects-myapp") == "myapp"

    def test_no_prefix(self):
        from cc_retrospect.utils import display_project
        assert display_project("myapp") == "myapp"

    def test_empty(self):
        from cc_retrospect.utils import display_project
        result = display_project("")
        assert isinstance(result, str)


class TestGroup:
    def test_groups_by_project(self):
        from cc_retrospect.utils import _group
        sessions = [
            make_summary(session_id="s1", project="projA", total_cost=5.0),
            make_summary(session_id="s2", project="projB", total_cost=3.0),
            make_summary(session_id="s3", project="projA", total_cost=7.0),
        ]
        result = _group(sessions, lambda s: s.project)
        assert result["projA"] == 12.0
        assert result["projB"] == 3.0

    def test_custom_val_fn(self):
        from cc_retrospect.utils import _group
        sessions = [
            make_summary(session_id="s1", project="p", message_count=10),
            make_summary(session_id="s2", project="p", message_count=20),
        ]
        result = _group(sessions, lambda s: s.project, val_fn=lambda s: s.message_count)
        assert result["p"] == 30


class TestTop:
    def test_sorts_descending(self):
        from cc_retrospect.utils import _top
        d = {"a": 10, "b": 30, "c": 20}
        result = _top(d)
        assert result[0] == ("b", 30)

    def test_limits_to_n(self):
        from cc_retrospect.utils import _top
        d = {str(i): i for i in range(20)}
        result = _top(d, n=5)
        assert len(result) == 5


class TestFilterSessions:
    def test_filter_by_project(self):
        from cc_retrospect.utils import _filter_sessions
        sessions = [
            make_summary(session_id="s1", project="-Users-test-Projects-myapp"),
            make_summary(session_id="s2", project="-Users-test-Projects-other"),
        ]
        result = _filter_sessions(sessions, project="myapp")
        assert len(result) == 1

    def test_filter_by_days(self):
        from cc_retrospect.utils import _filter_sessions
        now = datetime.now(timezone.utc)
        sessions = [
            make_summary(session_id="s1", start_ts=now.isoformat()),
            make_summary(session_id="s2", start_ts=(now - timedelta(days=10)).isoformat()),
        ]
        result = _filter_sessions(sessions, days=7)
        assert len(result) == 1

    def test_filter_by_config_exclude_project(self):
        from cc_retrospect.utils import _filter_sessions
        from cc_retrospect.config import Config, FilterConfig
        cfg = Config(filter=FilterConfig(exclude_projects=["secret"]), _env_file=None)
        sessions = [
            make_summary(session_id="s1", project="-Users-test-Projects-myapp"),
            make_summary(session_id="s2", project="-Users-test-Projects-secret-stuff"),
        ]
        result = _filter_sessions(sessions, config=cfg)
        assert len(result) == 1

    def test_filter_by_min_duration(self):
        from cc_retrospect.utils import _filter_sessions
        from cc_retrospect.config import Config, FilterConfig
        cfg = Config(filter=FilterConfig(exclude_sessions_shorter_than=30), _env_file=None)
        sessions = [
            make_summary(session_id="s1", duration_minutes=60),
            make_summary(session_id="s2", duration_minutes=10),
        ]
        result = _filter_sessions(sessions, config=cfg)
        assert len(result) == 1

    def test_no_filters(self):
        from cc_retrospect.utils import _filter_sessions
        sessions = [make_summary(), make_summary(session_id="s2")]
        result = _filter_sessions(sessions)
        assert len(result) == 2


class TestRender:
    def test_render_returns_zero(self, capsys):
        from cc_retrospect.utils import _render
        from cc_retrospect.analyzers import CostAnalyzer
        sessions = [make_summary()]
        result = _render(CostAnalyzer, {}, sessions=sessions)
        assert result == 0
        out = capsys.readouterr().out
        assert "Cost Analysis" in out

    def test_render_json_mode(self, capsys):
        from cc_retrospect.utils import _render
        from cc_retrospect.analyzers import CostAnalyzer
        sessions = [make_summary()]
        result = _render(CostAnalyzer, {"json": True}, sessions=sessions)
        assert result == 0
        import json
        data = json.loads(capsys.readouterr().out)
        assert data["title"] == "Cost Analysis"
