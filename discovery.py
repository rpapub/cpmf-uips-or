"""Discovery of Object Repository structure.

Traverses .objects/ hierarchy using .type files to determine node types:
  Library -> App -> AppVersion -> Screen -> Element (nested)

Screen nodes have ObjectRepositoryScreenData/.content with URL (V2).
Element nodes have ObjectRepositoryTargetData/.content with selectors (V6).
"""

from pathlib import Path

from . import adapter_element_V6 as element_adapter
from . import adapter_screen_V2 as screen_adapter
from .models import (
    AnyEntry,
    AppNode,
    AuditResult,
    ElementEntry,
    ElementNode,
    Inventory,
    LibraryMeta,
    ScreenEntry,
    ScreenNode,
    UrlStatus,
    VersionNode,
)
from .parser import Metadata, parse_metadata

# Optional PIL import for image dimensions
try:
    from PIL import Image

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _get_image_size(image_path: Path) -> tuple[int, int] | None:
    """Get image dimensions (width, height) in pixels.

    Returns None if PIL is not available or image cannot be read.
    """
    if not _PIL_AVAILABLE or not image_path.exists():
        return None
    try:
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception:
        return None


def find_objects_dir(project_json: Path) -> Path:
    """Get .objects directory from project.json path."""
    return project_json.parent / ".objects"


def read_type(folder: Path) -> str | None:
    """Read .type file to determine node type."""
    type_file = folder / ".type"
    if type_file.exists():
        return type_file.read_text().strip()
    return None


def discover_all(objects_dir: Path) -> tuple[list[ScreenEntry], list[ElementEntry]]:
    """Discover all Screen and Element objects in the repository.

    Args:
        objects_dir: Path to .objects directory

    Returns:
        Tuple of (screens, elements)
    """
    screens: list[ScreenEntry] = []
    elements: list[ElementEntry] = []

    if not objects_dir.exists():
        return screens, elements

    screenshots_dir = objects_dir.parent / ".screenshots"
    _traverse(
        objects_dir, screens, elements,
        app_name=None, app_version=None, screen_name=None,
        screenshots_dir=screenshots_dir if screenshots_dir.exists() else None,
    )

    return screens, elements


# Backwards compatible alias
def discover_objects(objects_dir: Path) -> list[ScreenEntry]:
    """Discover all Screen objects (backwards compatible)."""
    screens, _ = discover_all(objects_dir)
    return screens


