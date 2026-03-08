"""Tests for discovery traversal with a synthetic .objects directory."""

import json
from pathlib import Path

import pytest

from cpmf_uips_or.discovery import discover_all, discover_inventory
from cpmf_uips_or.models import UrlStatus
from tests.unit.conftest import (
    ELEMENT_V6_XML,
    SCREEN_V2_XML,
)


def _write_metadata(folder: Path, name: str, type_: str, ref: str, parent_ref: str | None = None):
    folder.mkdir(parents=True, exist_ok=True)
    meta = {
        "Name": name,
        "Type": type_,
        "Id": ref.split("/")[-1],
        "Reference": ref,
    }
    if parent_ref:
        meta["ParentRef"] = parent_ref
    (folder / ".metadata").write_text(json.dumps(meta), encoding="utf-8")
    (folder / ".type").write_text(type_, encoding="utf-8")


def _write_screen_content(content_dir: Path, url: str = "https://example.com"):
    """Write a minimal TargetApp .content file for a screen."""
    content_dir.mkdir(parents=True, exist_ok=True)
    xml = SCREEN_V2_XML.replace("https://example.com/login", url)
    (content_dir / ".content").write_text(xml, encoding="utf-8")


def _write_element_content(content_dir: Path):
    """Write a minimal TargetAnchorable .content file for an element."""
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / ".content").write_text(ELEMENT_V6_XML, encoding="utf-8")


@pytest.fixture
def synthetic_objects_dir(tmp_path: Path) -> Path:
    """Create a minimal .objects structure:
    Library
      App: CMS
        AppVersion: 2026-01
          Screen: Login
            Element: username
    """
    objects_dir = tmp_path / ".objects"
    objects_dir.mkdir()

    # Library-level metadata
    _write_metadata(objects_dir, "MyLibrary", "Library", "lib/root")

    # App
    app_dir = objects_dir / "CMS"
    _write_metadata(app_dir, "CMS", "App", "lib/app-001")

    # AppVersion
    version_dir = app_dir / "v1"
    _write_metadata(version_dir, "2026-01", "AppVersion", "lib/ver-001", parent_ref="lib/app-001")

    # Screen
    screen_dir = version_dir / "Login"
    _write_metadata(
        screen_dir, "Login", "Screen", "lib/scr-001", parent_ref="lib/ver-001"
    )
    _write_screen_content(
        screen_dir / ".data" / "ObjectRepositoryScreenData",
        url="https://example.com/login",
    )

    # Element
    elem_dir = screen_dir / "username"
    _write_metadata(
        elem_dir, "username", "Element", "lib/elem-001", parent_ref="lib/scr-001"
    )
    _write_element_content(elem_dir / ".data" / "ObjectRepositoryTargetData")

    return objects_dir


class TestSyntheticTraversal:
    def test_discovers_screen(self, synthetic_objects_dir: Path):
        inv = discover_inventory(synthetic_objects_dir)
        assert len(inv.screens) == 1
        assert inv.screens[0].screen_name == "Login"
        assert inv.screens[0].url == "https://example.com/login"
        assert inv.screens[0].url_status == UrlStatus.HARDCODED

    def test_discovers_element(self, synthetic_objects_dir: Path):
        inv = discover_inventory(synthetic_objects_dir)
        assert len(inv.elements) == 1
        assert inv.elements[0].element_name == "username"
        assert inv.elements[0].element_type == "InputBox"

    def test_builds_hierarchy(self, synthetic_objects_dir: Path):
        inv = discover_inventory(synthetic_objects_dir)
        assert len(inv.apps) == 1
        app = inv.apps[0]
        assert app.name == "CMS"
        assert len(app.versions) == 1
        version = app.versions[0]
        assert version.name == "2026-01"
        assert len(version.screens) == 1

    def test_element_under_screen_in_hierarchy(self, synthetic_objects_dir: Path):
        inv = discover_inventory(synthetic_objects_dir)
        screen_node = inv.apps[0].versions[0].screens[0]
        assert len(screen_node.elements) == 1
        assert screen_node.elements[0].entry.element_name == "username"

    def test_references_populated(self, synthetic_objects_dir: Path):
        inv = discover_inventory(synthetic_objects_dir)
        assert inv.screens[0].reference == "lib/scr-001"
        assert inv.elements[0].reference == "lib/elem-001"
        assert inv.elements[0].parent_ref == "lib/scr-001"

    def test_by_reference_lookup(self, synthetic_objects_dir: Path):
        inv = discover_inventory(synthetic_objects_dir)
        assert "lib/scr-001" in inv._by_reference
        assert "lib/elem-001" in inv._by_reference

    def test_discover_all_returns_flat_lists(self, synthetic_objects_dir: Path):
        screens, elements = discover_all(synthetic_objects_dir)
        assert len(screens) == 1
        assert len(elements) == 1
