"""Rules loading and application.

Loads replacement rules from TOML config files.
Supports both V2 Screens (URL) and V6 Elements (selector attributes).

Rule targeting:
- target = "all" (default): applies to all types
- target = "screen": V2 Screen URLs only
- target = "element.scope": V6 ScopeSelectorArgument only
- target = "element.selector": V6 FullSelectorArgument only

Cascade:
- cascade = true on screen.selector rules cascades to descendant element.scope
- Uses parent_ref chain to find all elements under a screen (including nested)
"""

import html
import tomllib
from fnmatch import fnmatch
from pathlib import Path

from . import adapter_element_V6 as element_adapter
from . import adapter_screen_V2 as screen_adapter
from .models import (
    AnyEntry,
    ElementEntry,
    EntryType,
    ParameterizeRule,
    RenameRule,
    ReplacePreview,
    ReplaceRule,
    ResetRule,
    RuleTarget,
    ScreenEntry,
    UrlStatus,
)


def _parse_target(target_str: str | None) -> RuleTarget:
    """Parse target string to RuleTarget enum."""
    if not target_str or target_str == "all":
        return RuleTarget.ALL
    elif target_str == "screen":
        return RuleTarget.SCREEN
    elif target_str == "screen.selector":
        return RuleTarget.SCREEN_SELECTOR
    elif target_str == "element.scope":
        return RuleTarget.ELEMENT_SCOPE
    elif target_str == "element.selector":
        return RuleTarget.ELEMENT_SELECTOR
    else:
        raise ValueError(f"Unknown target: {target_str}")


# ============================================================================
# Cascade helper functions
# ============================================================================


def find_root_screen(
    element: ElementEntry,
    screens_by_ref: dict[str, ScreenEntry],
    elements_by_ref: dict[str, ElementEntry],
) -> ScreenEntry | None:
    """Traverse parent_ref chain to find the ancestor screen.

    Handles nested elements by following the chain:
    NestedElement -> ParentElement -> ... -> Screen

    Args:
        element: The element to find the root screen for
        screens_by_ref: Lookup of screens by reference
        elements_by_ref: Lookup of elements by reference

    Returns:
        The ancestor ScreenEntry, or None if not found
    """
    parent_ref = element.parent_ref
    while parent_ref:
        if parent_ref in screens_by_ref:
            return screens_by_ref[parent_ref]
        if parent_ref in elements_by_ref:
            parent_ref = elements_by_ref[parent_ref].parent_ref
        else:
            break
    return None


def find_descendant_elements(
    screen: ScreenEntry,
    elements: list[ElementEntry],
    elements_by_ref: dict[str, ElementEntry],
) -> list[ElementEntry]:
    """Find all elements that are descendants of a screen (including nested).

    Args:
        screen: The screen to find descendants for
        elements: All elements to search
        elements_by_ref: Lookup of elements by reference

    Returns:
        List of all descendant elements
    """
    screens_by_ref = {screen.reference: screen}
    descendants = []
    for elem in elements:
        root = find_root_screen(elem, screens_by_ref, elements_by_ref)
        if root and root.reference == screen.reference:
            descendants.append(elem)
    return descendants


def _extract_selector_attr_value(selector: str, attr_name: str) -> str | None:
    """Extract an attribute value from a selector XML string.

    Args:
        selector: The selector XML string (may be escaped)
        attr_name: The attribute name to extract (e.g., "title")

    Returns:
        The attribute value, or None if not found
    """
    # Unescape the selector
    unescaped = html.unescape(selector)

    # Simple regex-free extraction: find attr='value' or attr="value"
    for quote in ["'", '"']:
        pattern = f"{attr_name}={quote}"
        start = unescaped.find(pattern)
        if start != -1:
            start += len(pattern)
            end = unescaped.find(quote, start)
            if end != -1:
                return unescaped[start:end]
    return None


