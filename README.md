# cpmf-uisor

CLI tool for UiPath Object Repository analysis and bulk parameterization.

## Features

- **Inventory** - List all Screen and Element objects with detailed metadata
- **Audit** - Check parameterization status and detect issues
- **Replace** - Bulk parameterize, rename, or reset variables using rules

## Installation

```bash
cd src/cpmf_uisor
uv pip install -e .
```

## Quick Start

```bash
# List all objects
uv run python -m cpmf_uisor.cli inventory /path/to/project.json

# Audit parameterization status
uv run python -m cpmf_uisor.cli audit /path/to/project.json

# Preview replacements with rules file
uv run python -m cpmf_uisor.cli replace --config rules.toml /path/to/project.json

# Apply replacements
uv run python -m cpmf_uisor.cli replace --config rules.toml --apply /path/to/project.json
```

## Commands

### inventory

List all objects in the repository with various output formats.

```bash
# Flat text (default)
uv run python -m cpmf_uisor.cli inventory project.json

# Filter by type
uv run python -m cpmf_uisor.cli inventory project.json --type screen
uv run python -m cpmf_uisor.cli inventory project.json --type element

# Output formats
uv run python -m cpmf_uisor.cli inventory project.json --format text       # Flat text
uv run python -m cpmf_uisor.cli inventory project.json --format json       # Flat JSON
uv run python -m cpmf_uisor.cli inventory project.json --format tree       # Hierarchical text
uv run python -m cpmf_uisor.cli inventory project.json --format json-tree  # Hierarchical JSON
uv run python -m cpmf_uisor.cli inventory project.json --format markdown   # Markdown with screenshots
uv run python -m cpmf_uisor.cli inventory project.json --format html       # HTML with screenshots
uv run python -m cpmf_uisor.cli inventory project.json --format zip        # ZIP bundle (cpmf-prism-pack)
```

#### ZIP Export Format

The `--format zip` option creates a `cpmf-prism-pack` bundle at `Documentation/UIAdapter/inventory.zip`:

```
inventory.zip/
├── prism.manifest.json    # Pack manifest (cpmf-prism-pack v0.1.0)
├── data/
│   └── uisor.json         # Object Repository export (schemaVersion: v0.1.0)
└── screenshots/           # All referenced screenshots
    ├── abc123.png
    └── ...
```

### audit

Check parameterization status and detect issues.

```bash
uv run python -m cpmf_uisor.cli audit project.json

# Exit with code 1 if issues found (useful for CI)
uv run python -m cpmf_uisor.cli audit project.json --exit-code
```

**Issues detected:**
- Unsupported descriptor versions
- Hardcoded URLs containing literal wildcards
- Inconsistent scope: Element has hardcoded `ScopeSelectorArgument` but ancestor Screen has parameterized `Selector`

### replace

Bulk replace values using rules from a TOML config file.

```bash
# Preview changes (dry-run)
uv run python -m cpmf_uisor.cli replace --config rules.toml project.json

# Apply changes
uv run python -m cpmf_uisor.cli replace --config rules.toml --apply project.json

# Interactive mode (prompt for each change)
uv run python -m cpmf_uisor.cli replace --config rules.toml --apply --interactive project.json
```

## Rules Configuration

Rules are defined in TOML format. See `demo-rules.toml` for examples.

### Rule Types

| Type | Description |
|------|-------------|
| `parameterize` | Replace hardcoded value with `[varName]` |
| `rename` | Rename existing variable |
| `reset` | Reset parameterized value back to hardcoded |

### Targets

| Target | Description |
|--------|-------------|
| `screen` | Screen URL (V2) |
| `screen.selector` | Screen Selector attributes (V2) |
| `element.scope` | Element ScopeSelectorArgument (V6) |
| `element.selector` | Element FullSelectorArgument (V6) |

### Parameterize Rule

```toml
# Screen URL
[[rules]]
type = "parameterize"
target = "screen"
match = "https://www.example.com/*"
variable = "baseUrl"
default_value = "https://www.example.com/"

# Screen Selector attribute
[[rules]]
type = "parameterize"
target = "screen.selector"
attribute = "title"
match = "My App"
variable = "windowTitle"
default_value = "My App"

# With cascade to descendant elements
[[rules]]
type = "parameterize"
target = "screen.selector"
attribute = "title"
match = "Google"
variable = "windowTitle"
default_value = "Google"
cascade = true  # Auto-applies to descendant Element.ScopeSelectorArgument
```

### Cascade Feature

When `cascade = true` on a `screen.selector` rule:
1. The Screen's Selector attribute is parameterized
2. All descendant Elements' `ScopeSelectorArgument` with the same attribute value are also parameterized
3. Elements use the same variable name

This ensures coordinated parameterization when Screen.Selector and Element.ScopeSelectorArgument need to match.

### Rename Rule

```toml
[[rules]]
type = "rename"
from_variable = "oldVarName"
to_variable = "newVarName"
```

### Reset Rule

```toml
[[rules]]
type = "reset"
variable = "baseUrl"
value = "https://www.example.com/"
```

## Development

Use the Justfile for common development commands:

```bash
cd src/cpmf_uisor

just                    # List available commands
just inventory          # Run inventory (all objects)
just inventory-screens  # Run inventory (screens only)
just inventory-elements # Run inventory (elements only)
just inventory-tree     # Run inventory as tree
just inventory-json     # Run inventory as JSON tree
just inventory-zip      # Export ZIP bundle
just audit              # Run audit
just replace-preview    # Preview with demo rules
just replace-apply      # Apply with demo rules
just test               # Run tests
just typecheck          # Run mypy
```

## Files

| File | Description |
|------|-------------|
| `cli.py` | Typer CLI commands |
| `discovery.py` | Object Repository traversal |
| `models.py` | Data classes |
| `rules.py` | Rule loading and preview generation |
| `formatters.py` | Output formatting (JSON, tree, markdown, HTML) |
| `adapter_screen_V2.py` | Screen content parsing and updates |
| `adapter_element_V6.py` | Element content parsing and updates |
| `parser.py` | Metadata parsing |
| `rules.example.toml` | Example rules file |
| `Justfile` | Development commands |
| `PROBLEMS.md` | Known issues and Object Repository internals |

## Object Repository Structure

```
.objects/
├── .metadata (Library)
└── {app-id}/
    ├── .type = "App"
    ├── .metadata (name, reference)
    └── {version-id}/
        ├── .type = "AppVersion"
        └── {screen-id}/
            ├── .type = "Screen"
            ├── .metadata (name, reference, parent_ref)
            └── .data/
                └── ObjectRepositoryScreenData/
                    └── .content (V2)
```

See `PROBLEMS.md` for detailed documentation on:
- Screen vs Element attributes
- Parameterization syntax (`[varName]` vs `[string.Format(...)]`)
- Scope inheritance
- Hash management (out of scope)

## Limitations

**cpmf-uisor modifies `.content` files only.** After using this tool:

1. Open the project in UiPath Studio
2. Studio will regenerate ContentHash values
3. Existing workflow usages need manual refresh (delete and re-add object reference)

This is by design. See `PROBLEMS.md` for details.
