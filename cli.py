"""CLI commands using Typer."""

import json
import re
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from . import __schema_version__
from . import adapter_element_V6 as element_adapter
from . import adapter_screen_V2 as screen_adapter
from .discovery import audit_all, discover_all, find_objects_dir
from .models import (
    ElementEntry,
    EntryType,
    ParameterizeRule,
    ProjectMeta,
    RenameRule,
    ResetRule,
    RuleTarget,
)

app = typer.Typer(
    name="cpmf-uisor",
    help="UiPath Object Repository CLI Tool",
    no_args_is_help=True,
)


class TypeFilter(str, Enum):
    """Type filter for commands."""

    all = "all"
    screen = "screen"
    element = "element"


class OutputFormat(str, Enum):
    """Output format for inventory command."""

    text = "text"  # Flat text output
    json = "json"  # Flat JSON (backward compat)
    tree = "tree"  # Hierarchical text
    json_tree = "json-tree"  # Hierarchical JSON
    markdown = "markdown"  # Markdown with screenshots (writes to file)
    html = "html"  # HTML with screenshots (writes to file)
    zip = "zip"  # ZIP bundle with JSON + screenshots


def _parse_project_json(project_path: Path) -> ProjectMeta | None:
    """Parse project.json for metadata.

    Extracts:
    - name, projectId, projectVersion, studioVersion, targetFramework
    - UiPath.UIAutomation.Activities version from dependencies
    """
    if not project_path.exists():
        return None

    try:
        data = json.loads(project_path.read_text(encoding="utf-8"))

        # Extract UIAutomation version from dependencies
        ui_automation_version = None
        deps = data.get("dependencies", {})
        ui_dep = deps.get("UiPath.UIAutomation.Activities", "")
        if ui_dep:
            # Extract version from "[25.10.12]" or "25.10.12"
            match = re.search(r"[\d.]+", ui_dep)
            if match:
                ui_automation_version = match.group(0)

        return ProjectMeta(
            name=data.get("name", ""),
            project_id=data.get("projectId", ""),
            version=data.get("projectVersion", ""),
            studio_version=data.get("studioVersion", ""),
            target_framework=data.get("targetFramework", ""),
            ui_automation_version=ui_automation_version,
        )
    except (json.JSONDecodeError, KeyError):
        return None