def load_rules(config_path: Path) -> list[ReplaceRule]:
    """Load replacement rules from TOML config file.

    Args:
        config_path: Path to TOML config file

    Returns:
        List of ReplaceRule objects

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config format is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    rules: list[ReplaceRule] = []

    for rule_data in config.get("rules", []):
        rule_type = rule_data.get("type", "")
        target = _parse_target(rule_data.get("target"))

        if rule_type == "parameterize":
            # Hardcoded value -> variable
            match = rule_data.get("match", "")
            variable = rule_data.get("variable", "")
            attribute = rule_data.get("attribute")  # For element rules
            default_value = rule_data.get("default_value", "*")  # For ObjectRepositoryVariableData
            cascade = rule_data.get("cascade", False)  # Cascade screen.selector to element.scope
            if not match or not variable:
                raise ValueError("parameterize rule requires 'match' and 'variable'")
            rules.append(
                ParameterizeRule(
                    target=target,
                    match=match,
                    variable=variable,
                    attribute=attribute,
                    default_value=default_value,
                    cascade=cascade,
                )
            )

        elif rule_type == "rename":
            # Variable -> variable
            from_var = rule_data.get("from_variable", "")
            to_var = rule_data.get("to_variable", "")
            if not from_var or not to_var:
                raise ValueError("rename rule requires 'from_variable' and 'to_variable'")
            rules.append(
                RenameRule(
                    target=target,
                    from_variable=from_var,
                    to_variable=to_var,
                )
            )

        elif rule_type == "reset":
            # Variable -> hardcoded value
            variable = rule_data.get("variable", "")
            value = rule_data.get("value", "") or rule_data.get("url", "")  # Support both
            if not variable or not value:
                raise ValueError("reset rule requires 'variable' and 'value'")
            rules.append(
                ResetRule(
                    target=target,
                    variable=variable,
                    value=value,
                )
            )

        else:
            raise ValueError(f"Unknown rule type: {rule_type}")

    return rules


def _target_matches_entry(target: RuleTarget, entry: AnyEntry, is_scope: bool = True) -> bool:
    """Check if a rule target matches an entry type.

    Args:
        target: Rule target
        entry: Entry to check
        is_scope: For elements, whether checking scope (True) or selector (False)

    Returns:
        True if target allows this entry type
    """
    if target == RuleTarget.ALL:
        return True

    if entry.entry_type == EntryType.SCREEN:
        return target == RuleTarget.SCREEN

    # Element entry
    if target == RuleTarget.ELEMENT_SCOPE:
        return is_scope
    if target == RuleTarget.ELEMENT_SELECTOR:
        return not is_scope

    return False


def _match_screen_rule(entry: ScreenEntry, rule: ReplaceRule) -> bool:
    """Check if a rule applies to a Screen entry (URL).

    Args:
        entry: Screen entry to check
        rule: Rule to match against

    Returns:
        True if rule applies, False otherwise
    """
    if not _target_matches_entry(rule.target, entry):
        return False

    if isinstance(rule, ParameterizeRule):
        # Only match hardcoded URLs
        if entry.url_status != UrlStatus.HARDCODED:
            return False
        # Match URL pattern (supports wildcards)
        return fnmatch(entry.url, rule.match)

    elif isinstance(rule, RenameRule):
        # Only match parameterized URLs with matching variable
        if entry.url_status != UrlStatus.PARAMETERIZED:
            return False
        return entry.variable_name == rule.from_variable

    elif isinstance(rule, ResetRule):
        # Only match parameterized URLs with matching variable
        if entry.url_status != UrlStatus.PARAMETERIZED:
            return False
        return entry.variable_name == rule.variable

    return False


def _match_screen_selector_rule(
    entry: ScreenEntry, rule: ReplaceRule
) -> tuple[bool, str | None, str | None]:
    """Check if a rule applies to a Screen entry's Selector attribute.

    Args:
        entry: Screen entry to check
        rule: Rule to match against

    Returns:
        Tuple of (matches, attribute, matched_value)
    """
    # Only process screen.selector target rules
    if rule.target != RuleTarget.SCREEN_SELECTOR:
        return False, None, None

    if not entry.selector:
        return False, None, None

    if isinstance(rule, ParameterizeRule):
        # Must have attribute specified for screen.selector rules
        if not rule.attribute:
            return False, None, None

        # Check specific attribute within selector
        import re

        # Try single quotes first (most common in selectors)
        match = re.search(f"{rule.attribute}='([^']*)'", entry.selector)
        if not match:
            # Try double quotes
            match = re.search(f'{rule.attribute}="([^"]*)"', entry.selector)

        if match:
            value = match.group(1)
            # Check if this value contains a variable already
            if not screen_adapter.is_parameterized(value):
                if fnmatch(value, rule.match):
                    return True, rule.attribute, value

    return False, None, None


def _is_selector_parameterized(selector: str) -> bool:
    """Check if a selector is already wrapped in a parameterized expression.

    Detects selectors that are already wrapped in [string.Format(...)] or similar
    VB.NET expressions, making the idempotency check more robust.

    Args:
        selector: The selector string to check

    Returns:
        True if selector is already parameterized at the expression level
    """
    stripped = selector.strip()
    # Check for [expression] wrapper (VB.NET expression syntax)
    if stripped.startswith("[") and stripped.endswith("]"):
        # Check for common parameterization patterns
        inner = stripped[1:-1].strip()
        if inner.startswith("string.Format(") or inner.startswith("String.Format("):
            return True
        # Also check for simple variable reference
        if not inner.startswith("<"):
            return True
    return False


def _match_element_rule(
    entry: ElementEntry, rule: ReplaceRule, selector_type: str
) -> tuple[bool, str | None, str | None]:
    """Check if a rule applies to an Element entry.

    Args:
        entry: Element entry to check
        rule: Rule to match against
        selector_type: "scope" or "selector"

    Returns:
        Tuple of (matches, attribute, matched_value)
    """
    is_scope = selector_type == "scope"
    if not _target_matches_entry(rule.target, entry, is_scope=is_scope):
        return False, None, None

    # Get the appropriate selector and parsed attributes
    if selector_type == "scope":
        selector = entry.scope_selector
        variables = entry.scope_variables
    else:
        selector = entry.full_selector
        variables = entry.selector_variables

    # Skip if selector is already parameterized at expression level
    if _is_selector_parameterized(selector):
        return False, None, None

    if isinstance(rule, ParameterizeRule):
        # Only match if not already parameterized for this attribute
        if rule.attribute:
            # Check specific attribute
            attr_pattern = f"{rule.attribute}='"
            if attr_pattern in selector:
                # Extract the value
                import re

                match = re.search(f"{rule.attribute}='([^']*)'", selector)
                if match:
                    value = match.group(1)
                    # Check if this value contains a variable already
                    if not element_adapter.is_parameterized(value):
                        if fnmatch(value, rule.match):
                            return True, rule.attribute, value
        else:
            # Match any attribute value (less common)
            if not element_adapter.is_parameterized(selector):
                if fnmatch(selector, rule.match):
                    return True, None, selector

    elif isinstance(rule, RenameRule):
        # Only match if using the specified variable
        if rule.from_variable in variables:
            return True, None, rule.from_variable

    elif isinstance(rule, ResetRule):
        # Only match if using the specified variable
        if rule.variable in variables:
            return True, None, rule.variable

    return False, None, None


def _compute_screen_new_value(entry: ScreenEntry, rule: ReplaceRule) -> str:
    """Compute new URL after applying rule to Screen.

    For parameterize rules with wildcard match (e.g., "https://example.com/*"),
    only the base URL is replaced and the path suffix is preserved.

    Args:
        entry: Screen entry
        rule: Rule to apply

    Returns:
        New URL string
    """
    if isinstance(rule, ParameterizeRule):
        variable_url = screen_adapter.format_variable(rule.variable)

        # Check if this is a base URL match (ends with * wildcard)
        if rule.match.endswith("*"):
            # Extract the base pattern (without the *)
            base_pattern = rule.match[:-1]
            if entry.url.startswith(base_pattern):
                # Preserve the path suffix after the base URL
                suffix = entry.url[len(base_pattern) :]
                return variable_url + suffix

        return variable_url

    elif isinstance(rule, RenameRule):
        return screen_adapter.format_variable(rule.to_variable)

    elif isinstance(rule, ResetRule):
        return rule.value

    return entry.url


def _compute_element_new_value(old_value: str, rule: ReplaceRule) -> str:
    """Compute new value after applying rule to Element (simple attribute value).

    Args:
        old_value: Current attribute value
        rule: Rule to apply

    Returns:
        New value string (just the attribute value, not full selector)
    """
    if isinstance(rule, ParameterizeRule):
        variable_syntax = element_adapter.format_variable(rule.variable)

        # Check if this is a base pattern match (ends with * wildcard)
        if rule.match.endswith("*"):
            base_pattern = rule.match[:-1]
            if old_value.startswith(base_pattern):
                suffix = old_value[len(base_pattern) :]
                return variable_syntax + suffix

        return variable_syntax

    elif isinstance(rule, RenameRule):
        # Replace the old variable with new one
        old_var_syntax = element_adapter.format_variable(rule.from_variable)
        new_var_syntax = element_adapter.format_variable(rule.to_variable)
        return old_value.replace(old_var_syntax, new_var_syntax)

    elif isinstance(rule, ResetRule):
        return rule.value

    return old_value


def _compute_element_selector_preview(
    selector: str,
    attr: str,
    old_attr_value: str,
    rule: ReplaceRule,
) -> tuple[str, str]:
    """Compute full selector preview for Element parameterization.

    Args:
        selector: Full selector string (e.g., "<html app='chrome.exe' title='Google' />")
        attr: Attribute name being changed (e.g., "title")
        old_attr_value: Current attribute value (e.g., "Google")
        rule: Rule to apply

    Returns:
        Tuple of (old_selector, new_selector) for preview display
    """
    if isinstance(rule, ParameterizeRule):
        # Use string.Format wrapper for full selector
        new_selector = element_adapter.format_selector_with_variable(
            selector, attr, old_attr_value, rule.variable
        )
        return selector, new_selector

    # For other rules, just do simple substitution
    new_attr_value = _compute_element_new_value(old_attr_value, rule)
    new_selector = selector.replace(
        f"{attr}='{old_attr_value}'", f"{attr}='{new_attr_value}'"
    )
    return selector, new_selector


def preview_replacements(
    screens: list[ScreenEntry],
    elements: list[ElementEntry],
    rules: list[ReplaceRule],
    force: bool = False,
) -> tuple[list[ReplacePreview], list[str]]:
    """Preview replacements without applying them.

    Args:
        screens: List of Screen entries
        elements: List of Element entries
        rules: List of replacement rules
        force: Allow mutations on unsupported versions

    Returns:
        Tuple of (previews, warnings)
    """
    previews: list[ReplacePreview] = []
    warnings: list[str] = []

    # Build lookup dicts for cascade support
    screens_by_ref = {s.reference: s for s in screens}
    elements_by_ref = {e.reference: e for e in elements}

    # Track elements that have been cascaded to (to avoid duplicate matches)
    cascaded_elements: set[str] = set()

    # Process Screens
    for entry in screens:
        # Check version support
        if not screen_adapter.is_version_supported(entry.descriptor_version):
            if not force:
                warnings.append(
                    f"Skipping {entry.full_path}: unsupported version {entry.descriptor_version}"
                )
                continue

        matched = False
        for rule in rules:
            if matched:
                break

            # Check screen URL rules (target = "screen" or "all")
            if _match_screen_rule(entry, rule):
                new_value = _compute_screen_new_value(entry, rule)
                previews.append(
                    ReplacePreview(
                        entry=entry,
                        old_value=entry.url,
                        new_value=new_value,
                        rule=rule,
                        attribute=None,
                    )
                )
                matched = True
                continue

            # Check screen.selector rules
            matches, attr, old_value = _match_screen_selector_rule(entry, rule)
            if matches and old_value:
                new_value = _compute_element_new_value(old_value, rule)
                previews.append(
                    ReplacePreview(
                        entry=entry,
                        old_value=old_value,
                        new_value=new_value,
                        rule=rule,
                        attribute=attr,
                    )
                )
                matched = True

                # Cascade to descendant elements if enabled
                if (
                    isinstance(rule, ParameterizeRule)
                    and rule.cascade
                    and attr  # Must have matched an attribute
                ):
                    descendants = find_descendant_elements(
                        entry, elements, elements_by_ref
                    )
                    for elem in descendants:
                        # Skip if already cascaded or not supported
                        if elem.reference in cascaded_elements:
                            continue
                        if not element_adapter.is_version_supported(
                            elem.descriptor_version
                        ):
                            if not force:
                                continue

                        # Check if element's scope has the same attribute value
                        elem_attr_value = _extract_selector_attr_value(
                            elem.scope_selector, attr
                        )
                        if elem_attr_value == old_value:
                            # Element scope matches - include in cascade
                            old_selector, new_selector = (
                                _compute_element_selector_preview(
                                    elem.scope_selector, attr, elem_attr_value, rule
                                )
                            )
                            previews.append(
                                ReplacePreview(
                                    entry=elem,
                                    old_value=old_selector,
                                    new_value=new_selector,
                                    rule=rule,
                                    attribute=attr or "scope",
                                    attr_value=elem_attr_value,
                                )
                            )
                            cascaded_elements.add(elem.reference)

    # Process Elements
    for entry in elements:
        # Skip if already handled by cascade
        if entry.reference in cascaded_elements:
            continue

        # Check version support
        if not element_adapter.is_version_supported(entry.descriptor_version):
            if not force:
                warnings.append(
                    f"Skipping {entry.full_path}: unsupported version {entry.descriptor_version}"
                )
                continue

        matched = False
        for rule in rules:
            if matched:
                break

            # Check scope selector
            matches, attr, old_attr_value = _match_element_rule(entry, rule, "scope")
            if matches and old_attr_value:
                old_selector, new_selector = _compute_element_selector_preview(
                    entry.scope_selector, attr, old_attr_value, rule
                )
                previews.append(
                    ReplacePreview(
                        entry=entry,
                        old_value=old_selector,
                        new_value=new_selector,
                        rule=rule,
                        attribute=attr or "scope",
                        attr_value=old_attr_value,
                    )
                )
                matched = True
                continue

            # Check full selector
            matches, attr, old_attr_value = _match_element_rule(entry, rule, "selector")
            if matches and old_attr_value:
                old_selector, new_selector = _compute_element_selector_preview(
                    entry.full_selector, attr, old_attr_value, rule
                )
                previews.append(
                    ReplacePreview(
                        entry=entry,
                        old_value=old_selector,
                        new_value=new_selector,
                        rule=rule,
                        attribute=attr or "selector",
                        attr_value=old_attr_value,
                    )
                )
                matched = True

    return previews, warnings
