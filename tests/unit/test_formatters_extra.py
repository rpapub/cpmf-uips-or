"""Additional tests for formatters — format_tree_json, _*_to_dict functions."""

from cpmf_uips_or.formatters import format_tree_json, format_tree_text
from cpmf_uips_or.models import (
    AppNode,
    ElementNode,
    Inventory,
    ScreenNode,
    VersionNode,
)
from tests.unit.test_models import _make_element, _make_screen


def _make_full_inventory() -> Inventory:
    """Build a minimal but complete inventory with app/version/screen/element."""
    screen = _make_screen(
        app_name="CMS", app_version="2026-01", screen_name="Login",
        reference="lib/scr-001",
    )
    element = _make_element(
        app_name="CMS", app_version="2026-01", screen_name="Login",
        element_name="username", reference="lib/elem-001", parent_ref="lib/scr-001",
    )

    screen_node = ScreenNode(entry=screen)
    elem_node = ElementNode(entry=element)
    screen_node.elements.append(elem_node)

    version = VersionNode(name="2026-01", reference="lib/ver-001", parent_ref="lib/app-001")
    version.screens.append(screen_node)

    app = AppNode(name="CMS", reference="lib/app-001")
    app.versions.append(version)

    return Inventory(
        screens=[screen],
        elements=[element],
        apps=[app],
    )


class TestFormatTreeJson:
    def test_basic_structure(self):
        inv = _make_full_inventory()
        result = format_tree_json(inv)
        assert "apps" in result
        assert len(result["apps"]) == 1

    def test_app_contains_versions(self):
        inv = _make_full_inventory()
        result = format_tree_json(inv)
        app = result["apps"][0]
        assert app["name"] == "CMS"
        assert len(app["versions"]) == 1

    def test_version_contains_screens(self):
        inv = _make_full_inventory()
        result = format_tree_json(inv)
        version = result["apps"][0]["versions"][0]
        assert version["name"] == "2026-01"
        assert len(version["screens"]) == 1

    def test_screen_contains_elements(self):
        inv = _make_full_inventory()
        result = format_tree_json(inv)
        screen = result["apps"][0]["versions"][0]["screens"][0]
        assert screen["name"] == "Login"
        assert len(screen["elements"]) == 1

    def test_element_fields(self):
        inv = _make_full_inventory()
        result = format_tree_json(inv)
        elem = result["apps"][0]["versions"][0]["screens"][0]["elements"][0]
        assert elem["name"] == "username"
        assert "search_steps" in elem
        assert "element_type" in elem

    def test_project_metadata_omitted_when_absent(self):
        inv = _make_full_inventory()
        result = format_tree_json(inv)
        assert "project" not in result


class TestFormatTreeTextWithElements:
    def test_elements_appear_in_output(self):
        inv = _make_full_inventory()
        result = format_tree_text(inv)
        assert "Element: username" in result

    def test_element_parameterization_shown(self):

        screen = _make_screen(
            app_name="CMS", app_version="v1", screen_name="Login",
            reference="lib/scr-001",
        )
        element = _make_element(
            app_name="CMS", app_version="v1", screen_name="Login",
            element_name="btn", reference="lib/elem-001", parent_ref="lib/scr-001",
            scope_variables=["windowTitle"],
        )

        screen_node = ScreenNode(entry=screen)
        elem_node = ElementNode(entry=element)
        screen_node.elements.append(elem_node)

        version = VersionNode(name="v1", reference="lib/ver-001", parent_ref="lib/a1")
        version.screens.append(screen_node)
        app = AppNode(name="CMS", reference="lib/a1")
        app.versions.append(version)
        inv = Inventory(screens=[screen], elements=[element], apps=[app])

        result = format_tree_text(inv)
        assert "parameterized" in result

    def test_nested_elements_indented(self):
        screen = _make_screen(
            app_name="CMS", app_version="v1", screen_name="Login",
            reference="lib/scr-001",
        )
        parent_elem = _make_element(
            app_name="CMS", app_version="v1", screen_name="Login",
            element_name="form", reference="lib/elem-001", parent_ref="lib/scr-001",
        )
        child_elem = _make_element(
            app_name="CMS", app_version="v1", screen_name="Login",
            element_name="input", reference="lib/elem-002", parent_ref="lib/elem-001",
        )

        parent_node = ElementNode(entry=parent_elem)
        child_node = ElementNode(entry=child_elem)
        parent_node.children.append(child_node)

        screen_node = ScreenNode(entry=screen)
        screen_node.elements.append(parent_node)

        version = VersionNode(name="v1", reference="lib/ver-001", parent_ref="lib/a1")
        version.screens.append(screen_node)
        app = AppNode(name="CMS", reference="lib/a1")
        app.versions.append(version)
        inv = Inventory(screens=[screen], elements=[parent_elem, child_elem], apps=[app])

        result = format_tree_text(inv)
        assert "Element: form" in result
        assert "Element: input" in result
