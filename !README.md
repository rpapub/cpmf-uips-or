# cpmf-uisor

CLI tool for UiPath Object Repository `.objects/` directories. Reads, audits, and modifies Screen URLs (V2) and Element selectors (V6).

> File named `!README.md` to appear first in GitHub Gist (lexicographic sort).

## Installation

Requires Python 3.11+. Run directly with [uv](https://github.com/astral-sh/uv):

```bash
uv run cpmf-uisor --help
```

## Object Repository Structure

UiPath stores UI automation targets in `.objects/` with this hierarchy:

```
.objects/
  {hash}/          # App
    .type          # Contains "App"
    .metadata      # XML: Name, Reference
    {hash}/        # AppVersion
      .type        # Contains "AppVersion"
      .metadata    # XML: Name, Reference, ParentRef
      {hash}/      # Screen
        .type      # Contains "Screen"
        .metadata  # XML: Name, Reference, ParentRef
        .data/ObjectRepositoryScreenData/.content   # V2: URL, Selector
        {hash}/    # Element
          .type    # Contains "Element"
          .metadata
          .data/ObjectRepositoryTargetData/.content # V6: Selectors
```

## Commands

### inventory

List objects with parameterization status.

```bash
# Flat text (default)
cpmf-uisor inventory path/to/project.json

# Filter by type
cpmf-uisor inventory path/to/project.json --type screen
cpmf-uisor inventory path/to/project.json --type element

# Output formats
cpmf-uisor inventory path/to/project.json --format text       # Flat text
cpmf-uisor inventory path/to/project.json --format json       # Flat JSON array
cpmf-uisor inventory path/to/project.json --format tree       # Hierarchical text
cpmf-uisor inventory path/to/project.json --format json-tree  # Hierarchical JSON
cpmf-uisor inventory path/to/project.json --format markdown   # Writes Documentation/inventory.md
cpmf-uisor inventory path/to/project.json --format html       # Writes Documentation/inventory.html
```

### audit

Report statistics and issues.

```bash
cpmf-uisor audit path/to/project.json
cpmf-uisor audit path/to/project.json --type screen
cpmf-uisor audit path/to/project.json --exit-code  # Exit 1 if issues found
```

Output includes:
- Total objects (Screens, Elements)
- Hardcoded vs parameterized counts
- Variables in use
- Version distribution
- Issues (unsupported versions, literal `*` in URLs)

### replace

Apply parameterization rules. Dry-run by default.

```bash
# Dry-run with config file
cpmf-uisor replace path/to/project.json --config rules.toml

# Apply changes
cpmf-uisor replace path/to/project.json --config rules.toml --apply

# Interactive mode (prompt per object)
cpmf-uisor replace path/to/project.json --config rules.toml --apply --interactive

# Interactive rule creation (no config file)
cpmf-uisor replace path/to/project.json --interactive

# Include unsupported versions
cpmf-uisor replace path/to/project.json --config rules.toml --force
```

## Rules Configuration (TOML)

Three rule types modify `.content` files. Rules are evaluated in order; **first matching rule wins**.

| Type | Purpose | Required Fields |
|------|---------|-----------------|
| `parameterize` | Hardcoded value → `[variable]` | `match`, `variable` |
| `rename` | `[oldVar]` → `[newVar]` | `from_variable`, `to_variable` |
| `reset` | `[variable]` → hardcoded value | `variable`, `value` |

### Targets

| Target | Applies To |
|--------|------------|
| `all` (default) | Screen URLs + Element selectors |
| `screen` | V2 Screen URLs only |
| `element.scope` | V6 `ScopeSelectorArgument` only |
| `element.selector` | V6 `FullSelectorArgument` only |

### Examples

```toml
# Parameterize base URL (wildcard preserves path suffix)
# https://cms.example.com/app/login → [cmsBaseUrl]login
[[rules]]
type = "parameterize"
match = "https://cms.example.com/app/*"
variable = "cmsBaseUrl"

# Parameterize element title attribute in scope selector
# <html title='Login Page - CMS' /> → <html title='[windowTitle]' />
[[rules]]
type = "parameterize"
target = "element.scope"
attribute = "title"
match = "Login Page*"
variable = "windowTitle"

# Rename variable across all types
[[rules]]
type = "rename"
from_variable = "oldBaseUrl"
to_variable = "baseUrl"

# Reset variable to hardcoded value
[[rules]]
type = "reset"
variable = "testUrl"
value = "https://test.example.com/"
```

## Variable Syntax

Both V2 Screens and V6 Elements use `[expression]` syntax. The expression can be:

- Simple variable: `[baseUrl]`
- Config lookup: `[Config("CmsBaseUrl").ToString()]`
- Any VB.NET expression UiPath accepts

Examples:
- **V2 Screen URL**: `[baseUrl]pages/login.xhtml`
- **V6 Selector attribute**: `<html title='[windowTitle]' />`

XML special characters (`"`, `<`, `>`, `&`, `'`) in variable expressions are automatically escaped when writing to `.content` files.

## Supported Versions

| Type | Version | File |
|------|---------|------|
| Screen | V2 | `.data/ObjectRepositoryScreenData/.content` |
| Element | V6 | `.data/ObjectRepositoryTargetData/.content` |

Unsupported versions are skipped by default. Use `--force` to include them.

## Files

| File | Purpose |
|------|---------|
| `cli.py` | Typer CLI commands |
| `discovery.py` | Traverse `.objects/`, build hierarchy |
| `models.py` | Data classes (ScreenEntry, ElementEntry, Inventory) |
| `parser.py` | Parse `.metadata` and `.content` XML |
| `adapter_screen_V2.py` | V2 Screen URL handling |
| `adapter_element_V6.py` | V6 Element selector handling |
| `rules.py` | Load and apply TOML rules |
| `formatters.py` | Output formatters (text, JSON, markdown, HTML) |
| `templates.py` | Jinja2 templates for markdown/HTML |