def _traverse(
    folder: Path,
    screens: list[ScreenEntry],
    elements: list[ElementEntry],
    app_name: str | None,
    app_version: str | None,
    screen_name: str | None,
    screenshots_dir: Path | None = None,
) -> None:
    """Recursively traverse the object repository."""
    node_type = read_type(folder)

    if node_type == "App":
        meta = parse_metadata(folder / ".metadata")
        app_name = meta.name if meta else folder.name

    elif node_type == "AppVersion":
        meta = parse_metadata(folder / ".metadata")
        app_version = meta.name if meta else folder.name

    elif node_type == "Screen":
        # Found a Screen - extract ObjectRepositoryScreenData
        meta = parse_metadata(folder / ".metadata")
        screen_name = meta.name if meta else folder.name
        reference = meta.reference if meta else ""

        content_path = folder / ".data" / "ObjectRepositoryScreenData" / ".content"
        if content_path.exists():
            content_data = screen_adapter.parse_content(content_path)
            if content_data:
                var_name, _ = screen_adapter.extract_variable(content_data.url)
                url_status = UrlStatus.PARAMETERIZED if var_name else UrlStatus.HARDCODED

                # Get screenshot dimensions if available
                screenshot_width = None
                screenshot_height = None
                if content_data.screenshot and screenshots_dir:
                    img_size = _get_image_size(screenshots_dir / content_data.screenshot)
                    if img_size:
                        screenshot_width, screenshot_height = img_size

                screens.append(
                    ScreenEntry(
                        app_name=app_name or "Unknown",
                        app_version=app_version or "Unknown",
                        screen_name=screen_name,
                        url=content_data.url,
                        url_status=url_status,
                        variable_name=var_name,
                        selector=content_data.selector,
                        reference=reference,
                        descriptor_version=content_data.version,
                        content_path=content_path,
                        parent_ref=meta.parent_ref if meta else None,
                        screenshot=content_data.screenshot,
                        screenshot_width=screenshot_width,
                        screenshot_height=screenshot_height,
                        declared_variables=content_data.variables,
                        created=meta.created if meta else None,
                        updated=meta.updated if meta else None,
                        created_by=meta.created_by if meta else None,
                        updated_by=meta.updated_by if meta else None,
                    )
                )

    elif node_type == "Element":
        # Found an Element - extract ObjectRepositoryTargetData
        meta = parse_metadata(folder / ".metadata")
        element_name = meta.name if meta else folder.name
        reference = meta.reference if meta else ""

        content_path = folder / ".data" / "ObjectRepositoryTargetData" / ".content"
        if content_path.exists():
            content_data = element_adapter.parse_content(content_path)
            if content_data:
                scope_vars = element_adapter.extract_variables(content_data.scope_selector)
                selector_vars = element_adapter.extract_variables(content_data.full_selector)

                # Get screenshot dimensions if available
                screenshot_width = None
                screenshot_height = None
                if content_data.screenshot and screenshots_dir:
                    img_size = _get_image_size(screenshots_dir / content_data.screenshot)
                    if img_size:
                        screenshot_width, screenshot_height = img_size

                elements.append(
                    ElementEntry(
                        app_name=app_name or "Unknown",
                        app_version=app_version or "Unknown",
                        screen_name=screen_name or "Unknown",
                        element_name=element_name,
                        search_steps=content_data.search_steps,
                        scope_selector=content_data.scope_selector,
                        full_selector=content_data.full_selector,
                        browser_url=content_data.browser_url,
                        element_type=content_data.element_type,
                        activity_type=content_data.activity_type,
                        reference=reference,
                        descriptor_version=content_data.version,
                        content_path=content_path,
                        parent_ref=meta.parent_ref if meta else None,
                        screenshot=content_data.screenshot,
                        screenshot_width=screenshot_width,
                        screenshot_height=screenshot_height,
                        fuzzy_selector=content_data.fuzzy_selector,
                        has_image=content_data.has_image,
                        has_cv=content_data.has_cv,
                        cv_type=content_data.cv_type,
                        visibility=content_data.visibility,
                        wait_for_ready=content_data.wait_for_ready,
                        scope_variables=scope_vars,
                        selector_variables=selector_vars,
                        declared_variables=content_data.variables,
                        created=meta.created if meta else None,
                        updated=meta.updated if meta else None,
                        created_by=meta.created_by if meta else None,
                        updated_by=meta.updated_by if meta else None,
                    )
                )

    # Continue traversing child folders (for all types)
    for child in folder.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            _traverse(child, screens, elements, app_name, app_version, screen_name, screenshots_dir)


