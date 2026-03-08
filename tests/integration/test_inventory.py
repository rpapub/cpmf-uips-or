"""Integration tests — requires a real UiPath project corpus.

Skipped automatically if the corpus path is not present on this machine.
"""

from pathlib import Path

import pytest

from cpmf_uips_or.discovery import discover_inventory, find_objects_dir

# Adjust this path to any local corpus that has a .objects directory
_CORPUS_PROJECT = Path(
    "D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001/project.json"
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def corpus_objects_dir():
    if not _CORPUS_PROJECT.exists():
        pytest.skip(f"Corpus not available: {_CORPUS_PROJECT}")
    return find_objects_dir(_CORPUS_PROJECT)


def test_discover_inventory_no_crash(corpus_objects_dir: Path):
    """discover_inventory must complete without raising on the real corpus."""
    inv = discover_inventory(corpus_objects_dir)
    # Just verify structural integrity
    assert inv is not None
    assert isinstance(inv.screens, list)
    assert isinstance(inv.elements, list)
    assert isinstance(inv.apps, list)


def test_inventory_screens_have_valid_versions(corpus_objects_dir: Path):
    inv = discover_inventory(corpus_objects_dir)
    for screen in inv.screens:
        assert screen.descriptor_version, f"Missing version for {screen.full_path}"


def test_inventory_elements_have_valid_versions(corpus_objects_dir: Path):
    inv = discover_inventory(corpus_objects_dir)
    for elem in inv.elements:
        assert elem.descriptor_version, f"Missing version for {elem.full_path}"
