"""Data models for Object Repository entries."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Union


class UrlStatus(Enum):
    """URL parameterization status."""

    HARDCODED = "hardcoded"
    PARAMETERIZED = "parameterized"


@dataclass
class VariableDecl:
    """Declared variable from ObjectRepositoryVariableData."""

    name: str
    default: str = "*"


class EntryType(Enum):
    """Object entry type."""

    SCREEN = "screen"
    ELEMENT = "element"


# ---------- Project and Library metadata ----------


@dataclass
class ProjectMeta:
    """Metadata from project.json."""

    name: str
    project_id: str
    version: str
    studio_version: str
    target_framework: str
    ui_automation_version: str | None = None


@dataclass
class LibraryMeta:
    """Metadata from .objects/.metadata (Library level)."""

    id: str
    created: str
    created_by: list[str]


# ---------- Entry classes ----------


@dataclass
class ScreenEntry:
    """Represents a Screen (V2) in the Object Repository."""

    app_name: str
    app_version: str
    screen_name: str
    url: str
    url_status: UrlStatus
    variable_name: str | None  # Set if parameterized
    selector: str
    reference: str
    descriptor_version: str  # V2
    content_path: Path
    parent_ref: str | None = None  # Reference to parent AppVersion
    screenshot: str | None = None  # InformativeScreenshot filename
    screenshot_width: int | None = None  # Screenshot width in pixels
    screenshot_height: int | None = None  # Screenshot height in pixels
    declared_variables: list[VariableDecl] | None = None  # ObjectRepositoryVariableData entries
    depth: int = 2  # Hierarchy depth: App(0) > Version(1) > Screen(2)

    # Audit metadata from .metadata file
    created: str | None = None
    updated: str | None = None
    created_by: list[str] | None = None
    updated_by: list[str] | None = None

    entry_type: EntryType = field(default=EntryType.SCREEN, init=False)

    @property
    def full_path(self) -> str:
        """App/Version/Screen path."""
        return f"{self.app_name}/{self.app_version}/{self.screen_name}"


# Alias for backwards compatibility
ObjectEntry = ScreenEntry


@dataclass
class ElementEntry:
    """Represents an Element (V6) in the Object Repository."""

    app_name: str
    app_version: str
    screen_name: str
    element_name: str
    search_steps: str  # Targeting strategy (Selector, Image, CV, etc.)
    scope_selector: str  # ScopeSelectorArgument
    full_selector: str  # FullSelectorArgument
    browser_url: str  # Informational only
    element_type: str  # Text, InputBox, Button, etc.
    activity_type: str  # Click, TypeInto, etc.
    reference: str
    descriptor_version: str  # V6
    content_path: Path
    parent_ref: str | None = None  # Reference to parent Screen or Element
    screenshot: str | None = None  # InformativeScreenshot filename
    screenshot_width: int | None = None  # Screenshot width in pixels
    screenshot_height: int | None = None  # Screenshot height in pixels

    # Additional selector types
    fuzzy_selector: str = ""  # FuzzySelectorArgument
    has_image: bool = False  # ImageBase64 present and non-empty
    has_cv: bool = False  # CV attributes present
    cv_type: str = ""  # CvType (InputBox, Text, Button, etc.)

    # Runtime behavior attributes
    visibility: str = ""  # Visibility (Interactive, None, etc.)
    wait_for_ready: str = ""  # WaitForReadyArgument (Interactive, Complete, None)

    # Parameterization status for scope and selector
    scope_variables: list[str] = field(default_factory=list)
    selector_variables: list[str] = field(default_factory=list)

    # Declared variables from ObjectRepositoryVariableData
    declared_variables: list[VariableDecl] | None = None
    depth: int = 3  # Hierarchy depth: App(0) > Version(1) > Screen(2) > Element(3+)

    # Audit metadata from .metadata file
    created: str | None = None
    updated: str | None = None
    created_by: list[str] | None = None
    updated_by: list[str] | None = None

    entry_type: EntryType = field(default=EntryType.ELEMENT, init=False)

    @property
    def full_path(self) -> str:
        """App/Version/Screen/Element path."""
        return f"{self.app_name}/{self.app_version}/{self.screen_name}/{self.element_name}"

    @property
    def is_parameterized(self) -> bool:
        """Check if any selector contains variables."""
        return bool(self.scope_variables or self.selector_variables)


# Union type for any entry
AnyEntry = Union[ScreenEntry, ElementEntry]


@dataclass
class AuditResult:
    """Aggregated audit statistics."""

    total_objects: int = 0
    hardcoded_count: int = 0
    parameterized_count: int = 0
    variables_in_use: set[str] = field(default_factory=set)
    version_counts: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0 or self.hardcoded_count > 0


class RuleTarget(Enum):
    """Rule target type."""

    ALL = "all"  # Default: applies to all types
    SCREEN = "screen"  # V2 Screen URLs only
    SCREEN_SELECTOR = "screen.selector"  # V2 Screen Selector attributes
    ELEMENT_SCOPE = "element.scope"  # V6 ScopeSelectorArgument
    ELEMENT_SELECTOR = "element.selector"  # V6 FullSelectorArgument


@dataclass
class ReplaceRule:
    """Base class for replacement rules."""

    target: RuleTarget = RuleTarget.ALL  # Default: all types


@dataclass
class ParameterizeRule:
    """Rule to replace hardcoded value with variable."""

    match: str  # Pattern to match
    variable: str  # Variable name to use
    target: RuleTarget = RuleTarget.ALL  # Default: all types
    attribute: str | None = None  # For element rules: which attribute
    default_value: str = "*"  # DefaultValue for ObjectRepositoryVariableData
    cascade: bool = False  # If true, cascade screen.selector to descendant element.scope


@dataclass
class RenameRule:
    """Rule to rename a variable."""

    from_variable: str
    to_variable: str
    target: RuleTarget = RuleTarget.ALL  # Default: all types


@dataclass
class ResetRule:
    """Rule to reset variable back to hardcoded value."""

    variable: str
    value: str  # Renamed from 'url' to be more generic
    target: RuleTarget = RuleTarget.ALL  # Default: all types


@dataclass
class ReplacePreview:
    """Preview of a replacement operation."""

    entry: AnyEntry
    old_value: str  # Full value for display (URL or full selector)
    new_value: str  # Full new value for display
    rule: ReplaceRule
    attribute: str | None = None  # For element rules: which attribute was changed
    attr_value: str | None = None  # Matched attribute value (e.g., "Google") for apply logic


# ---------- Hierarchy classes for tree representation ----------


@dataclass
class ElementNode:
    """Element node in hierarchy tree."""

    entry: ElementEntry  # Contains search_steps, element_type, etc.
    children: list["ElementNode"] = field(default_factory=list)


@dataclass
class ScreenNode:
    """Screen node in hierarchy tree."""

    entry: ScreenEntry
    elements: list[ElementNode] = field(default_factory=list)


@dataclass
class VersionNode:
    """AppVersion node in hierarchy tree."""

    name: str
    reference: str
    parent_ref: str | None
    screens: list[ScreenNode] = field(default_factory=list)
    # Audit metadata
    created: str | None = None
    created_by: list[str] | None = None


@dataclass
class AppNode:
    """App node in hierarchy tree."""

    name: str
    reference: str
    versions: list[VersionNode] = field(default_factory=list)
    # Audit metadata
    created: str | None = None
    created_by: list[str] | None = None


@dataclass
class Inventory:
    """Complete inventory with flat lists and hierarchy tree."""

    screens: list[ScreenEntry]  # Flat list (backward compat)
    elements: list[ElementEntry]  # Flat list (backward compat)
    apps: list[AppNode]  # Hierarchy tree
    _by_reference: dict[str, AnyEntry] = field(default_factory=dict, repr=False)
    # Project and library metadata
    project: ProjectMeta | None = None
    library: LibraryMeta | None = None
