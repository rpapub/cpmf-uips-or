"""Tests for cpmf_uips_or.formatters."""


from cpmf_uips_or.formatters import format_flat_json, format_tree_text
from cpmf_uips_or.models import (
    AppNode,
    Inventory,
    ScreenNode,
    VersionNode,
)
from tests.unit.test_models import _make_element, _make_screen


def _make_inventory(**kwargs) -> Inventory:
    defaults = dict(screens=[], elements=[], apps=[])
    defaults.update(kwargs)
    return Inventory(**defaults)


# ── format_tree_text ──────────────────────────────────────────────────────────


class TestFormatTreeText:
    def test_empty_inventory(self):
        inv = _make_inventory()
        result = format_tree_text(inv)
        assert result == ""

    def test_single_app_version_screen(self):
        screen = _make_screen(
            app_name="CMS", app_version="2026-01", screen_name="Login",
            url="https://example.com",
        )
        screen_node = ScreenNode(entry=screen)
        version = VersionNode(name="2026-01", reference="lib/v1", parent_ref="lib/app1")
        version.screens.append(screen_node)
        app = AppNode(name="CMS", reference="lib/app1")
        app.versions.append(version)

        inv = _make_inventory(apps=[app], screens=[screen])
        result = format_tree_text(inv)

        assert "App: CMS" in result
        assert "Version: 2026-01" in result
        assert "Screen: Login" in result
        assert "hardcoded" in result

    def test_parameterized_screen_shows_variable(self):
        from cpmf_uips_or.models import UrlStatus

        screen = _make_screen(
            app_name="CMS", app_version="v1", screen_name="Home",
            url="[baseUrl]", url_status=UrlStatus.PARAMETERIZED, variable_name="baseUrl"
        )
        screen_node = ScreenNode(entry=screen)
        version = VersionNode(name="v1", reference="lib/v1", parent_ref="lib/a1")
        version.screens.append(screen_node)
        app = AppNode(name="CMS", reference="lib/a1")
        app.versions.append(version)

        inv = _make_inventory(apps=[app], screens=[screen])
        result = format_tree_text(inv)

        assert "[baseUrl]" in result


# ── format_flat_json ──────────────────────────────────────────────────────────


class TestFormatFlatJson:
    def test_empty_inventory(self):
        inv = _make_inventory()
        result = format_flat_json(inv)
        assert result["entries"] == []

    def test_screen_appears_in_entries(self):
        screen = _make_screen()
        inv = _make_inventory(screens=[screen])
        result = format_flat_json(inv)
        entries = result["entries"]
        assert len(entries) == 1
        assert entries[0]["type"] == "screen"
        assert entries[0]["url"] == screen.url

    def test_element_appears_in_entries(self):
        element = _make_element()
        inv = _make_inventory(elements=[element])
        result = format_flat_json(inv)
        entries = result["entries"]
        assert len(entries) == 1
        assert entries[0]["type"] == "element"
        assert entries[0]["element_name"] == element.element_name

    def test_project_metadata_included(self):
        from cpmf_uips_or.models import ProjectMeta

        inv = _make_inventory()
        inv.project = ProjectMeta(
            name="MyProject",
            project_id="proj-001",
            version="1.0",
            studio_version="24.0",
            target_framework="Portable",
        )
        result = format_flat_json(inv)
        assert "project" in result
        assert result["project"]["name"] == "MyProject"
