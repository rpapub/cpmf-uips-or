"""Additional tests for rules.py — _parse_target branches, screen.selector rules, cascade."""

from pathlib import Path

import pytest

from cpmf_uips_or.models import (
    ParameterizeRule,
    RuleTarget,
    UrlStatus,
)
from cpmf_uips_or.rules import load_rules, preview_replacements
from tests.unit.test_models import _make_element, _make_screen


def _write_toml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "rules.toml"
    p.write_bytes(content.encode("utf-8"))
    return p


class TestParseTargetBranches:
    """Cover _parse_target for all target strings."""

    def test_screen_selector_target(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "Login"
variable = "windowTitle"
target = "screen.selector"
attribute = "title"
"""
        rules = load_rules(_write_toml(tmp_path, toml))
        assert rules[0].target == RuleTarget.SCREEN_SELECTOR

    def test_element_scope_target(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "Login"
variable = "windowTitle"
target = "element.scope"
attribute = "title"
"""
        rules = load_rules(_write_toml(tmp_path, toml))
        assert rules[0].target == RuleTarget.ELEMENT_SCOPE

    def test_element_selector_target(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "u123"
variable = "elementId"
target = "element.selector"
attribute = "id"
"""
        rules = load_rules(_write_toml(tmp_path, toml))
        assert rules[0].target == RuleTarget.ELEMENT_SELECTOR

    def test_unknown_target_raises(self, tmp_path: Path):
        toml = """
[[rules]]
type = "parameterize"
match = "*"
variable = "x"
target = "unknown.target"
"""
        with pytest.raises(ValueError):
            load_rules(_write_toml(tmp_path, toml))


class TestScreenSelectorRule:
    """Cover _match_screen_selector_rule path in preview_replacements."""

    def test_screen_selector_rule_matches(self):
        screen = _make_screen(
            selector="<html app='chrome.exe' title='Google' />",
            url="https://example.com",
            url_status=UrlStatus.HARDCODED,
        )
        rule = ParameterizeRule(
            match="Google",
            variable="windowTitle",
            target=RuleTarget.SCREEN_SELECTOR,
            attribute="title",
        )
        previews, _ = preview_replacements([screen], [], [rule])
        assert len(previews) == 1
        assert previews[0].attribute == "title"

    def test_screen_selector_rule_no_attribute_skips(self):
        screen = _make_screen(
            selector="<html app='chrome.exe' title='Google' />",
            url="https://example.com",
            url_status=UrlStatus.HARDCODED,
        )
        # Rule without attribute should be skipped for screen.selector
        rule = ParameterizeRule(
            match="Google",
            variable="windowTitle",
            target=RuleTarget.SCREEN_SELECTOR,
            attribute=None,
        )
        previews, _ = preview_replacements([screen], [], [rule])
        assert previews == []

    def test_screen_selector_rule_already_parameterized_skips(self):
        screen = _make_screen(
            selector="<html app='chrome.exe' title='[windowTitle]' />",
            url="https://example.com",
            url_status=UrlStatus.HARDCODED,
        )
        rule = ParameterizeRule(
            match="*",
            variable="windowTitle",
            target=RuleTarget.SCREEN_SELECTOR,
            attribute="title",
        )
        previews, _ = preview_replacements([screen], [], [rule])
        assert previews == []


class TestElementSelectorRule:
    """Cover full_selector matching path."""

    def test_element_selector_rule_matches(self):
        elem = _make_element(
            full_selector="<html /><webctrl id='u123' />",
            selector_variables=[],
        )
        rule = ParameterizeRule(
            match="u123",
            variable="elementId",
            target=RuleTarget.ELEMENT_SELECTOR,
            attribute="id",
        )
        previews, _ = preview_replacements([], [elem], [rule])
        assert len(previews) == 1


class TestAlreadyParameterizedSkipped:
    """Cover _is_selector_parameterized path."""

    def test_string_format_expression_skipped(self):
        elem = _make_element(
            scope_selector='[string.Format("<html title=\'{0}\' />", windowTitle)]',
            scope_variables=[],
        )
        rule = ParameterizeRule(
            match="*",
            variable="x",
            target=RuleTarget.ELEMENT_SCOPE,
            attribute="title",
        )
        previews, _ = preview_replacements([], [elem], [rule])
        assert previews == []
