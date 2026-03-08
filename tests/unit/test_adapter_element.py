"""Tests for cpmf_uips_or.adapter_element_V6."""

from pathlib import Path

from cpmf_uips_or import adapter_element_V6 as adapter

# ── parse_content ─────────────────────────────────────────────────────────────


class TestParseContent:
    def test_returns_none_for_missing_file(self, tmp_path: Path):
        result = adapter.parse_content(tmp_path / "nonexistent.content")
        assert result is None

    def test_parses_element_v6(self, element_v6_content: Path):
        result = adapter.parse_content(element_v6_content)
        assert result is not None
        assert result.version == "V6"
        assert result.search_steps == "Selector"
        assert result.element_type == "InputBox"
        assert result.activity_type == "TypeInto"
        assert result.visibility == "Interactive"
        assert result.wait_for_ready == "Interactive"
        assert "html" in result.scope_selector
        assert "webctrl" in result.full_selector

    def test_parses_parameterized_element(self, element_v6_parameterized_content: Path):
        result = adapter.parse_content(element_v6_parameterized_content)
        assert result is not None
        assert "[windowTitle]" in result.scope_selector
        assert "[windowTitle]" in result.full_selector

    def test_returns_none_for_screen_content(self, tmp_path: Path):
        p = tmp_path / "screen.content"
        p.write_text(
            '<?xml version="1.0"?><ObjectRepositoryScreenData Version="V2" Url="https://x.com" />',
            encoding="utf-8",
        )
        result = adapter.parse_content(p)
        assert result is None


# ── extract_variables ─────────────────────────────────────────────────────────


class TestExtractVariables:
    def test_no_variables(self):
        assert adapter.extract_variables("<html app='chrome.exe' />") == []

    def test_single_variable(self):
        assert adapter.extract_variables("<html title='[windowTitle]' />") == ["windowTitle"]

    def test_multiple_variables(self):
        result = adapter.extract_variables("<html title='[t]' app='[a]' />")
        assert set(result) == {"t", "a"}

    def test_mixed_hardcoded_and_variable(self):
        result = adapter.extract_variables("<html app='chrome.exe' title='[myTitle]' />")
        assert result == ["myTitle"]


# ── is_parameterized ──────────────────────────────────────────────────────────


class TestIsParameterized:
    def test_parameterized(self):
        assert adapter.is_parameterized("[myVar]") is True

    def test_not_parameterized(self):
        assert adapter.is_parameterized("<html app='chrome.exe' />") is False

    def test_partial_variable(self):
        assert adapter.is_parameterized("prefix[var]suffix") is True


# ── format_variable ───────────────────────────────────────────────────────────


class TestFormatVariable:
    def test_wraps_in_brackets(self):
        assert adapter.format_variable("windowTitle") == "[windowTitle]"


# ── is_version_supported ──────────────────────────────────────────────────────


class TestIsVersionSupported:
    def test_v6_supported(self):
        assert adapter.is_version_supported("V6") is True

    def test_v2_not_supported(self):
        assert adapter.is_version_supported("V2") is False
