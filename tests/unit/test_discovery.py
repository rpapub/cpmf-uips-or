"""Tests for cpmf_uips_or.discovery."""

from pathlib import Path

from cpmf_uips_or.discovery import (
    audit_all,
    discover_inventory,
    find_objects_dir,
)
from cpmf_uips_or.models import UrlStatus

# ── find_objects_dir ──────────────────────────────────────────────────────────


class TestFindObjectsDir:
    def test_returns_objects_dir(self, tmp_path: Path):
        project_json = tmp_path / "project.json"
        result = find_objects_dir(project_json)
        assert result == tmp_path / ".objects"

    def test_does_not_require_dir_to_exist(self, tmp_path: Path):
        project_json = tmp_path / "sub" / "project.json"
        result = find_objects_dir(project_json)
        assert result == tmp_path / "sub" / ".objects"


# ── discover_inventory ────────────────────────────────────────────────────────


class TestDiscoverInventory:
    def test_empty_objects_dir(self, tmp_objects_dir: Path):
        inv = discover_inventory(tmp_objects_dir)
        assert inv.screens == []
        assert inv.elements == []
        assert inv.apps == []

    def test_nonexistent_objects_dir(self, tmp_path: Path):
        inv = discover_inventory(tmp_path / ".objects")
        assert inv.screens == []
        assert inv.elements == []


# ── audit_all ─────────────────────────────────────────────────────────────────


class TestAuditAll:
    def test_empty_lists(self):
        result = audit_all([], [])
        assert result.total_objects == 0
        assert not result.has_issues

    def test_counts_total_objects(self):
        from tests.unit.test_models import _make_element, _make_screen

        screens = [_make_screen(), _make_screen()]
        elements = [_make_element()]
        result = audit_all(screens, elements)
        assert result.total_objects == 3

    def test_counts_hardcoded_screens(self):
        from tests.unit.test_models import _make_screen

        screens = [
            _make_screen(url_status=UrlStatus.HARDCODED, url="https://a.com"),
            _make_screen(url_status=UrlStatus.HARDCODED, url="https://b.com"),
        ]
        result = audit_all(screens, [])
        assert result.hardcoded_count == 2
        assert result.parameterized_count == 0

    def test_counts_parameterized_screens(self):
        from tests.unit.test_models import _make_screen

        screens = [
            _make_screen(
                url_status=UrlStatus.PARAMETERIZED,
                url="[baseUrl]",
                variable_name="baseUrl",
            ),
        ]
        result = audit_all(screens, [])
        assert result.parameterized_count == 1
        assert "baseUrl" in result.variables_in_use

    def test_unsupported_screen_version_adds_issue(self):
        from tests.unit.test_models import _make_screen

        screens = [_make_screen(descriptor_version="V1")]
        result = audit_all(screens, [])
        assert result.has_issues

    def test_version_counts_tracked(self):
        from tests.unit.test_models import _make_screen

        screens = [_make_screen(descriptor_version="V2"), _make_screen(descriptor_version="V2")]
        result = audit_all(screens, [])
        assert result.version_counts.get("V2") == 2
