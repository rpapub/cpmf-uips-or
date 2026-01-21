"""Element adapter for V6 Object Repository format.

Handles ObjectRepositoryTargetData with TargetAnchorable element.
Selector parameterization uses [varName] syntax within attribute values.

SearchSteps attribute indicates targeting strategy:
- "Selector" - selector-only targeting
- "Selector, Image" - selector with image fallback
- "Selector, Image, CV" - selector with image and computer vision
- etc.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .parser import read_content_file

VERSION = "V6"

# V6 uses same [variableName] syntax as V2
VARIABLE_PATTERN = re.compile(r"\[([^\]]+)\]")


@dataclass
class ElementContent:
    """Parsed Element .content file (TargetAnchorable)."""

    version: str
    search_steps: str  # Targeting strategy (Selector, Image, CV, etc.)
    scope_selector: str  # ScopeSelectorArgument (window/browser scope)
    full_selector: str  # FullSelectorArgument (element selector)
    browser_url: str  # Informational only, not used for targeting
    element_type: str  # Text, InputBox, Button, etc.
    activity_type: str  # Click, TypeInto, etc.
    screenshot: str | None = None  # InformativeScreenshot filename

    # Parsed attributes from selectors
    scope_attrs: dict[str, str] = field(default_factory=dict)
    selector_attrs: list[dict[str, str]] = field(default_factory=list)


def _unescape_xml(text: str) -> str:
    """Unescape XML entities."""
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&amp;", "&").replace("&quot;", '"')
    text = text.replace("&apos;", "'")
    return text


def _parse_selector_attrs(selector: str) -> list[dict[str, str]]:
    """Parse selector string into list of attribute dicts.

    Example: "<webctrl id='foo' tag='DIV' /><webctrl name='bar' />"
    Returns: [{"id": "foo", "tag": "DIV"}, {"name": "bar"}]
    """
    result = []
    # Match each <ctrl .../> or <webctrl .../> or <html .../> etc.
    for match in re.finditer(r"<(\w+)\s+([^>]*)/>", selector):
        tag = match.group(1)
        attrs_str = match.group(2)
        attrs = {"_tag": tag}

        # Parse attributes: name='value' or name="value"
        for attr_match in re.finditer(r"(\w+)=['\"]([^'\"]*)['\"]", attrs_str):
            attrs[attr_match.group(1)] = attr_match.group(2)

        result.append(attrs)

    return result


def parse_content(path: Path) -> ElementContent | None:
    """Parse an Element .content XML file for TargetAnchorable data.

    Args:
        path: Path to ObjectRepositoryTargetData/.content file

    Returns:
        ElementContent object or None if file doesn't exist/is invalid
    """
    if not path.exists():
        return None

    try:
        text, _ = read_content_file(path)

        # Verify this is an Element content file (has TargetAnchorable)
        if "TargetAnchorable" not in text:
            return None

        # Extract Version attribute
        version_match = re.search(r'Version="([^"]*)"', text)
        version = version_match.group(1) if version_match else ""

        # Extract SearchSteps attribute (important for targeting strategy)
        search_match = re.search(r'SearchSteps="([^"]*)"', text)
        search_steps = search_match.group(1) if search_match else ""

        # Extract ScopeSelectorArgument (window/browser scope)
        scope_match = re.search(r'ScopeSelectorArgument="([^"]*)"', text)
        scope_selector = _unescape_xml(scope_match.group(1)) if scope_match else ""

        # Extract FullSelectorArgument (element selector)
        full_match = re.search(r'FullSelectorArgument="([^"]*)"', text)
        full_selector = _unescape_xml(full_match.group(1)) if full_match else ""

        # Extract BrowserURL (informational only)
        browser_match = re.search(r'BrowserURL="([^"]*)"', text)
        browser_url = browser_match.group(1) if browser_match else ""

        # Extract ElementType
        elem_type_match = re.search(r'ElementType="([^"]*)"', text)
        element_type = elem_type_match.group(1) if elem_type_match else ""

        # Extract ActivityType
        activity_match = re.search(r'<x:String x:Key="ActivityType">([^<]*)</x:String>', text)
        activity_type = activity_match.group(1) if activity_match else ""

        # Extract InformativeScreenshot filename
        screenshot_match = re.search(
            r'<imageRef[^>]*attrName="InformativeScreenshot"[^>]*originalValue="([^"]*)"', text
        )
        screenshot = screenshot_match.group(1) if screenshot_match else None

        # Parse selector attributes
        scope_attrs = {}
        if scope_selector:
            parsed = _parse_selector_attrs(scope_selector)
            if parsed:
                scope_attrs = parsed[0]  # Scope usually has single element

        selector_attrs = _parse_selector_attrs(full_selector) if full_selector else []

        return ElementContent(
            version=version,
            search_steps=search_steps,
            scope_selector=scope_selector,
            full_selector=full_selector,
            browser_url=browser_url,
            element_type=element_type,
            activity_type=activity_type,
            screenshot=screenshot,
            scope_attrs=scope_attrs,
            selector_attrs=selector_attrs,
        )
    except Exception:
        return None


def format_variable(variable: str) -> str:
    """Format a variable name into V6 selector syntax.

    Args:
        variable: The variable name (e.g., "windowTitle")

    Returns:
        Formatted string (e.g., "[windowTitle]")
    """
    return f"[{variable}]"


def extract_variables(value: str) -> list[str]:
    """Extract all variable names from a parameterized value.

    Args:
        value: The attribute value (e.g., "[title]" or "prefix[var]suffix")

    Returns:
        List of variable names found
    """
    return VARIABLE_PATTERN.findall(value)


def is_parameterized(value: str) -> bool:
    """Check if value contains any variables."""
    return bool(VARIABLE_PATTERN.search(value))


def is_version_supported(version: str) -> bool:
    """Check if a descriptor version is supported for mutations."""
    return version == VERSION


def update_scope_attr(path: Path, attr: str, old_value: str, new_value: str) -> bool:
    """Update an attribute in ScopeSelectorArgument.

    Args:
        path: Path to .content file
        attr: Attribute name (e.g., "title")
        old_value: Current attribute value
        new_value: New attribute value

    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return False

    try:
        text, encoding = read_content_file(path)

        # Find and update the attribute in ScopeSelectorArgument
        # Pattern: attr='old_value' or attr="old_value"
        old_pattern = f"{attr}='{old_value}'"
        new_pattern = f"{attr}='{new_value}'"

        if old_pattern not in text:
            old_pattern = f'{attr}="{old_value}"'
            new_pattern = f'{attr}="{new_value}"'

        if old_pattern not in text:
            return False

        new_text = text.replace(old_pattern, new_pattern)
        path.write_text(new_text, encoding=encoding)
        return True
    except Exception:
        return False


def update_selector_attr(path: Path, attr: str, old_value: str, new_value: str) -> bool:
    """Update an attribute in FullSelectorArgument.

    Args:
        path: Path to .content file
        attr: Attribute name (e.g., "id")
        old_value: Current attribute value
        new_value: New attribute value

    Returns:
        True if successful, False otherwise
    """
    # Same implementation as update_scope_attr since both are in the same file
    return update_scope_attr(path, attr, old_value, new_value)
