"""Integration tests against REAL local session data.

These tests use ~/.claude/projects/ and ~/.cc-retrospect/ — they validate
that the plugin actually produces correct results on real data, not just
fixtures. Skip if no session data exists.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REAL_CLAUDE_DIR = Path.home() / ".claude"
REAL_DATA_DIR = Path.home() / ".cc-retrospect"
HAS_REAL_DATA = (REAL_CLAUDE_DIR / "projects").is_dir() and any((REAL_CLAUDE_DIR / "projects").iterdir())

pytestmark = pytest.mark.skipif(not HAS_REAL_DATA, reason="No real Claude Code session data on this machine")


class TestRealDataLoading:
    """Verify session loading against actual ~/.claude/projects/."""

    def test_loads_sessions(self):
        from cc_retrospect.core import load_all_sessions, default_config
        sessions = load_all_sessions(default_config())
        assert len(sessions) > 100, f"Expected 100+ sessions, got {len(sessions)}"

    def test_sessions_have_valid_fields(self):
        from cc_retrospect.core import load_all_sessions, default_config
        sessions = load_all_sessions(default_config())
        for s in sessions[:50]:
            assert s.session_id, "session_id should not be empty"
            assert s.project, "project should not be empty"
            assert s.message_count >= 0
            assert s.total_cost >= 0
            assert isinstance(s.tool_counts, dict)
            assert isinstance(s.model_breakdown, dict)

    def test_total_cost_is_positive(self):
        from cc_retrospect.core import load_all_sessions, default_config
        sessions = load_all_sessions(default_config())
        total = sum(s.total_cost for s in sessions)
        assert total > 100, f"Expected significant cost, got ${total:.2f}"

    def test_multiple_projects_found(self):
        from cc_retrospect.core import load_all_sessions, default_config
        sessions = load_all_sessions(default_config())
        projects = set(s.project for s in sessions)
        assert len(projects) >= 5, f"Expected 5+ projects, got {len(projects)}"

    def test_multiple_models_found(self):
        from cc_retrospect.core import load_all_sessions, default_config
        sessions = load_all_sessions(default_config())
        models = set()
        for s in sessions:
            models.update(s.model_breakdown.keys())
        assert len(models) >= 2, f"Expected 2+ models, got {models}"


class TestRealAnalyzers:
    """Run every analyzer against real data and verify output structure."""

    def _run_analyzer(self, cls_name):
        from cc_retrospect import core
        cls = getattr(core, cls_name)
        sessions = core.load_all_sessions(core.default_config())
        result = cls().analyze(sessions, core.default_config())
        assert result.title
        return result

    def test_cost_analyzer(self):
        result = self._run_analyzer("CostAnalyzer")
        assert len(result.sections) >= 2  # Totals + By Project at minimum
        # Should find cost data
        all_rows = [(label, val) for s in result.sections for label, val in s.rows]
        cost_row = next((v for l, v in all_rows if "Total cost" in l), None)
        assert cost_row and "$" in cost_row

    def test_waste_analyzer(self):
        result = self._run_analyzer("WasteAnalyzer")
        assert len(result.recommendations) > 0  # Real data should have some waste

    def test_habits_analyzer(self):
        result = self._run_analyzer("HabitsAnalyzer")
        assert any("Peak" in s.header for s in result.sections)
        assert any("Tool" in s.header for s in result.sections)

    def test_health_analyzer(self):
        result = self._run_analyzer("HealthAnalyzer")
        assert any("Long sessions" in r[0] for s in result.sections for r in s.rows)

    def test_tips_analyzer(self):
        result = self._run_analyzer("TipsAnalyzer")
        assert len(result.recommendations) > 0

    def test_compare_analyzer(self):
        result = self._run_analyzer("CompareAnalyzer")
        assert result.title == "This Week vs Last Week"

    def test_savings_analyzer(self):
        result = self._run_analyzer("SavingsAnalyzer")
        assert any("projection" in r[0].lower() for s in result.sections for r in s.rows)
        assert len(result.recommendations) > 0  # Should suggest something

    def test_model_analyzer(self):
        result = self._run_analyzer("ModelAnalyzer")
        assert any("efficiency" in r[0].lower() for s in result.sections for r in s.rows)


class TestRealDispatchCommands:
    """Run dispatch commands as subprocesses and verify they don't crash."""

    def _dispatch(self, cmd, timeout=30):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "dispatch.py"), cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return result

    def test_cost(self):
        r = self._dispatch("cost")
        assert r.returncode == 0
        assert "Cost Analysis" in r.stdout

    def test_habits(self):
        r = self._dispatch("habits")
        assert r.returncode == 0
        assert "Usage Habits" in r.stdout

    def test_health(self):
        r = self._dispatch("health")
        assert r.returncode == 0
        assert "Health Check" in r.stdout

    def test_waste(self):
        r = self._dispatch("waste")
        assert r.returncode == 0
        assert "Waste" in r.stdout

    def test_tips(self):
        r = self._dispatch("tips")
        assert r.returncode == 0

    def test_compare(self):
        r = self._dispatch("compare")
        assert r.returncode == 0

    def test_savings(self):
        r = self._dispatch("savings")
        assert r.returncode == 0
        assert "Savings" in r.stdout

    def test_model(self):
        r = self._dispatch("model")
        assert r.returncode == 0
        assert "Model Efficiency" in r.stdout

    def test_digest(self):
        r = self._dispatch("digest")
        assert r.returncode == 0

    def test_status(self):
        r = self._dispatch("status")
        assert r.returncode == 0
        assert "Status" in r.stdout
        assert "pydantic" in r.stdout

    def test_export(self):
        r = self._dispatch("export")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) > 100

    def test_hints(self):
        r = self._dispatch("hints")
        assert r.returncode == 0
        assert "HINTS__" in r.stdout

    def test_trends(self):
        r = self._dispatch("trends")
        assert r.returncode == 0

    def test_report(self):
        r = self._dispatch("report", timeout=60)
        assert r.returncode == 0
        assert "Report saved to" in r.stdout


