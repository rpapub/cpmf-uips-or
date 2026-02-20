"""Output formatters for inventory display."""

from typing import Any

from .models import (
    AppNode,
    ElementEntry,
    ElementNode,
    Inventory,
    ScreenEntry,
    ScreenNode,
    VariableDecl,
    VersionNode,
)


def _variables_to_dicts(variables: list[VariableDecl] | None) -> list[dict[str, str]] | None:
    """Convert VariableDecl list to JSON-serializable dicts."""
    if not variables:
        return None
    return [{"name": v.name, "default": v.default} for v in variables]


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
    """Format as nested JSON structure with project and library metadata."""
    result: dict[str, Any] = {}

    # Add project metadata if available
    if inventory.project:
        result["project"] = {
            "name": inventory.project.name,
            "project_id": inventory.project.project_id,
            "version": inventory.project.version,
            "studio_version": inventory.project.studio_version,
            "target_framework": inventory.project.target_framework,
            "ui_automation_version": inventory.project.ui_automation_version,
        }

    # Add library metadata if available
    if inventory.library:
        result["library"] = {
            "id": inventory.library.id,
            "created": inventory.library.created,
            "created_by": inventory.library.created_by,
        }

    result["apps"] = [_app_to_dict(app) for app in inventory.apps]
    return result


def _app_to_dict(app: AppNode) -> dict[str, Any]:
    """Convert AppNode to dict."""
    return {
        "name": app.name,
        "reference": app.reference,
        "created": app.created,
        "created_by": app.created_by,
        "versions": [_version_to_dict(v) for v in app.versions],
    }


def _version_to_dict(version: VersionNode) -> dict[str, Any]:
    """Convert VersionNode to dict."""
    return {
        "name": version.name,
        "reference": version.reference,
        "created": version.created,
        "created_by": version.created_by,
        "screens": [_screen_node_to_dict(s) for s in version.screens],
    }


def _screen_node_to_dict(screen_node: ScreenNode) -> dict[str, Any]:
    """Convert ScreenNode to dict."""
    screen = screen_node.entry
    return {
        "name": screen.screen_name,
        "reference": screen.reference,
        "depth": screen.depth,
        "url": screen.url,
        "url_status": screen.url_status.value,
        "variable": screen.variable_name,
        "selector": screen.selector,
        "declared_variables": _variables_to_dicts(screen.declared_variables),
        "version": screen.descriptor_version,
        "created": screen.created,
        "updated": screen.updated,
        "created_by": screen.created_by,
        "updated_by": screen.updated_by,
        "elements": [_element_node_to_dict(e) for e in screen_node.elements],
    }


def _element_node_to_dict(element_node: ElementNode) -> dict[str, Any]:
    """Convert ElementNode to dict (recursive for nested elements)."""
    el = element_node.entry
    return {
        "name": el.element_name,
        "reference": el.reference,
        "depth": el.depth,
        "search_steps": el.search_steps,
        "element_type": el.element_type,
        "activity_type": el.activity_type,
        "visibility": el.visibility,
        "wait_for_ready": el.wait_for_ready,
        "scope_selector": el.scope_selector,
        "full_selector": el.full_selector,
        "fuzzy_selector": el.fuzzy_selector,
        "has_image": el.has_image,
        "has_cv": el.has_cv,
        "cv_type": el.cv_type,
        "scope_variables": el.scope_variables,
        "selector_variables": el.selector_variables,
        "declared_variables": _variables_to_dicts(el.declared_variables),
        "version": el.descriptor_version,
        "created": el.created,
        "updated": el.updated,
        "created_by": el.created_by,
        "updated_by": el.updated_by,
        "children": [_element_node_to_dict(c) for c in element_node.children],
    }


def format_flat_json(inventory: Inventory) -> dict[str, Any]:
    """Format as flat JSON with project/library metadata and entries list."""
    result: dict[str, Any] = {}

    # Add project metadata if available
    if inventory.project:
        result["project"] = {
            "name": inventory.project.name,
            "project_id": inventory.project.project_id,
            "version": inventory.project.version,
            "studio_version": inventory.project.studio_version,
            "target_framework": inventory.project.target_framework,
            "ui_automation_version": inventory.project.ui_automation_version,
        }

    # Add library metadata if available
    if inventory.library:
        result["library"] = {
            "id": inventory.library.id,
            "created": inventory.library.created,
            "created_by": inventory.library.created_by,
        }

    # Add entries list
    entries: list[dict[str, Any]] = []
    for screen in inventory.screens:
        entries.append(_screen_to_flat_dict(screen))
    for element in inventory.elements:
        entries.append(_element_to_flat_dict(element))

    result["entries"] = entries
    return result


def _screen_to_flat_dict(screen: ScreenEntry) -> dict[str, Any]:
    """Convert ScreenEntry to flat dict."""
    return {
        "type": "screen",
        "path": screen.full_path,
        "depth": screen.depth,
        "screenshot": screen.screenshot,
        "screenshot_width": screen.screenshot_width,
        "screenshot_height": screen.screenshot_height,
        # Explicit filter fields
        "app_name": screen.app_name,
        "app_version": screen.app_version,
        "screen_name": screen.screen_name,
        # Screen attributes
        "url": screen.url,
        "selector": screen.selector,
        "declared_variables": _variables_to_dicts(screen.declared_variables),
        "status": screen.url_status.value,
        "variable": screen.variable_name,
        "version": screen.descriptor_version,
        # References for hierarchy navigation
        "reference": screen.reference,
        "parent_ref": screen.parent_ref,
        "created": screen.created,
        "updated": screen.updated,
        "created_by": screen.created_by,
        "updated_by": screen.updated_by,
    }


def _element_to_flat_dict(element: ElementEntry) -> dict[str, Any]:
    """Convert ElementEntry to flat dict."""
    # Parent path is the screen containing this element
    parent_path = f"{element.app_name}/{element.app_version}/{element.screen_name}"

    return {
        "type": "element",
        "path": element.full_path,
        "depth": element.depth,
        "screenshot": element.screenshot,
        "screenshot_width": element.screenshot_width,
        "screenshot_height": element.screenshot_height,
        # Explicit filter fields
        "app_name": element.app_name,
        "app_version": element.app_version,
        "screen_name": element.screen_name,
        "element_name": element.element_name,
        "parent_path": parent_path,
        # Element attributes
        "search_steps": element.search_steps,
        "element_type": element.element_type,
        "activity_type": element.activity_type,
        "visibility": element.visibility,
        "wait_for_ready": element.wait_for_ready,
        "scope_selector": element.scope_selector,
        "full_selector": element.full_selector,
        "fuzzy_selector": element.fuzzy_selector,
        "has_image": element.has_image,
        "has_cv": element.has_cv,
        "cv_type": element.cv_type,
        "scope_variables": element.scope_variables,
        "selector_variables": element.selector_variables,
        "declared_variables": _variables_to_dicts(element.declared_variables),
        "version": element.descriptor_version,
        # References for hierarchy navigation
        "reference": element.reference,
        "parent_ref": element.parent_ref,
        "created": element.created,
        "updated": element.updated,
        "created_by": element.created_by,
        "updated_by": element.updated_by,
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
