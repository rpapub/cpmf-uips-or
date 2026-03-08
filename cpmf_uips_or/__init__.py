"""cpmf-uips-or: UiPath Object Repository CLI Tool."""

from .__version__ import __description__, __schema_version__, __version__

# Core discovery
from .discovery import (
    audit_all,
    audit_objects,
    discover_all,
    discover_inventory,
    discover_objects,
    find_objects_dir,
)

# Formatters
from .formatters import (
    format_flat_json,
    format_html,
    format_markdown,
    format_tree_json,
    format_tree_text,
)

# Data models
from .models import (
    AuditResult,
    ElementEntry,
    EntryType,
    Inventory,
    ParameterizeRule,
    RenameRule,
    ReplacePreview,
    ResetRule,
    RuleTarget,
    ScreenEntry,
    UrlStatus,
)

# Rules
from .rules import load_rules, preview_replacements

__all__ = [
    # Version
    "__version__",
    "__schema_version__",
    "__description__",
    # Discovery
    "discover_inventory",
    "discover_all",
    "discover_objects",
    "audit_all",
    "audit_objects",
    "find_objects_dir",
    # Models
    "Inventory",
    "ScreenEntry",
    "ElementEntry",
    "AuditResult",
    "UrlStatus",
    "EntryType",
    "RuleTarget",
    "ParameterizeRule",
    "RenameRule",
    "ResetRule",
    "ReplacePreview",
    # Rules
    "load_rules",
    "preview_replacements",
    # Formatters
    "format_tree_text",
    "format_tree_json",
    "format_flat_json",
    "format_markdown",
    "format_html",
]