class TestRealDataConsistency:
    """Cross-validate analyzer outputs against each other."""

    def test_cost_matches_export(self):
        """Total cost from CostAnalyzer should match sum of exported sessions."""
        from cc_retrospect.core import load_all_sessions, CostAnalyzer, default_config
        cfg = default_config()
        sessions = load_all_sessions(cfg)
        result = CostAnalyzer().analyze(sessions, cfg)
        # Extract total cost from result
        for s in result.sections:
            for label, value in s.rows:
                if "Total cost" in label:
                    analyzer_cost = float(value.replace("$", "").replace(",", ""))
                    export_cost = sum(s.total_cost for s in sessions)
                    assert abs(analyzer_cost - export_cost) < 1.0, f"Analyzer: ${analyzer_cost}, Export: ${export_cost}"
                    return
        pytest.fail("No 'Total cost' row found in CostAnalyzer output")

    def test_model_efficiency_is_reasonable(self):
        """Model efficiency score should be between 0 and 100."""
        from cc_retrospect.core import load_all_sessions, ModelAnalyzer, default_config
        cfg = default_config()
        sessions = load_all_sessions(cfg)
        result = ModelAnalyzer().analyze(sessions, cfg)
        for s in result.sections:
            for label, value in s.rows:
                if "efficiency" in label.lower():
                    score = int(value.rstrip("%"))
                    assert 0 <= score <= 100, f"Efficiency score out of range: {score}"
                    return

    def test_savings_doesnt_exceed_total_cost(self):
        """Monthly savings projection shouldn't exceed monthly cost projection."""
        from cc_retrospect.core import load_all_sessions, SavingsAnalyzer, default_config
        cfg = default_config()
        sessions = load_all_sessions(cfg)
        result = SavingsAnalyzer().analyze(sessions, cfg)
        monthly_cost = monthly_savings = 0
        for s in result.sections:
            for label, value in s.rows:
                if "Current monthly projection" in label:
                    monthly_cost = float(value.replace("$", "").replace(",", ""))
                if "Total potential monthly savings" in label:
                    monthly_savings = float(value.replace("$", "").replace(",", ""))
        if monthly_cost > 0 and monthly_savings > 0:
            assert monthly_savings <= monthly_cost, f"Savings ${monthly_savings} > cost ${monthly_cost}"

    def test_waste_webfetch_count_matches_sessions(self):
        """WebFetch waste count should match sum using the configured waste domains."""
        from cc_retrospect.core import load_all_sessions, WasteAnalyzer, default_config
        cfg = default_config()
        sessions = load_all_sessions(cfg)
        # Count using the same logic as WasteAnalyzer: only configured waste domains
        actual_wf = sum(
            sum(c for d, c in s.webfetch_domains.items()
                if any(wd in d for wd in cfg.thresholds.waste_webfetch_domains))
            for s in sessions
        )
        result = WasteAnalyzer().analyze(sessions, cfg)
        for s in result.sections:
            for label, value in s.rows:
                if "WebFetch" in label:
                    reported = int(value)
                    assert reported == actual_wf, f"Reported: {reported}, Actual: {actual_wf}"
                    return

    def test_session_count_consistent(self):
        """All analyzers should see the same session count."""
        from cc_retrospect.core import load_all_sessions, CostAnalyzer, HabitsAnalyzer, default_config
        cfg = default_config()
        sessions = load_all_sessions(cfg)
        cost_result = CostAnalyzer().analyze(sessions, cfg)
        habits_result = HabitsAnalyzer().analyze(sessions, cfg)
        cost_count = habits_count = 0
        for s in cost_result.sections:
            for label, value in s.rows:
                if "Sessions" == label.strip():
                    cost_count = int(value)
        for s in habits_result.sections:
            for label, value in s.rows:
                if "Total sessions" == label.strip():
                    habits_count = int(value)
        assert cost_count == habits_count == len(sessions)