@app.command()
def inventory(
    project: Path = typer.Argument(..., help="Path to project.json"),
    type_filter: TypeFilter = typer.Option(TypeFilter.all, "--type", help="Filter by type"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", "-f", help="Output format"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as flat JSON (backward compat)"),
):
    """List all objects in the repository."""
    import json as json_module

    from .discovery import discover_inventory
    from .formatters import (
        format_flat_json,
        format_html,
        format_markdown,
        format_tree_json,
        format_tree_text,
    )

    objects_dir = find_objects_dir(project)
    inv = discover_inventory(objects_dir)

    # Attach project metadata
    inv.project = _parse_project_json(project)

    # Apply type filter to flat lists
    screens = inv.screens if type_filter in (TypeFilter.all, TypeFilter.screen) else []
    elements = inv.elements if type_filter in (TypeFilter.all, TypeFilter.element) else []

    total = len(screens) + len(elements)
    if total == 0:
        typer.echo(f"No objects found in {objects_dir}")
        raise typer.Exit(0)

    # Backward compat: --json overrides --format
    if json_output:
        output_format = OutputFormat.json

    # Route to appropriate formatter
    if output_format == OutputFormat.tree:
        typer.echo(format_tree_text(inv))

    elif output_format == OutputFormat.json_tree:
        typer.echo(json_module.dumps(format_tree_json(inv), indent=2))

    elif output_format == OutputFormat.json:
        # Flat JSON - apply type filter to entries
        data = format_flat_json(inv)
        if type_filter == TypeFilter.screen:
            data["entries"] = [e for e in data["entries"] if e["type"] == "screen"]
        elif type_filter == TypeFilter.element:
            data["entries"] = [e for e in data["entries"] if e["type"] == "element"]
        typer.echo(json_module.dumps(data, indent=2))

    elif output_format == OutputFormat.markdown:
        # Markdown with screenshots - write to Documentation/UIAdapter/inventory.md
        output_dir = project.parent / "Documentation" / "UIAdapter"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "inventory.md"

        md_content = format_markdown(inv, screenshots_rel_path="../../.screenshots")
        output_path.write_text(md_content, encoding="utf-8")
        typer.echo(f"Markdown inventory written to: {output_path}")

    elif output_format == OutputFormat.html:
        # HTML with screenshots - write to Documentation/UIAdapter/inventory.html
        output_dir = project.parent / "Documentation" / "UIAdapter"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "inventory.html"

        html_content = format_html(inv, screenshots_rel_path="../../.screenshots")
        output_path.write_text(html_content, encoding="utf-8")
        typer.echo(f"HTML inventory written to: {output_path}")

    elif output_format == OutputFormat.zip:
        # ZIP bundle with manifest + data + screenshots (cpmf-prism-pack format)
        import zipfile
        from datetime import datetime, timezone

        output_dir = project.parent / "Documentation" / "UIAdapter"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "inventory.zip"

        screenshots_dir = project.parent / ".screenshots"

        # Prepare uisor data
        uisor_data = format_flat_json(inv)
        uisor_data["schemaVersion"] = __schema_version__
        if type_filter == TypeFilter.screen:
            uisor_data["entries"] = [e for e in uisor_data["entries"] if e["type"] == "screen"]
        elif type_filter == TypeFilter.element:
            uisor_data["entries"] = [e for e in uisor_data["entries"] if e["type"] == "element"]

        # Build manifest
        manifest = {
            "format": "cpmf-prism-pack",
            "version": "v0.1.0",
            "source": "uipath-studio",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "exports": [
                {
                    "type": "uisor",
                    "id": "or-main",
                    "path": "data/uisor.json",
                    "contentType": "application/json",
                    "schemaVersion": __schema_version__,
                }
            ],
        }

        # Add project metadata to manifest if available
        if inv.project:
            manifest["projectName"] = inv.project.name
            manifest["projectId"] = inv.project.project_id

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add prism.manifest.json at root
            zf.writestr("prism.manifest.json", json_module.dumps(manifest, indent=2))

            # Add data/uisor.json
            zf.writestr("data/uisor.json", json_module.dumps(uisor_data, indent=2))

            # Add screenshots
            if screenshots_dir.exists():
                for img_file in screenshots_dir.iterdir():
                    if img_file.is_file():
                        zf.write(img_file, f"screenshots/{img_file.name}")

        typer.echo(f"ZIP bundle written to: {output_path}")

    else:  # OutputFormat.text (default)
        typer.echo(f"Found {total} object(s) in {objects_dir}")
        typer.echo(f"  Screens:  {len(screens)}")
        typer.echo(f"  Elements: {len(elements)}\n")

        # Display Screens
        if screens:
            typer.echo("=== Screens (V2) ===\n")
            for e in screens:
                url_status = f"[{e.variable_name}]" if e.variable_name else "hardcoded"
                typer.echo(f"{e.full_path} [{e.descriptor_version}]")
                typer.echo(f"  URL:      {e.url} ({url_status})")
                typer.echo(f"  Selector: {_truncate(e.selector, 80)}")
                if e.declared_variables:
                    var_strs = [f"{v.name}={v.default}" for v in e.declared_variables]
                    typer.echo(f"  Variables: {', '.join(var_strs)}")
                typer.echo()

        # Display Elements
        if elements:
            typer.echo("=== Elements (V6) ===\n")
            for e in elements:
                typer.echo(f"{e.full_path} [{e.descriptor_version}]")
                typer.echo(f"  SearchSteps:   {e.search_steps}")
                typer.echo(f"  Type:          {e.element_type} / {e.activity_type}")
                typer.echo(f"  Visibility:    {e.visibility or '(not set)'}")
                typer.echo(f"  WaitForReady:  {e.wait_for_ready or '(not set)'}")
                typer.echo(f"  Scope:         {_truncate(e.scope_selector, 80)}")
                typer.echo(f"  Selector:      {_truncate(e.full_selector, 80)}")

                # Show additional selector types based on SearchSteps
                if "FuzzySelector" in e.search_steps:
                    if e.fuzzy_selector:
                        typer.echo(f"  Fuzzy:         {_truncate(e.fuzzy_selector, 80)}")
                    else:
                        typer.echo("  Fuzzy:         (configured but empty)")
                if "Image" in e.search_steps:
                    typer.echo(f"  Image:         {'present' if e.has_image else '(configured but empty)'}")
                if "CV" in e.search_steps:
                    if e.has_cv:
                        typer.echo(f"  CV:            {e.cv_type or 'present'}")
                    else:
                        typer.echo("  CV:            (configured but empty)")

                # Show parameterization status
                if e.scope_variables:
                    typer.echo(f"  Scope vars:    {', '.join(e.scope_variables)}")
                if e.selector_variables:
                    typer.echo(f"  Selector vars: {', '.join(e.selector_variables)}")
                typer.echo()


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    if not text:
        return "(empty)"
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


