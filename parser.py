"""Parsers for Object Repository files.

Handles:
- .metadata (JSON) - Identity and hierarchy
- .content (XML) - TargetApp descriptors
  Note: .content files declare utf-16 in XML header but are typically UTF-8.
  May use actual UTF-16 when special characters are present.
"""

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


def _is_valid_content(text: str) -> bool:
    """Check if decoded text looks like valid .content XML.

    Uses Version="V2" as a key marker since it appears at a known
    location in all valid Screen .content files.
    """
    return 'Version="V2"' in text or "<?xml" in text[:100]


def read_content_file(path: Path) -> tuple[str, str]:
    """Read .content file with encoding auto-detection.

    Tries UTF-8 first, then UTF-16 variants if that fails.
    Validates by checking for Version="V2" marker.

    Args:
        path: Path to .content file

    Returns:
        Tuple of (text content, detected encoding)

    Raises:
        UnicodeDecodeError: If no encoding works
    """
    data = path.read_bytes()

    # Check for BOM to detect encoding
    if data[:2] == b"\xff\xfe":
        return data.decode("utf-16-le"), "utf-16-le"
    if data[:2] == b"\xfe\xff":
        return data.decode("utf-16-be"), "utf-16-be"

    # Try UTF-8 first (most common case)
    try:
        text = data.decode("utf-8")
        if _is_valid_content(text):
            return text, "utf-8"
    except UnicodeDecodeError:
        pass

    # Fallback to UTF-16 without BOM
    for enc in ["utf-16-le", "utf-16-be"]:
        try:
            text = data.decode(enc)
            if _is_valid_content(text):
                return text, enc
        except UnicodeDecodeError:
            continue

    # Last resort - force UTF-8
    return data.decode("utf-8", errors="replace"), "utf-8"


def verify_xml_wellformed(path: Path) -> tuple[bool, str | None]:
    """Verify that a .content file is well-formed XML.

    Args:
        path: Path to .content file

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if XML is well-formed
        - (False, error_message) if XML is malformed
    """
    if not path.exists():
        return False, f"File not found: {path}"

    try:
        text, _ = read_content_file(path)
        ET.fromstring(text)
        return True, None
    except ET.ParseError as e:
        return False, f"XML parse error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


@dataclass
class Metadata:
    """Parsed .metadata file."""

    name: str
    type: str  # App, AppVersion, Screen, Element
    id: str
    reference: str
    parent_ref: str | None = None
    # Audit metadata
    created: str | None = None  # ISO 8601 timestamp
    updated: str | None = None  # ISO 8601 timestamp
    created_by: list[str] | None = None  # UiPath platform version array
    updated_by: list[str] | None = None  # UiPath platform version array


@dataclass
class ContentData:
    """Parsed .content file (TargetApp)."""

    url: str
    selector: str
    version: str  # V2, etc.
    browser_type: str | None = None


def parse_metadata(path: Path) -> Metadata | None:
    """Parse a .metadata JSON file.

    Args:
        path: Path to .metadata file

    Returns:
        Metadata object or None if file doesn't exist/is invalid
    """
    if not path.exists():
        return None

    try:
        # Handle BOM (utf-8-sig)
        text = path.read_text(encoding="utf-8-sig")
        data = json.loads(text)

        return Metadata(
            name=data.get("Name", ""),
            type=data.get("Type", ""),
            id=data.get("Id", ""),
            reference=data.get("Reference", ""),
            parent_ref=data.get("ParentRef"),
            created=data.get("Created"),
            updated=data.get("Updated"),
            created_by=data.get("CreatedBy"),
            updated_by=data.get("UpdatedBy"),
        )
    except (json.JSONDecodeError, KeyError):
        return None


def parse_content(path: Path) -> ContentData | None:
    """Parse a .content XML file for TargetApp data.

    Args:
        path: Path to .content file

    Returns:
        ContentData object or None if file doesn't exist/is invalid
    """
    if not path.exists():
        return None

    try:
        text, _ = read_content_file(path)

        # Extract Version attribute
        version_match = re.search(r'Version="([^"]*)"', text)
        version = version_match.group(1) if version_match else ""

        # Extract Url attribute
        url_match = re.search(r'Url="([^"]*)"', text)
        url = url_match.group(1) if url_match else ""

        # Extract Selector attribute (XML-escaped)
        selector_match = re.search(r'Selector="([^"]*)"', text)
        selector = ""
        if selector_match:
            selector = selector_match.group(1)
            selector = selector.replace("&lt;", "<").replace("&gt;", ">")
            selector = selector.replace("&amp;", "&").replace("&quot;", '"')

        # Extract BrowserType attribute
        browser_match = re.search(r'BrowserType="([^"]*)"', text)
        browser_type = browser_match.group(1) if browser_match else None

        return ContentData(
            url=url,
            selector=selector,
            version=version,
            browser_type=browser_type,
        )
    except Exception:
        return None


def update_content_url(path: Path, old_url: str, new_url: str) -> bool:
    """Update the URL in a .content file.

    Preserves the original file encoding.

    Args:
        path: Path to .content file
        old_url: Current URL value
        new_url: New URL value

    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return False

    try:
        text, encoding = read_content_file(path)

        # Replace the URL attribute value
        old_attr = f'Url="{old_url}"'
        new_attr = f'Url="{new_url}"'

        if old_attr not in text:
            return False

        new_text = text.replace(old_attr, new_attr)
        path.write_text(new_text, encoding=encoding)
        return True
    except Exception:
        return False
