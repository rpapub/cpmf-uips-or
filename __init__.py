"""cpmf-uisor: UiPath Object Repository CLI Tool."""

__version__ = "0.1.2"
__schema_version__ = "v0.1.2"  # JSON export schema version

# Core discovery
from .discovery import (
    audit_all,
    audit_objects,
    discover_all,
    discover_inventory,
    discover_objects,
    find_objects_dir,
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

# Formatters
from .formatters import (
    format_flat_json,
    format_html,
    format_markdown,
    format_tree_json,
    format_tree_text,
)

__all__ = [
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
