"""Screen adapter for V2 Object Repository format.

Handles ObjectRepositoryScreenData with TargetApp element.
URL parameterization uses [varName] syntax.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from .parser import read_content_file

VERSION = "V2"

# V2 syntax: [variableName]
VARIABLE_TEMPLATE = "[{variable}]"
VARIABLE_PATTERN = re.compile(r"^\[([^\]]+)\](.*)$")  # Captures variable and optional suffix


@dataclass
class ScreenContent:
    """Parsed Screen .content file (TargetApp)."""

    url: str
    selector: str
    version: str
    browser_type: str | None = None
    screenshot: str | None = None  # InformativeScreenshot filename


def parse_content(path: Path) -> ScreenContent | None:
    """Parse a Screen .content XML file for TargetApp data.

    Args:
        path: Path to ObjectRepositoryScreenData/.content file

    Returns:
        ScreenContent object or None if file doesn't exist/is invalid
    """
    if not path.exists():
        return None

    try:
        text, _ = read_content_file(path)

        # Verify this is a Screen content file (has TargetApp)
        if "TargetApp" not in text:
            return None

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

        # Extract InformativeScreenshot filename
        screenshot_match = re.search(
            r'<imageRef[^>]*attrName="InformativeScreenshot"[^>]*originalValue="([^"]*)"', text
        )
        screenshot = screenshot_match.group(1) if screenshot_match else None

        return ScreenContent(
            url=url,
            selector=selector,
            version=version,
            browser_type=browser_type,
            screenshot=screenshot,
        )
    except Exception:
        return None


def format_variable(variable: str) -> str:
    """Format a variable name into V2 URL syntax.

    Args:
        variable: The variable name (e.g., "baseUrl")

    Returns:
        Formatted URL string (e.g., "[baseUrl]")
    """
    return VARIABLE_TEMPLATE.format(variable=variable)


def extract_variable(url: str) -> tuple[str | None, str]:
    """Extract variable name from parameterized URL.

    Args:
        url: The URL string (e.g., "[baseUrl]" or "[baseUrl]path/to/page")

    Returns:
        Tuple of (variable_name, suffix) where variable_name is None if hardcoded
    """
    match = VARIABLE_PATTERN.match(url)
    if match:
        return match.group(1), match.group(2)
    return None, ""


def is_parameterized(url: str) -> bool:
    """Check if URL is parameterized (uses a variable)."""
    return url.startswith("[") and "]" in url


def is_version_supported(version: str) -> bool:
    """Check if a descriptor version is supported for mutations."""
    return version == VERSION


def update_content(path: Path, old_url: str, new_url: str) -> bool:
    """Update the URL in a Screen .content file.

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