@app.command()
def audit(
    project: Path = typer.Argument(..., help="Path to project.json"),
    type_filter: TypeFilter = typer.Option(TypeFilter.all, "--type", help="Filter by type"),
    exit_code: bool = typer.Option(False, "--exit-code", help="Exit 1 if issues found"),
):
    """Audit repository and show statistics."""
    objects_dir = find_objects_dir(project)
    screens, elements = discover_all(objects_dir)

    # Apply type filter
    if type_filter == TypeFilter.screen:
        elements = []
    elif type_filter == TypeFilter.element:
        screens = []

    result = audit_all(screens, elements)

    typer.echo("=== Object Repository Audit ===\n")
    typer.echo(f"Total objects:    {result.total_objects}")
    typer.echo(f"  Screens:        {len(screens)}")
    typer.echo(f"  Elements:       {len(elements)}")
    typer.echo(f"Hardcoded:        {result.hardcoded_count}")
    typer.echo(f"Parameterized:    {result.parameterized_count}")

    if result.variables_in_use:
        typer.echo(f"\nVariables in use: {', '.join(sorted(result.variables_in_use))}")

    if result.version_counts:
        typer.echo("\nVersions:")
        for version, count in sorted(result.version_counts.items()):
            typer.echo(f"  {version}: {count}")

    if result.issues:
        typer.echo("\nIssues:")
        for issue in result.issues:
            typer.echo(f"  - {issue}")

    if exit_code and result.has_issues:
        raise typer.Exit(1)


@app.command()
def replace(
    project: Path = typer.Argument(..., help="Path to project.json"),
    config: Optional[Path] = typer.Option(None, "--config", help="Path to rules TOML file"),
    type_filter: TypeFilter = typer.Option(TypeFilter.all, "--type", help="Filter by type"),
    apply: bool = typer.Option(False, "--apply", help="Apply changes (default: dry-run)"),
    force: bool = typer.Option(False, "--force", help="Allow mutations on unsupported versions"),
    interactive: bool = typer.Option(False, "--interactive", help="Prompt for each object"),
):
    """Replace values using rules from config or interactive prompts."""
    from .rules import load_rules, preview_replacements

    objects_dir = find_objects_dir(project)
    screens, elements = discover_all(objects_dir)

    # Apply type filter
    if type_filter == TypeFilter.screen:
        elements = []
    elif type_filter == TypeFilter.element:
        screens = []

    if not screens and not elements:
        typer.echo("No objects found")
        raise typer.Exit(0)

    # Load rules from config or prompt interactively
    if config:
        rules = load_rules(config)
    else:
        rules = _prompt_for_rules()

    if not rules:
        typer.echo("No rules defined")
        raise typer.Exit(0)

    # Preview replacements
    previews, warnings = preview_replacements(screens, elements, rules, force=force)

    # Show warnings
    for warning in warnings:
        typer.echo(f"WARNING: {warning}")

    if not previews:
        typer.echo("\nNo matches found")
        raise typer.Exit(0)

    # Show preview
    typer.echo(f"\n{'[DRY RUN] ' if not apply else ''}Replacements:\n")

    for preview in previews:
        typer.echo(f"{preview.entry.full_path}")

        # Determine label for the attribute being changed
        is_element = preview.entry.entry_type == EntryType.ELEMENT
        if is_element and preview.attribute:
            # Show which selector attribute is being changed
            rule_target = preview.rule.target if hasattr(preview.rule, "target") else None
            if preview.attribute == "scope" or rule_target == RuleTarget.ELEMENT_SCOPE:
                label = "ScopeSelectorArgument"
            elif preview.attribute == "selector" or rule_target == RuleTarget.ELEMENT_SELECTOR:
                label = "FullSelectorArgument"
            else:
                label = f"ScopeSelectorArgument ({preview.attribute})"
            typer.echo(f"  {label}:")
        elif preview.attribute:
            typer.echo(f"  Selector ({preview.attribute}):")
        else:
            typer.echo(f"  Url:")

        typer.echo(f"    - {preview.old_value}")
        typer.echo(f"    + {preview.new_value}")

        if interactive and apply:
            confirm = typer.confirm("  Apply this change?", default=True)
            if confirm:
                success = _apply_preview(preview)
                typer.echo(f"  {'OK' if success else 'FAILED'}")
            else:
                typer.echo("  Skipped")
        typer.echo()

    # Batch apply if not interactive
    if apply and not interactive:
        confirm = typer.confirm(f"\nApply {len(previews)} change(s)?", default=False)
        if confirm:
            success_count = sum(1 for p in previews if _apply_preview(p))
            typer.echo(f"\nApplied {success_count}/{len(previews)} changes")
        else:
            typer.echo("Aborted")
    elif not apply:
        typer.echo("Run with --apply to make changes")


