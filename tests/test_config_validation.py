"""Tests for cc_retrospect/config.py — config loading, validation, and defaults."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestConfigDefaults:
    """All config fields have sensible defaults without env file."""

    def test_default_config_loads(self):
        from cc_retrospect.config import default_config
        cfg = default_config()
        assert cfg.pricing.opus.input_per_mtok == 5.0
        assert cfg.pricing.sonnet.input_per_mtok == 3.0
        assert cfg.pricing.haiku.input_per_mtok == 1.0

    def test_thresholds_defaults(self):
        from cc_retrospect.config import default_config
        cfg = default_config()
        assert cfg.thresholds.long_session_minutes == 90
        assert cfg.thresholds.long_session_messages == 150
        assert cfg.thresholds.tool_chain_threshold == 5
        assert cfg.thresholds.max_subagents_per_session == 8

    def test_hints_defaults(self):
        from cc_retrospect.config import default_config
        cfg = default_config()
        assert cfg.hints.session_start is True
        assert cfg.hints.pre_tool is True
        assert cfg.hints.post_tool is True
        assert cfg.hints.user_prompt is True

    def test_budget_defaults(self):
        from cc_retrospect.config import default_config
        cfg = default_config()
        assert cfg.budget.warning.threshold == 100.0
        assert cfg.budget.critical.threshold == 300.0
        assert cfg.budget.severe.threshold == 500.0

    def test_filter_defaults(self):
        from cc_retrospect.config import default_config
        cfg = default_config()
        assert "cc-retrospect" in cfg.filter.exclude_entrypoints

    def test_messages_prefix(self):
        from cc_retrospect.config import default_config
        cfg = default_config()
        assert cfg.messages.prefix == "[cc-retrospect]"

    def test_data_dir_default(self):
        from cc_retrospect.config import default_config
        cfg = default_config()
        assert cfg.data_dir == Path.home() / ".cc-retrospect"


class TestConfigFromEnvFile:
    """Config loads overrides from a config.env file."""

    def test_pricing_override(self, tmp_path):
        from cc_retrospect.config import Config
        env_file = tmp_path / "config.env"
        env_file.write_text("PRICING__OPUS__INPUT_PER_MTOK=20.0\n")
        cfg = Config(_env_file=str(env_file))
        assert cfg.pricing.opus.input_per_mtok == 20.0
        # Others untouched
        assert cfg.pricing.sonnet.input_per_mtok == 3.0

    def test_threshold_override(self, tmp_path):
        from cc_retrospect.config import Config
        env_file = tmp_path / "config.env"
        env_file.write_text("THRESHOLDS__LONG_SESSION_MINUTES=120\n")
        cfg = Config(_env_file=str(env_file))
        assert cfg.thresholds.long_session_minutes == 120

    def test_budget_override(self, tmp_path):
        from cc_retrospect.config import Config
        env_file = tmp_path / "config.env"
        env_file.write_text("BUDGET__WARNING__THRESHOLD=75\n")
        cfg = Config(_env_file=str(env_file))
        assert cfg.budget.warning.threshold == 75.0

    def test_hints_override(self, tmp_path):
        from cc_retrospect.config import Config
        env_file = tmp_path / "config.env"
        env_file.write_text("HINTS__SESSION_START=false\n")
        cfg = Config(_env_file=str(env_file))
        assert cfg.hints.session_start is False

    def test_missing_env_file_uses_defaults(self, tmp_path):
        from cc_retrospect.config import load_config
        cfg = load_config(tmp_path / "nonexistent.env")
        assert cfg.pricing.opus.input_per_mtok == 5.0


class TestProjectOverrides:
    """Per-project threshold overrides."""

    def test_project_override_returns_custom(self):
        from cc_retrospect.config import Config, ProjectOverride
        cfg = Config(
            project_overrides={"myapp": ProjectOverride(daily_cost_warning=200.0)},
            _env_file=None,
        )
        assert cfg.get_threshold("-Users-test-Projects-myapp", "daily_cost_warning") == 200.0

    def test_project_override_falls_back_to_global(self):
        from cc_retrospect.config import Config, ProjectOverride
        cfg = Config(
            project_overrides={"myapp": ProjectOverride(daily_cost_warning=200.0)},
            _env_file=None,
        )
        # long_session_minutes not overridden → global
        assert cfg.get_threshold("-Users-test-Projects-myapp", "long_session_minutes") == 90

    def test_unknown_project_returns_global(self):
        from cc_retrospect.config import Config
        cfg = Config(_env_file=None)
        assert cfg.get_threshold("unknown-project", "daily_cost_warning") == 400.0


class TestConfigExtraFields:
    """Config ignores unknown fields (extra='ignore')."""

    def test_extra_fields_ignored(self, tmp_path):
        from cc_retrospect.config import Config
        env_file = tmp_path / "config.env"
        env_file.write_text("UNKNOWN_FIELD=foo\n")
        cfg = Config(_env_file=str(env_file))
        assert not hasattr(cfg, "UNKNOWN_FIELD")


class TestExceptions:
    """Custom exception hierarchy."""

    def test_hierarchy(self):
        from cc_retrospect.exceptions import CCRetroError, SessionParseError, CacheCorruptError, ConfigError, DashboardError
        assert issubclass(SessionParseError, CCRetroError)
        assert issubclass(CacheCorruptError, CCRetroError)
        assert issubclass(ConfigError, CCRetroError)
        assert issubclass(DashboardError, CCRetroError)
        assert issubclass(CCRetroError, Exception)

    def test_exceptions_are_catchable(self):
        from cc_retrospect.exceptions import CCRetroError, SessionParseError
        with pytest.raises(CCRetroError):
            raise SessionParseError("bad session")
