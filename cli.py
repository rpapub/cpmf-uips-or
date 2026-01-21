"""CLI commands using Typer."""

from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from . import adapter_screen_V2 as screen_adapter
from .discovery import audit_all, discover_all, find_objects_dir
from .models import (
    EntryType,
    ParameterizeRule,
    RenameRule,
    ResetRule,
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
        # Flat JSON - apply type filter
        data = format_flat_json(inv)
        if type_filter == TypeFilter.screen:
            data = [d for d in data if d["type"] == "screen"]
        elif type_filter == TypeFilter.element:
            data = [d for d in data if d["type"] == "element"]
        typer.echo(json_module.dumps(data, indent=2))

    elif output_format == OutputFormat.markdown:
        # Markdown with screenshots - write to Documentation/inventory.md
        docs_dir = project.parent / "Documentation"
        docs_dir.mkdir(exist_ok=True)
        output_path = docs_dir / "inventory.md"

        md_content = format_markdown(inv, screenshots_rel_path="../.screenshots")
        output_path.write_text(md_content, encoding="utf-8")
        typer.echo(f"Markdown inventory written to: {output_path}")

    elif output_format == OutputFormat.html:
        # HTML with screenshots - write to Documentation/inventory.html
        docs_dir = project.parent / "Documentation"
        docs_dir.mkdir(exist_ok=True)
        output_path = docs_dir / "inventory.html"

        html_content = format_html(inv, screenshots_rel_path="../.screenshots")
        output_path.write_text(html_content, encoding="utf-8")
        typer.echo(f"HTML inventory written to: {output_path}")

    else:  # OutputFormat.text (default)
        typer.echo(f"Found {total} object(s) in {objects_dir}")
        typer.echo(f"  Screens:  {len(screens)}")
        typer.echo(f"  Elements: {len(elements)}\n")

        # Display Screens
        if screens:
            typer.echo("=== Screens (V2) ===\n")
            for e in screens:
                status = f"[{e.variable_name}]" if e.variable_name else "hardcoded"
                typer.echo(f"{e.full_path}")
                typer.echo(f"  URL:     {e.url} ({status})")
                typer.echo(f"  Version: {e.descriptor_version}")
                typer.echo()

        # Display Elements
        if elements:
            typer.echo("=== Elements (V6) ===\n")
            for e in elements:
                param_status = "parameterized" if e.is_parameterized else "hardcoded"
                typer.echo(f"{e.full_path}")
                typer.echo(f"  SearchSteps: {e.search_steps}")
                typer.echo(f"  Type:        {e.element_type} / {e.activity_type}")
                typer.echo(f"  Status:      {param_status}")
                if e.scope_variables:
                    typer.echo(f"  Scope vars:  {', '.join(e.scope_variables)}")
                if e.selector_variables:
                    typer.echo(f"  Selector vars: {', '.join(e.selector_variables)}")
                typer.echo()


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
        if preview.attribute:
            typer.echo(f"  Attribute: {preview.attribute}")
        typer.echo(f"  - {preview.old_value}")
        typer.echo(f"  + {preview.new_value}")

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
    """Apply a single replacement preview."""

    if preview.entry.entry_type == EntryType.SCREEN:
        return screen_adapter.update_content(
            preview.entry.content_path,
            preview.old_value,
            preview.new_value,
        )
    else:
        # Element - use element adapter
        from . import adapter_element_V6 as element_adapter

        return element_adapter.update_scope_attr(
            preview.entry.content_path,
            preview.attribute or "title",
            preview.old_value,
            preview.new_value,
        )


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
