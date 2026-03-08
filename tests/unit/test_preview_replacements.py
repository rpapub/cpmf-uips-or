"""Tests for cpmf_uips_or.rules.preview_replacements and helpers."""


from cpmf_uips_or.models import (
    ParameterizeRule,
    RenameRule,
    ResetRule,
    RuleTarget,
    UrlStatus,
)
from cpmf_uips_or.rules import (
    find_descendant_elements,
    find_root_screen,
    preview_replacements,
)
from tests.unit.test_models import _make_element, _make_screen

# ── preview_replacements — screens ────────────────────────────────────────────


class TestPreviewScreen:
    def test_no_rules_no_previews(self):
        screens = [_make_screen()]
        previews, warnings = preview_replacements(screens, [], [])
        assert previews == []
        assert warnings == []

    def test_parameterize_hardcoded_url(self):
        screen = _make_screen(url="https://example.com/login", url_status=UrlStatus.HARDCODED)
        rule = ParameterizeRule(match="https://example.com/*", variable="baseUrl")
        previews, _ = preview_replacements([screen], [], [rule])
        assert len(previews) == 1
        assert previews[0].old_value == "https://example.com/login"
        assert "[baseUrl]" in previews[0].new_value

    def test_parameterize_preserves_path_suffix(self):
        # match "https://example.com/*" → base_pattern = "https://example.com/"
        # suffix = url[len(base_pattern):] = "login/page"  (no leading slash)
        screen = _make_screen(
            url="https://example.com/login/page", url_status=UrlStatus.HARDCODED
        )
        rule = ParameterizeRule(match="https://example.com/*", variable="baseUrl")
        previews, _ = preview_replacements([screen], [], [rule])
        assert len(previews) == 1
        assert previews[0].new_value == "[baseUrl]login/page"

    def test_does_not_match_parameterized_url(self):
        screen = _make_screen(
            url="[baseUrl]",
            url_status=UrlStatus.PARAMETERIZED,
            variable_name="baseUrl",
        )
        rule = ParameterizeRule(match="*", variable="baseUrl")
        previews, _ = preview_replacements([screen], [], [rule])
        assert previews == []

    def test_rename_parameterized_screen(self):
        screen = _make_screen(
            url="[oldVar]",
            url_status=UrlStatus.PARAMETERIZED,
            variable_name="oldVar",
        )
        rule = RenameRule(from_variable="oldVar", to_variable="newVar")
        previews, _ = preview_replacements([screen], [], [rule])
        assert len(previews) == 1
        assert previews[0].new_value == "[newVar]"

    def test_reset_parameterized_screen(self):
        screen = _make_screen(
            url="[baseUrl]",
            url_status=UrlStatus.PARAMETERIZED,
            variable_name="baseUrl",
        )
        rule = ResetRule(variable="baseUrl", value="https://example.com")
        previews, _ = preview_replacements([screen], [], [rule])
        assert len(previews) == 1
        assert previews[0].new_value == "https://example.com"

    def test_unsupported_version_skipped_without_force(self):
        screen = _make_screen(descriptor_version="V1")
        rule = ParameterizeRule(match="*", variable="x")
        previews, warnings = preview_replacements([screen], [], [rule])
        assert previews == []
        assert len(warnings) == 1

    def test_unsupported_version_allowed_with_force(self):
        screen = _make_screen(
            url="https://example.com",
            url_status=UrlStatus.HARDCODED,
            descriptor_version="V1",
        )
        rule = ParameterizeRule(match="https://example.com", variable="x")
        previews, warnings = preview_replacements([screen], [], [rule], force=True)
        assert len(previews) == 1


# ── preview_replacements — elements ───────────────────────────────────────────


class TestPreviewElement:
    def test_parameterize_element_scope(self):
        elem = _make_element(
            scope_selector="<html app='chrome.exe' title='Google' />",
            scope_variables=[],
        )
        rule = ParameterizeRule(
            match="Google",
            variable="windowTitle",
            target=RuleTarget.ELEMENT_SCOPE,
            attribute="title",
        )
        previews, _ = preview_replacements([], [elem], [rule])
        assert len(previews) == 1

    def test_rename_element_scope_variable(self):
        elem = _make_element(scope_variables=["oldVar"])
        rule = RenameRule(from_variable="oldVar", to_variable="newVar")
        previews, _ = preview_replacements([], [elem], [rule])
        assert len(previews) == 1
        assert previews[0].old_value == elem.scope_selector

    def test_reset_element_scope_variable(self):
        elem = _make_element(scope_variables=["baseVar"])
        rule = ResetRule(variable="baseVar", value="hardcoded")
        previews, _ = preview_replacements([], [elem], [rule])
        assert len(previews) == 1

    def test_unsupported_element_version_skipped(self):
        elem = _make_element(descriptor_version="V5")
        rule = ParameterizeRule(match="*", variable="x")
        previews, warnings = preview_replacements([], [elem], [rule])
        assert previews == []
        assert len(warnings) == 1


# ── find_root_screen ──────────────────────────────────────────────────────────


class TestFindRootScreen:
    def test_direct_parent_screen(self):
        screen = _make_screen(reference="lib/scr-001")
        elem = _make_element(reference="lib/elem-001", parent_ref="lib/scr-001")
        screens_by_ref = {"lib/scr-001": screen}
        elements_by_ref = {"lib/elem-001": elem}
        result = find_root_screen(elem, screens_by_ref, elements_by_ref)
        assert result is screen

    def test_nested_element_finds_screen(self):
        screen = _make_screen(reference="lib/scr-001")
        parent_elem = _make_element(reference="lib/elem-001", parent_ref="lib/scr-001")
        child_elem = _make_element(reference="lib/elem-002", parent_ref="lib/elem-001")
        screens_by_ref = {"lib/scr-001": screen}
        elements_by_ref = {
            "lib/elem-001": parent_elem,
            "lib/elem-002": child_elem,
        }
        result = find_root_screen(child_elem, screens_by_ref, elements_by_ref)
        assert result is screen

    def test_returns_none_when_no_parent(self):
        elem = _make_element(parent_ref=None)
        result = find_root_screen(elem, {}, {})
        assert result is None

    def test_returns_none_when_parent_unknown(self):
        elem = _make_element(parent_ref="lib/unknown")
        result = find_root_screen(elem, {}, {})
        assert result is None


# ── find_descendant_elements ──────────────────────────────────────────────────


class TestFindDescendantElements:
    def test_direct_child(self):
        screen = _make_screen(reference="lib/scr-001")
        elem = _make_element(reference="lib/elem-001", parent_ref="lib/scr-001")
        result = find_descendant_elements(screen, [elem], {"lib/elem-001": elem})
        assert elem in result

    def test_nested_child(self):
        screen = _make_screen(reference="lib/scr-001")
        parent_elem = _make_element(reference="lib/elem-001", parent_ref="lib/scr-001")
        child_elem = _make_element(reference="lib/elem-002", parent_ref="lib/elem-001")
        elements_by_ref = {
            "lib/elem-001": parent_elem,
            "lib/elem-002": child_elem,
        }
        result = find_descendant_elements(screen, [parent_elem, child_elem], elements_by_ref)
        assert parent_elem in result
        assert child_elem in result

    def test_does_not_include_elements_of_other_screens(self):
        screen1 = _make_screen(reference="lib/scr-001", screen_name="S1")
        elem_s2 = _make_element(reference="lib/elem-002", parent_ref="lib/scr-002")
        result = find_descendant_elements(screen1, [elem_s2], {"lib/elem-002": elem_s2})
        assert result == []
