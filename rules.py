"""Rules loading and application.

Loads replacement rules from TOML config files.
Supports both V2 Screens (URL) and V6 Elements (selector attributes).

Rule targeting:
- target = "all" (default): applies to all types
- target = "screen": V2 Screen URLs only
- target = "element.scope": V6 ScopeSelectorArgument only
- target = "element.selector": V6 FullSelectorArgument only
"""

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
    elif target_str == "element.scope":
        return RuleTarget.ELEMENT_SCOPE
    elif target_str == "element.selector":
        return RuleTarget.ELEMENT_SELECTOR
    else:
        raise ValueError(f"Unknown target: {target_str}")


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
            if not match or not variable:
                raise ValueError("parameterize rule requires 'match' and 'variable'")
            rules.append(
                ParameterizeRule(
                    target=target,
                    match=match,
                    variable=variable,
                    attribute=attribute,
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
    """Check if a rule applies to a Screen entry.

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
    """Compute new value after applying rule to Element.

    Args:
        old_value: Current attribute value
        rule: Rule to apply

    Returns:
        New value string
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

    # Process Screens
    for entry in screens:
        # Check version support
        if not screen_adapter.is_version_supported(entry.descriptor_version):
            if not force:
                warnings.append(
                    f"Skipping {entry.full_path}: unsupported version {entry.descriptor_version}"
                )
                continue

        for rule in rules:
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
                break  # Only apply first matching rule

    # Process Elements
    for entry in elements:
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
            matches, attr, old_value = _match_element_rule(entry, rule, "scope")
            if matches and old_value:
                new_value = _compute_element_new_value(old_value, rule)
                previews.append(
                    ReplacePreview(
                        entry=entry,
                        old_value=old_value,
                        new_value=new_value,
                        rule=rule,
                        attribute=attr or "scope",
                    )
                )
                matched = True
                continue

            # Check full selector
            matches, attr, old_value = _match_element_rule(entry, rule, "selector")
            if matches and old_value:
                new_value = _compute_element_new_value(old_value, rule)
                previews.append(
                    ReplacePreview(
                        entry=entry,
                        old_value=old_value,
                        new_value=new_value,
                        rule=rule,
                        attribute=attr or "selector",
                    )
                )
                matched = True

    return previews, warnings
