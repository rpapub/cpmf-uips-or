"""Screen adapter for V2 Object Repository format.

Handles ObjectRepositoryScreenData with TargetApp element.
URL parameterization uses [varName] syntax.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from .models import VariableDecl
from .parser import read_content_file, verify_xml_wellformed

VERSION = "V2"

# V2 syntax: [variableName]
VARIABLE_TEMPLATE = "[{variable}]"
VARIABLE_PATTERN = re.compile(r"^\[([^\]]+)\](.*)$")  # Captures variable and optional suffix


def _escape_xml(text: str) -> str:
    """Escape XML special characters for attribute values."""
    text = text.replace("&", "&amp;")  # Must be first
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


@dataclass
class ScreenContent:
    """Parsed Screen .content file (TargetApp)."""

    url: str
    selector: str
    version: str
    browser_type: str | None = None
    screenshot: str | None = None  # InformativeScreenshot filename
    variables: list[VariableDecl] | None = None  # ObjectRepositoryVariableData entries


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

        # Extract ObjectRepositoryVariableData (Name and DefaultValue)
        variables: list[VariableDecl] = []
        for var_match in re.finditer(r'<ObjectRepositoryVariableData\s+([^>]*)/?>', text):
            attrs = var_match.group(1)
            name_match = re.search(r'Name="([^"]*)"', attrs)
            default_match = re.search(r'DefaultValue="([^"]*)"', attrs)
            if name_match:
                name = name_match.group(1)
                default = default_match.group(1) if default_match else "*"
                variables.append(VariableDecl(name=name, default=default))

        return ScreenContent(
            url=url,
            selector=selector,
            version=version,
            browser_type=browser_type,
            screenshot=screenshot,
            variables=variables if variables else None,
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

        # Replace the URL attribute value (escape XML special chars in new value)
        old_attr = f'Url="{old_url}"'
        new_attr = f'Url="{_escape_xml(new_url)}"'

        if old_attr not in text:
            return False

        new_text = text.replace(old_attr, new_attr)
        path.write_text(new_text, encoding=encoding)
        return True
    except Exception:
        return False


def update_selector_attr(path: Path, attr: str, old_value: str, new_value: str) -> bool:
    """Update an attribute within the Screen's Selector.

    The Selector attribute is XML-escaped in the .content file, e.g.:
    Selector="&lt;html app='chrome.exe' title='Login Page' /&gt;"

    This function finds attr='old_value' within the unescaped selector,
    replaces it with attr='new_value', and writes back properly escaped.

    Args:
        path: Path to .content file
        attr: Attribute name (e.g., "title", "app")
        old_value: Current attribute value
        new_value: New attribute value (may contain [variable])

    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return False

    try:
        text, encoding = read_content_file(path)

        # Find the Selector attribute (XML-escaped)
        selector_match = re.search(r'Selector="([^"]*)"', text)
        if not selector_match:
            return False

        escaped_selector = selector_match.group(1)

        # Build the old pattern (within the escaped selector)
        # The selector attribute values use single quotes inside, e.g., title='Login'
        # These are escaped as &apos; but often left as single quotes
        old_pattern_sq = f"{attr}='{old_value}'"
        old_pattern_dq = f'{attr}="{old_value}"'

        # Check which quote style is used (with XML escaping)
        if old_pattern_sq in escaped_selector:
            new_pattern = f"{attr}='{_escape_xml(new_value)}'"
            new_escaped_selector = escaped_selector.replace(old_pattern_sq, new_pattern)
        elif old_pattern_dq in escaped_selector:
            new_pattern = f'{attr}="{_escape_xml(new_value)}"'
            new_escaped_selector = escaped_selector.replace(old_pattern_dq, new_pattern)
        else:
            # Try with XML entity escapes in the old value
            escaped_old = old_value.replace("'", "&apos;")
            old_pattern_esc = f"{attr}='{escaped_old}'"
            if old_pattern_esc in escaped_selector:
                new_pattern = f"{attr}='{_escape_xml(new_value)}'"
                new_escaped_selector = escaped_selector.replace(old_pattern_esc, new_pattern)
            else:
                return False

        # Replace in the full text
        old_full = f'Selector="{escaped_selector}"'
        new_full = f'Selector="{new_escaped_selector}"'

        new_text = text.replace(old_full, new_full)
        path.write_text(new_text, encoding=encoding)
        return True
    except Exception:
        return False


# ---------- ObjectRepositoryVariableData management ----------

# XML templates for variable declarations
VARIABLES_LIST_TEMPLATE = """    <scg:List x:TypeArguments="ObjectRepositoryVariableData" x:Key="Variables" Capacity="{capacity}">
      <ObjectRepositoryVariableData DefaultValue="{default_value}" Name="{name}" />
    </scg:List>
"""

VARIABLE_ENTRY_TEMPLATE = """      <ObjectRepositoryVariableData DefaultValue="{default_value}" Name="{name}" />
"""

# Regex patterns for variable list manipulation
VARIABLES_LIST_PATTERN = re.compile(
    r'<scg:List\s+x:TypeArguments="ObjectRepositoryVariableData"[^>]*>.*?</scg:List>',
    re.DOTALL,
)
VARIABLE_ENTRY_PATTERN = re.compile(
    r'<ObjectRepositoryVariableData[^>]*Name="([^"]*)"[^>]*/?>',
)
CAPACITY_PATTERN = re.compile(r'Capacity="(\d+)"')
SCG_NAMESPACE_PATTERN = re.compile(r'xmlns:scg="[^"]*"')