def _apply_preview(preview) -> bool:
    """Apply a single replacement preview and manage ObjectRepositoryVariableData."""
    path = preview.entry.content_path
    rule = preview.rule

    # Determine which adapter to use
    is_screen = preview.entry.entry_type == EntryType.SCREEN
    adapter = screen_adapter if is_screen else element_adapter

    # Apply the value update
    if is_screen:
        # Check if this is a screen.selector rule (has attribute set)
        if preview.attribute:
            success = screen_adapter.update_selector_attr(
                path,
                preview.attribute,
                preview.old_value,
                preview.new_value,
            )
        else:
            # Screen URL rule
            success = screen_adapter.update_content(
                path,
                preview.old_value,
                preview.new_value,
            )
    else:
        # Element - use element adapter with string.Format for parameterization
        entry: ElementEntry = preview.entry
        # attr_value is the actual attribute value (e.g., "Google"), old_value is full selector
        attr_value = preview.attr_value or preview.old_value

        # Check if this is a ParameterizeRule with a specific attribute
        if isinstance(rule, ParameterizeRule) and preview.attribute:
            # Use string.Format wrapper for element selector parameterization
            # Determine which selector based on rule target
            if rule.target == RuleTarget.ELEMENT_SELECTOR:
                success = element_adapter.update_full_selector_parameterized(
                    path,
                    entry.full_selector,
                    preview.attribute,
                    attr_value,
                    rule.variable,
                )
            else:
                # Default to scope selector (element.scope or ALL target)
                success = element_adapter.update_scope_selector_parameterized(
                    path,
                    entry.scope_selector,
                    preview.attribute,
                    attr_value,
                    rule.variable,
                )
        else:
            # Non-parameterize rules (rename, reset) - use simple attribute update
            success = element_adapter.update_scope_attr(
                path,
                preview.attribute or "title",
                attr_value,
                preview.new_value,
            )

    if not success:
        return False

    # Manage ObjectRepositoryVariableData based on rule type
    if isinstance(rule, ParameterizeRule):
        # Add variable declaration with default value
        adapter.ensure_variable(path, rule.variable, rule.default_value)

    elif isinstance(rule, ResetRule):
        # Remove variable declaration (no longer used)
        adapter.remove_variable(path, rule.variable)

    elif isinstance(rule, RenameRule):
        # Remove old variable, add new variable
        adapter.remove_variable(path, rule.from_variable)
        adapter.ensure_variable(path, rule.to_variable, "*")

    return True


def _prompt_for_rules() -> list:
    """Interactively prompt user for replacement rules."""
    typer.echo("Define replacement rule:\n")

    rule_type = typer.prompt(
        "Type",
        type=typer.Choice(["parameterize", "rename", "reset"]),
    )

    if rule_type == "parameterize":
        match = typer.prompt("Pattern to match (supports wildcards)")
        variable = typer.prompt("Variable name")
        return [ParameterizeRule(match=match, variable=variable)]

    elif rule_type == "rename":
        from_var = typer.prompt("From variable")
        to_var = typer.prompt("To variable")
        return [RenameRule(from_variable=from_var, to_variable=to_var)]

    elif rule_type == "reset":
        variable = typer.prompt("Variable name")
        value = typer.prompt("Value to reset to")
        return [ResetRule(variable=variable, value=value)]

    return []


if __name__ == "__main__":
    app()
