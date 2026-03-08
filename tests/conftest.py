"""Shared test fixtures for cpmf-uips-or tests."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_objects_dir(tmp_path: Path) -> Path:
    """Return an empty .objects directory."""
    objects_dir = tmp_path / ".objects"
    objects_dir.mkdir()
    return objects_dir


@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """Return a tmp dir with a minimal project.json and empty .objects."""
    (tmp_path / ".objects").mkdir()
    (tmp_path / "project.json").write_text(
        '{"name": "TestProject", "projectId": "abc123", '
        '"projectVersion": "1.0.0", "studioVersion": "24.0", '
        '"targetFramework": "Portable"}',
        encoding="utf-8",
    )
    return tmp_path