def ensure_variable(path: Path, variable_name: str, default_value: str = "*") -> bool:
    """Ensure ObjectRepositoryVariableData exists for variable (V2 Screen).

    Handles:
    - List doesn't exist → create it with scg namespace if needed
    - List exists, var missing → add var to list
    - List exists, var present → update DefaultValue if different

    Args:
        path: Path to ObjectRepositoryScreenData/.content file
        variable_name: Variable name to ensure exists
        default_value: DefaultValue attribute (default "*")

    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return False

    try:
        text, encoding = read_content_file(path)
        original_text = text  # Keep original for rollback

        # Check if variables list exists
        list_match = VARIABLES_LIST_PATTERN.search(text)
        new_text = None

        if list_match:
            # List exists - check if variable is already in it
            list_content = list_match.group(0)
            existing_vars = VARIABLE_ENTRY_PATTERN.findall(list_content)

            if variable_name in existing_vars:
                # Variable exists - update DefaultValue if needed
                old_entry_pattern = re.compile(
                    rf'<ObjectRepositoryVariableData[^>]*Name="{re.escape(variable_name)}"[^>]*/?>',
                )
                old_entry_match = old_entry_pattern.search(list_content)
                if old_entry_match:
                    old_entry = old_entry_match.group(0)
                    # Check if DefaultValue needs updating
                    if f'DefaultValue="{default_value}"' in old_entry:
                        return True  # Already correct
                    # Build new entry
                    new_entry = f'<ObjectRepositoryVariableData DefaultValue="{_escape_xml(default_value)}" Name="{variable_name}" />'
                    new_list_content = list_content.replace(old_entry, new_entry)
                    new_text = text.replace(list_content, new_list_content)
            else:
                # Variable not in list - add it
                new_entry = VARIABLE_ENTRY_TEMPLATE.format(
                    default_value=_escape_xml(default_value),
                    name=variable_name,
                )
                # Insert before </scg:List>
                new_list_content = list_content.replace(
                    "</scg:List>",
                    new_entry + "    </scg:List>",
                )
                # Update Capacity
                new_capacity = len(existing_vars) + 1
                new_list_content = CAPACITY_PATTERN.sub(
                    f'Capacity="{new_capacity}"',
                    new_list_content,
                )
                new_text = text.replace(list_content, new_list_content)
        else:
            # List doesn't exist - create it
            # First, ensure scg namespace is declared
            if not SCG_NAMESPACE_PATTERN.search(text):
                # Add scg namespace to root element
                text = text.replace(
                    'xmlns="http://schemas.uipath.com/workflow/activities/uix"',
                    'xmlns="http://schemas.uipath.com/workflow/activities/uix" '
                    'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"',
                )

            # Insert variables list before </ObjectRepositoryScreenData.Data>
            new_list = VARIABLES_LIST_TEMPLATE.format(
                capacity=1,
                default_value=_escape_xml(default_value),
                name=variable_name,
            )
            insertion_point = "</ObjectRepositoryScreenData.Data>"
            new_text = text.replace(
                insertion_point,
                new_list + "  " + insertion_point,
            )

        if new_text:
            path.write_text(new_text, encoding=encoding)
            # Verify XML is well-formed
            is_valid, error = verify_xml_wellformed(path)
            if not is_valid:
                # Rollback to original
                path.write_text(original_text, encoding=encoding)
                return False

        return True

    except Exception:
        return False


def remove_variable(path: Path, variable_name: str) -> bool:
    """Remove ObjectRepositoryVariableData for variable (V2 Screen).

    If this is the last variable, removes the entire list.
    Otherwise, removes just the entry and updates Capacity.

    Args:
        path: Path to ObjectRepositoryScreenData/.content file
        variable_name: Variable name to remove

    Returns:
        True if successful (or variable didn't exist), False on error
    """
    if not path.exists():
        return False

    try:
        text, encoding = read_content_file(path)
        original_text = text  # Keep original for rollback

        # Check if variables list exists
        list_match = VARIABLES_LIST_PATTERN.search(text)

        if not list_match:
            return True  # Nothing to remove

        list_content = list_match.group(0)
        existing_vars = VARIABLE_ENTRY_PATTERN.findall(list_content)

        if variable_name not in existing_vars:
            return True  # Variable doesn't exist

        new_text = None
        if len(existing_vars) == 1:
            # Last variable - remove entire list
            # Also remove the leading whitespace/newline
            list_with_whitespace = re.compile(
                r'\s*<scg:List\s+x:TypeArguments="ObjectRepositoryVariableData"[^>]*>.*?</scg:List>\s*',
                re.DOTALL,
            )
            new_text = list_with_whitespace.sub("\n  ", text)
        else:
            # Remove just this entry
            entry_pattern = re.compile(
                rf'\s*<ObjectRepositoryVariableData[^>]*Name="{re.escape(variable_name)}"[^>]*/?>',
            )
            new_list_content = entry_pattern.sub("", list_content)
            # Update Capacity
            new_capacity = len(existing_vars) - 1
            new_list_content = CAPACITY_PATTERN.sub(
                f'Capacity="{new_capacity}"',
                new_list_content,
            )
            new_text = text.replace(list_content, new_list_content)

        if new_text:
            path.write_text(new_text, encoding=encoding)
            # Verify XML is well-formed
            is_valid, error = verify_xml_wellformed(path)
            if not is_valid:
                # Rollback to original
                path.write_text(original_text, encoding=encoding)
                return False

        return True

    except Exception:
        return False
