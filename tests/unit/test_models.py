"""Tests for cpmf_uips_or.models."""

from pathlib import Path

from cpmf_uips_or.models import (
    AuditResult,
    ElementEntry,
    EntryType,
    ParameterizeRule,
    RenameRule,
    ReplaceRule,
    ResetRule,
    RuleTarget,
    ScreenEntry,
    UrlStatus,
)


def _make_screen(**kwargs) -> ScreenEntry:
    defaults = dict(
        app_name="MyApp",
        app_version="v1",
        screen_name="Login",
        url="https://example.com",
        url_status=UrlStatus.HARDCODED,
        variable_name=None,
        selector="<html app='chrome.exe' />",
        reference="lib/screen-001",
        descriptor_version="V2",
        content_path=Path("/fake/path"),
    )
    defaults.update(kwargs)
    return ScreenEntry(**defaults)


def _make_element(**kwargs) -> ElementEntry:
    defaults = dict(
        app_name="MyApp",
        app_version="v1",
        screen_name="Login",
        element_name="username",
        search_steps="Selector",
        scope_selector="<html />",
        full_selector="<html /><webctrl id='u' />",
        browser_url="",
        element_type="InputBox",
        activity_type="TypeInto",
        reference="lib/elem-001",
        descriptor_version="V6",
        content_path=Path("/fake/path"),
    )
    defaults.update(kwargs)
    return ElementEntry(**defaults)


# ── ScreenEntry ──────────────────────────────────────────────────────────────


class TestScreenEntry:
    def test_full_path(self):
        s = _make_screen(app_name="CMS", app_version="2026-01", screen_name="Dashboard")
        assert s.full_path == "CMS/2026-01/Dashboard"

    def test_entry_type_is_screen(self):
        s = _make_screen()
        assert s.entry_type == EntryType.SCREEN

    def test_url_status_hardcoded(self):
        s = _make_screen(url_status=UrlStatus.HARDCODED)
        assert s.url_status == UrlStatus.HARDCODED

    def test_url_status_parameterized(self):
        s = _make_screen(url_status=UrlStatus.PARAMETERIZED, variable_name="baseUrl")
        assert s.url_status == UrlStatus.PARAMETERIZED
        assert s.variable_name == "baseUrl"


# ── ElementEntry ─────────────────────────────────────────────────────────────


class TestElementEntry:
    def test_full_path(self):
        e = _make_element(
            app_name="CMS", app_version="2026-01", screen_name="Login", element_name="btnLogin"
        )
        assert e.full_path == "CMS/2026-01/Login/btnLogin"

    def test_entry_type_is_element(self):
        e = _make_element()
        assert e.entry_type == EntryType.ELEMENT

    def test_is_parameterized_false_by_default(self):
        e = _make_element()
        assert not e.is_parameterized

    def test_is_parameterized_scope_variables(self):
        e = _make_element(scope_variables=["windowTitle"])
        assert e.is_parameterized

    def test_is_parameterized_selector_variables(self):
        e = _make_element(selector_variables=["myVar"])
        assert e.is_parameterized

    def test_is_parameterized_both(self):
        e = _make_element(scope_variables=["a"], selector_variables=["b"])
        assert e.is_parameterized


# ── AuditResult ──────────────────────────────────────────────────────────────


class TestAuditResult:
    def test_has_issues_false_when_empty(self):
        r = AuditResult()
        assert not r.has_issues

    def test_has_issues_true_when_hardcoded(self):
        r = AuditResult(hardcoded_count=1)
        assert r.has_issues

    def test_has_issues_true_when_issues_list(self):
        r = AuditResult(issues=["some issue"])
        assert r.has_issues

    def test_default_counts(self):
        r = AuditResult()
        assert r.total_objects == 0
        assert r.hardcoded_count == 0
        assert r.parameterized_count == 0


# ── UrlStatus ─────────────────────────────────────────────────────────────────


class TestUrlStatus:
    def test_values(self):
        assert UrlStatus.HARDCODED.value == "hardcoded"
        assert UrlStatus.PARAMETERIZED.value == "parameterized"


# ── Rule inheritance ──────────────────────────────────────────────────────────


class TestRuleInheritance:
    def test_parameterize_is_replace_rule(self):
        r = ParameterizeRule(match="https://example.com/*", variable="baseUrl")
        assert isinstance(r, ReplaceRule)

    def test_rename_is_replace_rule(self):
        r = RenameRule(from_variable="oldVar", to_variable="newVar")
        assert isinstance(r, ReplaceRule)

    def test_reset_is_replace_rule(self):
        r = ResetRule(variable="baseUrl", value="https://example.com")
        assert isinstance(r, ReplaceRule)

    def test_parameterize_default_target(self):
        r = ParameterizeRule(match="*", variable="x")
        assert r.target == RuleTarget.ALL

    def test_parameterize_custom_target(self):
        r = ParameterizeRule(match="*", variable="x", target=RuleTarget.SCREEN)
        assert r.target == RuleTarget.SCREEN

    def test_parameterize_defaults(self):
        r = ParameterizeRule(match="*", variable="x")
        assert r.default_value == "*"
        assert r.cascade is False
        assert r.attribute is None
