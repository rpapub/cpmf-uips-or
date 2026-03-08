"""Tests for cpmf_uips_or.parser."""

from pathlib import Path

from cpmf_uips_or.parser import Metadata, parse_metadata, read_content_file

# ── parse_metadata ────────────────────────────────────────────────────────────


class TestParseMetadata:
    def test_returns_none_for_missing_file(self, tmp_path: Path):
        result = parse_metadata(tmp_path / "nonexistent.metadata")
        assert result is None

    def test_parses_full_metadata(self, metadata_file: Path):
        result = parse_metadata(metadata_file)
        assert isinstance(result, Metadata)
        assert result.name == "LoginScreen"
        assert result.type == "Screen"
        assert result.id == "screen-001"
        assert result.reference == "lib/screen-001"
        assert result.parent_ref == "lib/version-001"
        assert result.created == "2024-01-01T00:00:00Z"
        assert result.updated == "2024-06-01T00:00:00Z"
        assert result.created_by == ["24.10.0"]
        assert result.updated_by == ["24.10.1"]

    def test_parses_minimal_metadata(self, tmp_path: Path):
        p = tmp_path / ".metadata"
        p.write_text('{"Name": "App", "Type": "App", "Id": "a", "Reference": "lib/a"}')
        result = parse_metadata(p)
        assert result is not None
        assert result.name == "App"
        assert result.parent_ref is None
        assert result.created is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path):
        p = tmp_path / ".metadata"
        p.write_text("not json")
        result = parse_metadata(p)
        assert result is None

    def test_handles_bom(self, tmp_path: Path):
        p = tmp_path / ".metadata"
        data = '{"Name": "X", "Type": "App", "Id": "1", "Reference": "lib/1"}'
        # Write with BOM (utf-8-sig)
        p.write_bytes(b"\xef\xbb\xbf" + data.encode("utf-8"))
        result = parse_metadata(p)
        assert result is not None
        assert result.name == "X"


# ── read_content_file ─────────────────────────────────────────────────────────


class TestReadContentFile:
    def test_reads_utf8(self, tmp_path: Path):
        p = tmp_path / "test.content"
        content = '<?xml version="1.0"?><root Version="V2" Url="https://example.com" />'
        p.write_text(content, encoding="utf-8")
        text, encoding = read_content_file(p)
        assert "V2" in text
        assert encoding == "utf-8"

    def test_reads_utf16_le_with_bom(self, tmp_path: Path):
        p = tmp_path / "test.content"
        content = '<?xml version="1.0"?><root Version="V2" />'
        p.write_bytes(b"\xff\xfe" + content.encode("utf-16-le"))
        text, encoding = read_content_file(p)
        assert encoding == "utf-16-le"
        assert "V2" in text

    def test_reads_utf16_be_with_bom(self, tmp_path: Path):
        p = tmp_path / "test.content"
        content = '<?xml version="1.0"?><root Version="V2" />'
        p.write_bytes(b"\xfe\xff" + content.encode("utf-16-be"))
        text, encoding = read_content_file(p)
        assert encoding == "utf-16-be"
        assert "V2" in text