def _find_root_screen(
    element: ElementEntry,
    screens_by_ref: dict[str, ScreenEntry],
    elements_by_ref: dict[str, ElementEntry],
) -> ScreenEntry | None:
    """Traverse parent_ref chain to find the ancestor screen.

    Handles nested elements by following the chain:
    NestedElement -> ParentElement -> ... -> Screen
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


def _is_selector_parameterized(selector: str) -> bool:
    """Check if a selector contains parameterized values [varName]."""
    import re
    # Look for [varName] pattern (not string.Format, just simple variable)
    return bool(re.search(r"\[(?!string\.Format)[a-zA-Z_][a-zA-Z0-9_]*\]", selector))


def _check_scope_consistency(
    screens: list[ScreenEntry],
    elements: list[ElementEntry],
) -> list[str]:
    """Find elements with hardcoded scope whose ancestor screen has parameterized selector.

    Returns:
        List of issue strings describing inconsistencies
    """
    issues: list[str] = []
    screens_by_ref = {s.reference: s for s in screens}
    elements_by_ref = {e.reference: e for e in elements}

    for elem in elements:
        # Find ancestor screen (handles nested elements)
        root_screen = _find_root_screen(elem, screens_by_ref, elements_by_ref)
        if not root_screen:
            continue

        # Check: ancestor has parameterized selector but element has hardcoded scope
        screen_selector_parameterized = _is_selector_parameterized(root_screen.selector)
        element_scope_parameterized = bool(elem.scope_variables)

        if screen_selector_parameterized and not element_scope_parameterized:
            issues.append(
                f"Inconsistent scope: {elem.full_path} has hardcoded scope but "
                f"ancestor Screen '{root_screen.screen_name}' has parameterized selector"
            )

    return issues


def audit_all(
    screens: list[ScreenEntry],
    elements: list[ElementEntry],
) -> AuditResult:
    """Generate audit statistics from discovered objects.

    Args:
        screens: List of ScreenEntry objects
        elements: List of ElementEntry objects

    Returns:
        AuditResult with aggregated statistics
    """
    result = AuditResult()
    result.total_objects = len(screens) + len(elements)

    # Audit Screens (V2)
    for entry in screens:
        if entry.url_status == UrlStatus.HARDCODED:
            result.hardcoded_count += 1
        else:
            result.parameterized_count += 1
            if entry.variable_name:
                result.variables_in_use.add(entry.variable_name)

        version = entry.descriptor_version
        result.version_counts[version] = result.version_counts.get(version, 0) + 1

        if entry.descriptor_version not in {"V2"}:
            result.issues.append(
                f"Unsupported Screen version {entry.descriptor_version}: {entry.full_path}"
            )

        # Warn about literal wildcards in URLs
        if "*" in entry.url and entry.url_status == UrlStatus.HARDCODED:
            result.issues.append(
                f"URL contains literal '*' (not honored by UiPath): {entry.full_path}"
            )

    # Audit Elements (V6)
    for entry in elements:
        if entry.is_parameterized:
            result.parameterized_count += 1
            for var in entry.scope_variables + entry.selector_variables:
                result.variables_in_use.add(var)
        else:
            result.hardcoded_count += 1

        version = entry.descriptor_version
        result.version_counts[version] = result.version_counts.get(version, 0) + 1

        if entry.descriptor_version not in {"V6"}:
            result.issues.append(
                f"Unsupported Element version {entry.descriptor_version}: {entry.full_path}"
            )

    # Check scope consistency (parameterized screen selector with hardcoded element scope)
    consistency_issues = _check_scope_consistency(screens, elements)
    result.issues.extend(consistency_issues)

    return result


# Backwards compatible alias
def audit_objects(entries: list[ScreenEntry]) -> AuditResult:
    """Audit Screen objects only (backwards compatible)."""
    return audit_all(entries, [])


# ---------- Hierarchy building ----------


def _extract_id(reference: str | None) -> str | None:
    """Extract ID from reference. E.g., 'lib/abc123' -> 'abc123'"""
    if not reference:
        return None
    parts = reference.split("/")
    return parts[-1] if parts else None


def _collect_hierarchy_metadata(
    objects_dir: Path,
) -> tuple[list[Metadata], list[Metadata]]:
    """Collect App and AppVersion metadata.

    Returns:
        Tuple of (apps_meta, versions_meta) where both are lists of Metadata objects
    """
    apps_meta: list[Metadata] = []
    versions_meta: list[Metadata] = []

    def _collect(folder: Path) -> None:
        node_type = read_type(folder)

        if node_type == "App":
            meta = parse_metadata(folder / ".metadata")
            if meta:
                apps_meta.append(meta)

        elif node_type == "AppVersion":
            meta = parse_metadata(folder / ".metadata")
            if meta:
                versions_meta.append(meta)

        # Continue traversing for nested nodes
        for child in folder.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                _collect(child)

    if objects_dir.exists():
        _collect(objects_dir)

    return apps_meta, versions_meta


def build_hierarchy(
    screens: list[ScreenEntry],
    elements: list[ElementEntry],
    apps_meta: list[Metadata],
    versions_meta: list[Metadata],
) -> list[AppNode]:
    """Build tree from flat lists using parent_ref links.

    1. Create lookup tables by reference ID
    2. Group versions under apps
    3. Group screens under versions
    4. Group elements under screens (handles nesting via parent_ref)
    """
    # Build apps lookup: reference -> AppNode
    apps_by_ref: dict[str, AppNode] = {}
    for meta in apps_meta:
        apps_by_ref[meta.reference] = AppNode(
            name=meta.name,
            reference=meta.reference,
            created=meta.created,
            created_by=meta.created_by,
        )

    # Build versions lookup: reference -> VersionNode
    versions_by_ref: dict[str, VersionNode] = {}
    for meta in versions_meta:
        versions_by_ref[meta.reference] = VersionNode(
            name=meta.name,
            reference=meta.reference,
            parent_ref=meta.parent_ref,
            created=meta.created,
            created_by=meta.created_by,
        )

    # Group versions under apps
    for version in versions_by_ref.values():
        if version.parent_ref and version.parent_ref in apps_by_ref:
            apps_by_ref[version.parent_ref].versions.append(version)

    # Build screens lookup: reference -> ScreenNode
    screens_by_ref: dict[str, ScreenNode] = {}
    for screen in screens:
        screens_by_ref[screen.reference] = ScreenNode(entry=screen)

    # Group screens under versions
    for screen_node in screens_by_ref.values():
        parent_ref = screen_node.entry.parent_ref
        if parent_ref and parent_ref in versions_by_ref:
            versions_by_ref[parent_ref].screens.append(screen_node)

    # Build elements lookup: reference -> ElementNode
    elements_by_ref: dict[str, ElementNode] = {}
    for element in elements:
        elements_by_ref[element.reference] = ElementNode(entry=element)

    # Group elements - can be under screens or other elements (nesting)
    for element_node in elements_by_ref.values():
        parent_ref = element_node.entry.parent_ref
        if not parent_ref:
            continue

        # Check if parent is a screen
        if parent_ref in screens_by_ref:
            screens_by_ref[parent_ref].elements.append(element_node)
        # Check if parent is another element (nested elements)
        elif parent_ref in elements_by_ref:
            elements_by_ref[parent_ref].children.append(element_node)

    return list(apps_by_ref.values())


def _calculate_element_depth(
    element: ElementEntry,
    elements_by_ref: dict[str, ElementEntry],
    screens_by_ref: dict[str, ScreenEntry],
) -> int:
    """Calculate element depth by traversing parent_ref chain.

    Depth: App(0) > Version(1) > Screen(2) > Element(3+)
    Nested elements have depth = 3 + nesting level.
    """
    depth = 3  # Base depth for elements under a screen
    parent_ref = element.parent_ref

    while parent_ref:
        if parent_ref in screens_by_ref:
            # Reached screen parent - done
            break
        if parent_ref in elements_by_ref:
            # Parent is another element - increment depth
            depth += 1
            parent_ref = elements_by_ref[parent_ref].parent_ref
        else:
            # Unknown parent - stop
            break

    return depth


def discover_inventory(objects_dir: Path) -> Inventory:
    """Discover all objects and build hierarchical inventory.

    Args:
        objects_dir: Path to .objects directory

    Returns:
        Inventory with flat lists and hierarchy tree
    """
    screens: list[ScreenEntry] = []
    elements: list[ElementEntry] = []

    if not objects_dir.exists():
        return Inventory(screens=[], elements=[], apps=[])

    # Parse library-level metadata
    library_meta = None
    lib_metadata_path = objects_dir / ".metadata"
    if lib_metadata_path.exists():
        lib_meta = parse_metadata(lib_metadata_path)
        if lib_meta and lib_meta.created_by:
            library_meta = LibraryMeta(
                id=lib_meta.id,
                created=lib_meta.created or "",
                created_by=lib_meta.created_by,
            )

    # Collect flat lists
    screenshots_dir = objects_dir.parent / ".screenshots"
    _traverse(
        objects_dir, screens, elements,
        app_name=None, app_version=None, screen_name=None,
        screenshots_dir=screenshots_dir if screenshots_dir.exists() else None,
    )

    # Build reference lookups for depth calculation
    screens_by_ref = {s.reference: s for s in screens}
    elements_by_ref = {e.reference: e for e in elements}

    # Calculate depths for elements (screens are always depth 2)
    for element in elements:
        element.depth = _calculate_element_depth(element, elements_by_ref, screens_by_ref)

    # Collect hierarchy metadata
    apps_meta, versions_meta = _collect_hierarchy_metadata(objects_dir)

    # Build hierarchy tree
    apps = build_hierarchy(screens, elements, apps_meta, versions_meta)

    # Build reference lookup
    by_reference: dict[str, AnyEntry] = {}
    for screen in screens:
        by_reference[screen.reference] = screen
    for element in elements:
        by_reference[element.reference] = element

    return Inventory(
        screens=screens,
        elements=elements,
        apps=apps,
        _by_reference=by_reference,
        library=library_meta,
    )
