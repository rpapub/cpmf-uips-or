"""Output formatters for inventory display."""

from typing import Any

from .models import (
    AppNode,
    ElementEntry,
    ElementNode,
    Inventory,
    ScreenEntry,
    ScreenNode,
    VersionNode,
)


def format_tree_text(inventory: Inventory) -> str:
    """Format as indented tree text.

    Example output:
        App: CMS
          Version: 2026-01
            Screen: Login (hardcoded)
              Element: username (InputBox, Selector)
              Element: loginBtn (Button, Selector)
                Element: btnIcon (nested)
    """
    lines: list[str] = []

    for app in inventory.apps:
        lines.append(f"App: {app.name}")
        for version in app.versions:
            lines.append(f"  Version: {version.name}")
            for screen_node in version.screens:
                screen = screen_node.entry
                status = f"[{screen.variable_name}]" if screen.variable_name else "hardcoded"
                lines.append(f"    Screen: {screen.screen_name} ({status})")
                _format_elements_text(screen_node.elements, lines, indent=6)

    return "\n".join(lines)


def _format_elements_text(
    elements: list[ElementNode],
    lines: list[str],
    indent: int,
) -> None:
    """Recursively format element nodes with proper indentation."""
    prefix = " " * indent
    for element_node in elements:
        el = element_node.entry
        param_status = "parameterized" if el.is_parameterized else "hardcoded"
        lines.append(
            f"{prefix}Element: {el.element_name} ({el.element_type}, {el.search_steps}) [{param_status}]"
        )
        # Recurse for nested elements
        if element_node.children:
            _format_elements_text(element_node.children, lines, indent + 2)


def format_tree_json(inventory: Inventory) -> dict[str, Any]:
    """Format as nested JSON structure."""
    return {
        "apps": [_app_to_dict(app) for app in inventory.apps],
    }


def _app_to_dict(app: AppNode) -> dict[str, Any]:
    """Convert AppNode to dict."""
    return {
        "name": app.name,
        "reference": app.reference,
        "versions": [_version_to_dict(v) for v in app.versions],
    }


def _version_to_dict(version: VersionNode) -> dict[str, Any]:
    """Convert VersionNode to dict."""
    return {
        "name": version.name,
        "reference": version.reference,
        "screens": [_screen_node_to_dict(s) for s in version.screens],
    }


def _screen_node_to_dict(screen_node: ScreenNode) -> dict[str, Any]:
    """Convert ScreenNode to dict."""
    screen = screen_node.entry
    return {
        "name": screen.screen_name,
        "reference": screen.reference,
        "url": screen.url,
        "url_status": screen.url_status.value,
        "variable": screen.variable_name,
        "version": screen.descriptor_version,
        "elements": [_element_node_to_dict(e) for e in screen_node.elements],
    }


def _element_node_to_dict(element_node: ElementNode) -> dict[str, Any]:
    """Convert ElementNode to dict (recursive for nested elements)."""
    el = element_node.entry
    return {
        "name": el.element_name,
        "reference": el.reference,
        "search_steps": el.search_steps,
        "element_type": el.element_type,
        "activity_type": el.activity_type,
        "scope_selector": el.scope_selector,
        "full_selector": el.full_selector,
        "scope_variables": el.scope_variables,
        "selector_variables": el.selector_variables,
        "version": el.descriptor_version,
        "children": [_element_node_to_dict(c) for c in element_node.children],
    }


def format_flat_json(inventory: Inventory) -> list[dict[str, Any]]:
    """Format as flat JSON list (backward compatible)."""
    data: list[dict[str, Any]] = []

    for screen in inventory.screens:
        data.append(_screen_to_flat_dict(screen))

    for element in inventory.elements:
        data.append(_element_to_flat_dict(element))

    return data


def _screen_to_flat_dict(screen: ScreenEntry) -> dict[str, Any]:
    """Convert ScreenEntry to flat dict."""
    return {
        "type": "screen",
        "path": screen.full_path,
        "url": screen.url,
        "status": screen.url_status.value,
        "variable": screen.variable_name,
        "version": screen.descriptor_version,
        "reference": screen.reference,
    }


def _element_to_flat_dict(element: ElementEntry) -> dict[str, Any]:
    """Convert ElementEntry to flat dict."""
    return {
        "type": "element",
        "path": element.full_path,
        "search_steps": element.search_steps,
        "element_type": element.element_type,
        "activity_type": element.activity_type,
        "scope_selector": element.scope_selector,
        "full_selector": element.full_selector,
        "scope_variables": element.scope_variables,
        "selector_variables": element.selector_variables,
        "version": element.descriptor_version,
        "reference": element.reference,
    }


def format_markdown(inventory: Inventory, screenshots_rel_path: str = "../.screenshots") -> str:
    """Format as markdown with screenshots using Jinja template.

    Args:
        inventory: The inventory to format
        screenshots_rel_path: Relative path from output file to .screenshots dir

    Returns:
        Markdown string
    """
    from jinja2 import Environment

    from .templates import MARKDOWN_ELEMENT_TEMPLATE, MARKDOWN_TEMPLATE

    env = Environment(autoescape=False)

    # Create element renderer function for recursive rendering
    element_template = env.from_string(MARKDOWN_ELEMENT_TEMPLATE)

    def render_elements_md(elements: list[ElementNode], depth: int) -> str:
        return element_template.render(
            elements=elements,
            indent="  " * depth,
            depth=depth,
            screenshots_path=screenshots_rel_path,
            render_elements_md=render_elements_md,
        )

    main_template = env.from_string(MARKDOWN_TEMPLATE)
    return main_template.render(
        apps=inventory.apps,
        screenshots_path=screenshots_rel_path,
        render_elements_md=render_elements_md,
    )


def format_html(inventory: Inventory, screenshots_rel_path: str = "../.screenshots") -> str:
    """Format as HTML with screenshots using Jinja template.

    Args:
        inventory: The inventory to format
        screenshots_rel_path: Relative path from output file to .screenshots dir

    Returns:
        HTML string
    """
    from jinja2 import Environment

    from .templates import HTML_ELEMENT_TEMPLATE, HTML_TEMPLATE

    env = Environment(autoescape=True)

    # Create element renderer function for recursive rendering
    element_template = env.from_string(HTML_ELEMENT_TEMPLATE)

    def render_elements_html(elements: list[ElementNode], depth: int) -> str:
        return element_template.render(
            elements=elements,
            depth=depth,
            screenshots_path=screenshots_rel_path,
            render_elements_html=render_elements_html,
        )

    main_template = env.from_string(HTML_TEMPLATE)
    return main_template.render(
        apps=inventory.apps,
        screenshots_path=screenshots_rel_path,
        render_elements_html=render_elements_html,
    )
