# cpmf-uisor development commands

# Default project path
project := "/mnt/d/git.dhl.com/RPA-PEP-CSC/041_Handle_Registration_Postcard_eSAV/project.json"

# List available commands
default:
    @just --list

# Run tests
test:
    uv run pytest tests/ -v

# Lint check
lint:
    uv run ruff check cpmf_uips_or/ tests/
    uv run ruff format --check cpmf_uips_or/ tests/

# Type check
typecheck:
    uv run mypy cpmf_uips_or/

# Format code
format:
    uv run ruff format cpmf_uips_or/ tests/
    uv run ruff check --fix cpmf_uips_or/ tests/

# Run all checks (lint + typecheck + test)
check: lint typecheck test

# Build package
build:
    uv build
    uv run twine check dist/*

# Install package in editable mode
install:
    uv pip install -e .

# Run inventory (all objects)
inventory:
    uv run python -m cpmf_uips_or.cli inventory {{project}}

# Run inventory (screens only)
inventory-screens:
    uv run python -m cpmf_uips_or.cli inventory {{project}} --type screen

# Run inventory (elements only)
inventory-elements:
    uv run python -m cpmf_uips_or.cli inventory {{project}} --type element

# Run inventory as tree
inventory-tree:
    uv run python -m cpmf_uips_or.cli inventory {{project}} --format tree

# Run inventory as JSON tree
inventory-json:
    uv run python -m cpmf_uips_or.cli inventory {{project}} --format json-tree

# Export ZIP bundle (JSON + screenshots)
inventory-zip:
    uv run python -m cpmf_uips_or.cli inventory {{project}} --format zip

# Run audit
audit:
    uv run python -m cpmf_uips_or.cli audit {{project}}

# Preview replacements with example rules
replace-preview:
    uv run python -m cpmf_uips_or.cli replace --config rules.example.toml {{project}}

# Apply replacements with example rules
replace-apply:
    uv run python -m cpmf_uips_or.cli replace --config rules.example.toml --apply {{project}}

# Preview replacements with custom rules file
replace-preview-config config:
    uv run python -m cpmf_uips_or.cli replace --config {{config}} {{project}}

# Apply replacements with custom rules file
replace-apply-config config:
    uv run python -m cpmf_uips_or.cli replace --config {{config}} --apply {{project}}
