"""Git integration for Object Repository diff.

Compare working tree vs commits to detect changes in .objects/
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .parser import read_content_file


@dataclass
class ObjectChange:
    """Represents a change to an object."""

    path: str
    change_type: str  # added, modified, deleted
    old_url: str | None = None
    new_url: str | None = None


def get_changed_content_files(
    project_dir: Path,
    ref: str = "HEAD",
) -> list[str]:
    """Get list of .content files changed since ref.

    Args:
        project_dir: Project directory containing .objects/
        ref: Git reference to compare against (default: HEAD)

    Returns:
        List of changed .content file paths (relative to project_dir)
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", ref, "--", ".objects/**/.content"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        files = result.stdout.strip().split("\n")
        return [f for f in files if f and f.endswith(".content")]
    except subprocess.CalledProcessError:
        return []


def get_file_at_ref(
    project_dir: Path,
    file_path: str,
    ref: str = "HEAD",
) -> str | None:
    """Get file content at a specific git ref.

    Args:
        project_dir: Project directory
        file_path: Relative path to file
        ref: Git reference

    Returns:
        File content or None if not found
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{file_path}"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def diff_objects(
    project_dir: Path,
    ref: str = "HEAD",
) -> list[ObjectChange]:
    """Compare object repository changes against a git ref.

    Args:
        project_dir: Project directory
        ref: Git reference to compare against

    Returns:
        List of ObjectChange objects
    """
    changes: list[ObjectChange] = []
    changed_files = get_changed_content_files(project_dir, ref)

    for file_path in changed_files:
        old_content = get_file_at_ref(project_dir, file_path, ref)
        full_path = project_dir / file_path

        if not full_path.exists():
            # Deleted
            changes.append(
                ObjectChange(
                    path=file_path,
                    change_type="deleted",
                )
            )
        elif old_content is None:
            # Added
            changes.append(
                ObjectChange(
                    path=file_path,
                    change_type="added",
                )
            )
        else:
            # Modified - extract URL changes
            old_url_match = re.search(r'Url="([^"]*)"', old_content)
            old_url = old_url_match.group(1) if old_url_match else None

            new_content, _ = read_content_file(full_path)
            new_url_match = re.search(r'Url="([^"]*)"', new_content)
            new_url = new_url_match.group(1) if new_url_match else None

            if old_url != new_url:
                changes.append(
                    ObjectChange(
                        path=file_path,
                        change_type="modified",
                        old_url=old_url,
                        new_url=new_url,
                    )
                )

    return changes
