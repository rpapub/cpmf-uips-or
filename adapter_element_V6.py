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

from .models import VariableDecl
from .parser import read_content_file, verify_xml_wellformed

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

    # Additional selector types
    fuzzy_selector: str = ""  # FuzzySelectorArgument
    has_image: bool = False  # ImageBase64 present and non-empty
    has_cv: bool = False  # CV attributes present
    cv_type: str = ""  # CvType (InputBox, Text, Button, etc.)

    # Runtime behavior attributes
    visibility: str = ""  # Visibility (Interactive, None, etc.)
    wait_for_ready: str = ""  # WaitForReadyArgument (Interactive, Complete, None)

    # Parsed attributes from selectors
    scope_attrs: dict[str, str] = field(default_factory=dict)
    selector_attrs: list[dict[str, str]] = field(default_factory=list)

    # Declared variables from ObjectRepositoryVariableData
    variables: list[VariableDecl] | None = None


def _unescape_xml(text: str) -> str:
    """Unescape XML entities."""
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&amp;", "&").replace("&quot;", '"')
    text = text.replace("&apos;", "'")
    return text


def _escape_xml(text: str) -> str:
    """Escape XML special characters for attribute values."""
    text = text.replace("&", "&amp;")  # Must be first
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def _escape_xml_selector(text: str) -> str:
    """Escape XML for selector strings (don't escape single quotes).

    UiPath stores selectors with single quotes unescaped inside double-quoted attributes:
    ScopeSelectorArgument="&lt;html app='chrome.exe' title='Google' /&gt;"
    """
    text = text.replace("&", "&amp;")  # Must be first
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    # Note: single quotes are NOT escaped in UiPath selector attributes
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

        # Extract FuzzySelectorArgument
        fuzzy_match = re.search(r'FuzzySelectorArgument="([^"]*)"', text)
        fuzzy_selector = _unescape_xml(fuzzy_match.group(1)) if fuzzy_match else ""

        # Extract ImageBase64 (check presence and non-empty)
        image_match = re.search(r'ImageBase64="([^"]*)"', text)
        has_image = bool(image_match and image_match.group(1))

        # Extract CV attributes
        cv_screen_match = re.search(r'CVScreenId="([^"]*)"', text)
        cv_type_match = re.search(r'CvType="([^"]*)"', text)
        has_cv = bool(cv_screen_match and cv_screen_match.group(1))
        cv_type = cv_type_match.group(1) if cv_type_match else ""

        # Extract runtime behavior attributes
        visibility_match = re.search(r'Visibility="([^"]*)"', text)
        visibility = visibility_match.group(1) if visibility_match else ""

        wait_for_ready_match = re.search(r'WaitForReadyArgument="([^"]*)"', text)
        wait_for_ready = wait_for_ready_match.group(1) if wait_for_ready_match else ""

        # Parse selector attributes
        scope_attrs = {}
        if scope_selector:
            parsed = _parse_selector_attrs(scope_selector)
            if parsed:
                scope_attrs = parsed[0]  # Scope usually has single element

        selector_attrs = _parse_selector_attrs(full_selector) if full_selector else []

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

        return ElementContent(
            version=version,
            search_steps=search_steps,
            scope_selector=scope_selector,
            full_selector=full_selector,
            browser_url=browser_url,
            element_type=element_type,
            activity_type=activity_type,
            screenshot=screenshot,
            fuzzy_selector=fuzzy_selector,
            has_image=has_image,
            has_cv=has_cv,
            cv_type=cv_type,
            visibility=visibility,
            wait_for_ready=wait_for_ready,
            scope_attrs=scope_attrs,
            selector_attrs=selector_attrs,
            variables=variables if variables else None,
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
        # Escape XML special chars in new value
        old_pattern = f"{attr}='{old_value}'"
        new_pattern = f"{attr}='{_escape_xml(new_value)}'"

        if old_pattern not in text:
            old_pattern = f'{attr}="{old_value}"'
            new_pattern = f'{attr}="{_escape_xml(new_value)}"'

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


def format_selector_with_variable(
    selector: str,
    attr: str,
    old_value: str,
    variable: str,
) -> str:
    """Format a selector with string.Format expression for variable substitution.

    UiPath requires the entire selector to be wrapped in a string.Format expression
    when parameterizing attribute values within selectors.

    Args:
        selector: Original selector string, e.g., "<html app='chrome.exe' title='Google' />"
        attr: Attribute name being parameterized, e.g., "title"
        old_value: Current attribute value, e.g., "Google"
        variable: Variable name, e.g., "windowTitle"

    Returns:
        Formatted expression, e.g., '[string.Format("<html ... title='{0}' />", windowTitle)]'
    """
    # Replace the attribute value with {0} placeholder
    # Handle both single and double quote styles
    new_selector = selector.replace(f"{attr}='{old_value}'", f"{attr}='{{0}}'")
    if new_selector == selector:
        new_selector = selector.replace(f'{attr}="{old_value}"', f'{attr}="{{0}}"')

    # Wrap in string.Format expression with quotes escaped for XML
    # Note: The selector inside string.Format needs regular quotes, not XML entities
    return f'[string.Format("{new_selector}", {variable})]'


def update_scope_selector_parameterized(
    path: Path,
    selector: str,
    attr: str,
    old_value: str,
    variable: str,
) -> bool:
    """Replace ScopeSelectorArgument with string.Format parameterized version.

    Args:
        path: Path to .content file
        selector: Original selector string (unescaped)
        attr: Attribute name being parameterized
        old_value: Current attribute value
        variable: Variable name

    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return False

    try:
        text, encoding = read_content_file(path)
        original_text = text

        # Build the new value using string.Format
        new_value = format_selector_with_variable(selector, attr, old_value, variable)

        # Replace the entire ScopeSelectorArgument attribute
        # Use _escape_xml_selector which doesn't escape single quotes (UiPath convention)
        escaped_old_selector = _escape_xml_selector(selector)
        escaped_new_value = _escape_xml_selector(new_value)

        old_attr = f'ScopeSelectorArgument="{escaped_old_selector}"'
        new_attr = f'ScopeSelectorArgument="{escaped_new_value}"'

        if old_attr not in text:
            return False

        new_text = text.replace(old_attr, new_attr)
        path.write_text(new_text, encoding=encoding)

        # Verify XML is well-formed
        is_valid, error = verify_xml_wellformed(path)
        if not is_valid:
            # Rollback
            path.write_text(original_text, encoding=encoding)
            return False

        return True
    except Exception:
        return False


def update_full_selector_parameterized(
    path: Path,
    selector: str,
    attr: str,
    old_value: str,
    variable: str,
) -> bool:
    """Replace FullSelectorArgument with string.Format parameterized version.

    Args:
        path: Path to .content file
        selector: Original selector string (unescaped)
        attr: Attribute name being parameterized
        old_value: Current attribute value
        variable: Variable name

    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return False

    try:
        text, encoding = read_content_file(path)
        original_text = text

        # Build the new value using string.Format
        new_value = format_selector_with_variable(selector, attr, old_value, variable)

        # Replace the entire FullSelectorArgument attribute
        # Use _escape_xml_selector which doesn't escape single quotes (UiPath convention)
        escaped_old_selector = _escape_xml_selector(selector)
        escaped_new_value = _escape_xml_selector(new_value)

        old_attr = f'FullSelectorArgument="{escaped_old_selector}"'
        new_attr = f'FullSelectorArgument="{escaped_new_value}"'

        if old_attr not in text:
            return False

        new_text = text.replace(old_attr, new_attr)
        path.write_text(new_text, encoding=encoding)

        # Verify XML is well-formed
        is_valid, error = verify_xml_wellformed(path)
        if not is_valid:
            # Rollback
            path.write_text(original_text, encoding=encoding)
            return False

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
    """Ensure ObjectRepositoryVariableData exists for variable (V6 Element).

    Handles:
    - List doesn't exist → create it with scg namespace if needed
    - List exists, var missing → add var to list
    - List exists, var present → update DefaultValue if different

    Args:
        path: Path to ObjectRepositoryTargetData/.content file
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

            # Insert variables list before </ObjectRepositoryTargetData.Data>
            new_list = VARIABLES_LIST_TEMPLATE.format(
                capacity=1,
                default_value=_escape_xml(default_value),
                name=variable_name,
            )
            insertion_point = "</ObjectRepositoryTargetData.Data>"
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
    """Remove ObjectRepositoryVariableData for variable (V6 Element).

    If this is the last variable, removes the entire list.
    Otherwise, removes just the entry and updates Capacity.

    Args:
        path: Path to ObjectRepositoryTargetData/.content file
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
