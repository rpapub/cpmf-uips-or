"""Tests for adapter mutation functions — update_content, update_selector_attr."""

from pathlib import Path

from cpmf_uips_or import adapter_element_V6 as element_adapter
from cpmf_uips_or import adapter_screen_V2 as screen_adapter
from tests.unit.conftest import ELEMENT_V6_XML, SCREEN_V2_XML

# ── adapter_screen_V2: update_content ─────────────────────────────────────────


class TestScreenUpdateContent:
    def test_updates_url(self, tmp_path: Path):
        p = tmp_path / "screen.content"
        p.write_text(SCREEN_V2_XML, encoding="utf-8")
        success = screen_adapter.update_content(
            p, "https://example.com/login", "[baseUrl]"
        )
        assert success is True
        text = p.read_text()
        assert "[baseUrl]" in text
        assert "https://example.com/login" not in text

    def test_returns_false_for_missing_file(self, tmp_path: Path):
        success = screen_adapter.update_content(
            tmp_path / "missing.content", "old", "new"
        )
        assert success is False

    def test_returns_false_when_old_url_not_found(self, tmp_path: Path):
        p = tmp_path / "screen.content"
        p.write_text(SCREEN_V2_XML, encoding="utf-8")
        success = screen_adapter.update_content(p, "https://wrong.com", "[baseUrl]")
        assert success is False


# ── adapter_screen_V2: update_selector_attr ───────────────────────────────────


class TestScreenUpdateSelectorAttr:
    def test_updates_selector_attribute(self, tmp_path: Path):
        p = tmp_path / "screen.content"
        p.write_text(SCREEN_V2_XML, encoding="utf-8")
        # The Selector is "&lt;html app='chrome.exe' title='Login' /&gt;"
        success = screen_adapter.update_selector_attr(p, "title", "Login", "[windowTitle]")
        assert success is True
        text = p.read_text()
        assert "[windowTitle]" in text

    def test_returns_false_for_missing_file(self, tmp_path: Path):
        success = screen_adapter.update_selector_attr(
            tmp_path / "missing.content", "title", "Login", "[t]"
        )
        assert success is False

    def test_returns_false_when_attr_not_found(self, tmp_path: Path):
        p = tmp_path / "screen.content"
        p.write_text(SCREEN_V2_XML, encoding="utf-8")
        success = screen_adapter.update_selector_attr(p, "title", "NotFound", "[t]")
        assert success is False


# ── adapter_element_V6: update_scope_attr ────────────────────────────────────


class TestElementUpdateScopeAttr:
    def test_updates_scope_attribute(self, tmp_path: Path):
        p = tmp_path / "elem.content"
        p.write_text(ELEMENT_V6_XML, encoding="utf-8")
        # ScopeSelectorArgument contains title='Login'
        success = element_adapter.update_scope_attr(p, "title", "Login", "[windowTitle]")
        assert success is True
        text = p.read_text()
        assert "[windowTitle]" in text

    def test_returns_false_for_missing_file(self, tmp_path: Path):
        success = element_adapter.update_scope_attr(
            tmp_path / "missing.content", "title", "Login", "[t]"
        )
        assert success is False

    def test_returns_false_when_attr_not_found(self, tmp_path: Path):
        p = tmp_path / "elem.content"
        p.write_text(ELEMENT_V6_XML, encoding="utf-8")
        success = element_adapter.update_scope_attr(p, "title", "NotFound", "[t]")
        assert success is False
