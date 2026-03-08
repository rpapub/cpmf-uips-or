"""Tests for cpmf_uips_or.rules — load_rules and rule type dispatch."""

from pathlib import Path

import pytest

from cpmf_uips_or.models import (
    ParameterizeRule,
    RenameRule,
    ResetRule,
    RuleTarget,
)
from cpmf_uips_or.rules import load_rules


def _write_toml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "rules.toml"
    p.write_bytes(content.encode("utf-8"))
    return p


# ── load_rules ────────────────────────────────────────────────────────────────


class TestLoadRules:
    def test_raises_for_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_rules(tmp_path / "nonexistent.toml")

    def test_empty_rules_list(self, tmp_path: Path):
        p = _write_toml(tmp_path, "")
        result = load_rules(p)
        assert result == []

    def test_parameterize_rule(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "https://example.com/*"
variable = "baseUrl"
"""
        p = _write_toml(tmp_path, toml)
        rules = load_rules(p)
        assert len(rules) == 1
        r = rules[0]
        assert isinstance(r, ParameterizeRule)
        assert r.match == "https://example.com/*"
        assert r.variable == "baseUrl"
        assert r.target == RuleTarget.ALL
        assert r.default_value == "*"
        assert r.cascade is False

    def test_parameterize_with_target(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "https://example.com/*"
variable = "baseUrl"
target = "screen"
"""
        p = _write_toml(tmp_path, toml)
        rules = load_rules(p)
        assert rules[0].target == RuleTarget.SCREEN

    def test_rename_rule(self, tmp_path: Path):
        toml = """
[[rules]]
type = "rename"
from_variable = "oldVar"
to_variable = "newVar"
"""
        p = _write_toml(tmp_path, toml)
        rules = load_rules(p)
        assert len(rules) == 1
        r = rules[0]
        assert isinstance(r, RenameRule)
        assert r.from_variable == "oldVar"
        assert r.to_variable == "newVar"

    def test_reset_rule(self, tmp_path: Path):
        toml = """
[[rules]]
type = "reset"
variable = "baseUrl"
value = "https://example.com"
"""
        p = _write_toml(tmp_path, toml)
        rules = load_rules(p)
        assert len(rules) == 1
        r = rules[0]
        assert isinstance(r, ResetRule)
        assert r.variable == "baseUrl"
        assert r.value == "https://example.com"

    def test_multiple_rules(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "https://a.com/*"
variable = "urlA"

[[rules]]
type = "rename"
from_variable = "old"
to_variable = "new"
"""
        p = _write_toml(tmp_path, toml)
        rules = load_rules(p)
        assert len(rules) == 2
        assert isinstance(rules[0], ParameterizeRule)
        assert isinstance(rules[1], RenameRule)

    def test_unknown_rule_type_raises(self, tmp_path: Path):
        toml = """
[[rules]]
type = "unknown"
"""
        p = _write_toml(tmp_path, toml)
        with pytest.raises(ValueError, match="Unknown rule type"):
            load_rules(p)

    def test_parameterize_missing_match_raises(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
variable = "x"
"""
        p = _write_toml(tmp_path, toml)
        with pytest.raises(ValueError, match="requires 'match' and 'variable'"):
            load_rules(p)

    def test_cascade_flag(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "*"
variable = "x"
cascade = true
"""
        p = _write_toml(tmp_path, toml)
        rules = load_rules(p)
        assert isinstance(rules[0], ParameterizeRule)
        assert rules[0].cascade is True
