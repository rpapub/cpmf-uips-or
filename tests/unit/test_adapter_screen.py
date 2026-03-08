"""Tests for cpmf_uips_or.adapter_screen_V2."""

from pathlib import Path

from cpmf_uips_or import adapter_screen_V2 as adapter
from tests.unit.conftest import SCREEN_V2_XML

# ── parse_content ─────────────────────────────────────────────────────────────


class TestParseContent:
    def test_returns_none_for_missing_file(self, tmp_path: Path):
        result = adapter.parse_content(tmp_path / "nonexistent.content")
        assert result is None

    def test_parses_screen_v2(self, screen_v2_content: Path):
        result = adapter.parse_content(screen_v2_content)
        assert result is not None
        assert result.version == "V2"
        assert result.url == "https://example.com/login"
        assert result.browser_type == "Chrome"
        assert "html" in result.selector

    def test_parses_parameterized_url(self, screen_v2_parameterized_content: Path):
        result = adapter.parse_content(screen_v2_parameterized_content)
        assert result is not None
        assert result.url == "[baseUrl]"

    def test_returns_none_for_element_content(self, tmp_path: Path):
        # Element files don't have TargetApp
        p = tmp_path / "elem.content"
        p.write_text(
            '<?xml version="1.0"?><ObjectRepositoryTargetData Version="V6" />', encoding="utf-8"
        )
        result = adapter.parse_content(p)
        assert result is None

    def test_parses_variables(self, tmp_path: Path):
        xml = SCREEN_V2_XML.replace(
            "</ObjectRepositoryScreenData.Data>",
            '<ObjectRepositoryVariableData Name="baseUrl" DefaultValue="*" />'
            "</ObjectRepositoryScreenData.Data>",
        )
        p = tmp_path / "screen_with_vars.content"
        p.write_text(xml, encoding="utf-8")
        result = adapter.parse_content(p)
        assert result is not None
        assert result.variables is not None
        assert len(result.variables) == 1
        assert result.variables[0].name == "baseUrl"


# ── extract_variable ──────────────────────────────────────────────────────────


class TestExtractVariable:
    def test_hardcoded_url_returns_none(self):
        var, suffix = adapter.extract_variable("https://example.com")
        assert var is None
        assert suffix == ""

    def test_simple_variable(self):
        var, suffix = adapter.extract_variable("[baseUrl]")
        assert var == "baseUrl"
        assert suffix == ""

    def test_variable_with_suffix(self):
        var, suffix = adapter.extract_variable("[baseUrl]/login/page")
        assert var == "baseUrl"
        assert suffix == "/login/page"

    def test_empty_string(self):
        var, suffix = adapter.extract_variable("")
        assert var is None

    def test_is_parameterized_true(self):
        assert adapter.is_parameterized("[myVar]") is True

    def test_is_parameterized_false(self):
        assert adapter.is_parameterized("https://example.com") is False


# ── format_variable ───────────────────────────────────────────────────────────


class TestFormatVariable:
    def test_wraps_in_brackets(self):
        assert adapter.format_variable("myVar") == "[myVar]"


# ── is_version_supported ──────────────────────────────────────────────────────


class TestIsVersionSupported:
    def test_v2_supported(self):
        assert adapter.is_version_supported("V2") is True

    def test_v1_not_supported(self):
        assert adapter.is_version_supported("V1") is False

    def test_v6_not_supported(self):
        assert adapter.is_version_supported("V6") is False
