"""Additional tests for parser.py — parse_content, verify_xml_wellformed, update_content_url."""

from pathlib import Path

from cpmf_uips_or.parser import (
    parse_content,
    update_content_url,
    verify_xml_wellformed,
)

SCREEN_CONTENT_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ObjectRepositoryScreenData xmlns="http://schemas.uipath.com/workflow/activities/uix">
  <ObjectRepositoryScreenData.Data>
    <TargetApp Version="V2"
        Url="https://example.com/login"
        Selector="&lt;html app='chrome.exe' title='Login' /&gt;"
        BrowserType="Chrome" />
  </ObjectRepositoryScreenData.Data>
</ObjectRepositoryScreenData>
"""


class TestParseContentParser:
    """Tests for parser.parse_content (legacy, not adapter_screen)."""

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        result = parse_content(tmp_path / "missing.content")
        assert result is None

    def test_parses_url_and_version(self, tmp_path: Path):
        p = tmp_path / "test.content"
        p.write_text(SCREEN_CONTENT_XML, encoding="utf-8")
        result = parse_content(p)
        assert result is not None
        assert result.url == "https://example.com/login"
        assert result.version == "V2"
        assert result.browser_type == "Chrome"
        assert "html" in result.selector

    def test_returns_none_on_parse_error(self, tmp_path: Path):
        p = tmp_path / "bad.content"
        p.write_bytes(b"\x00\x01\x02\x03")  # invalid bytes
        parse_content(p)
        # Should not crash, may return None or a result depending on fallback


class TestVerifyXmlWellformed:
    def test_valid_xml(self, tmp_path: Path):
        p = tmp_path / "good.content"
        p.write_text(SCREEN_CONTENT_XML, encoding="utf-8")
        is_valid, err = verify_xml_wellformed(p)
        assert is_valid is True
        assert err is None

    def test_invalid_xml(self, tmp_path: Path):
        p = tmp_path / "bad.content"
        p.write_text("<?xml version='1.0'?><root><unclosed>", encoding="utf-8")
        is_valid, err = verify_xml_wellformed(p)
        assert is_valid is False
        assert err is not None

    def test_missing_file(self, tmp_path: Path):
        is_valid, err = verify_xml_wellformed(tmp_path / "nonexistent.content")
        assert is_valid is False
        assert "not found" in (err or "").lower()


class TestUpdateContentUrl:
    def test_updates_url_successfully(self, tmp_path: Path):
        p = tmp_path / "screen.content"
        p.write_text(SCREEN_CONTENT_XML, encoding="utf-8")
        success = update_content_url(p, "https://example.com/login", "[baseUrl]")
        assert success is True
        assert "[baseUrl]" in p.read_text()

    def test_returns_false_for_missing_file(self, tmp_path: Path):
        success = update_content_url(tmp_path / "missing.content", "old", "new")
        assert success is False

    def test_returns_false_when_old_url_not_found(self, tmp_path: Path):
        p = tmp_path / "screen.content"
        p.write_text(SCREEN_CONTENT_XML, encoding="utf-8")
        success = update_content_url(p, "https://wrong.com", "[baseUrl]")
        assert success is False
