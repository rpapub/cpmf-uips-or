# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-03-08

### Added
- mypy strict configuration with full type checking
- pytest + pytest-cov configuration with 70% coverage threshold
- Test suite: 147 unit tests covering models, parser, adapters, discovery, formatters, rules
- GitHub Actions CI: test (3.11–3.13), lint, typecheck, build jobs
- Pre-commit hooks: ruff, mypy, trailing-whitespace, check-yaml/toml
- `twine` dev dependency for `uv run twine check dist/*`

### Changed
- `pyproject.toml`: migrated dev deps from `[project.optional-dependencies]` to `[dependency-groups]`
- `Justfile`: fixed `typecheck` path (`src/cpmf_uisor/` → `cpmf_uips_or/`); added `check`, `format`, `build` targets
- `README.md` is now the canonical readme (was `!README.md` in pyproject.toml)
- Ruff config: removed deprecated `W` selector, removed redundant `E501` ignore (line-length=100 covers it), added `UP` and `B` rule sets
- Fixed mypy type errors: proper `ReplaceRule` inheritance hierarchy using `@dataclass(kw_only=True)`, loop variable naming conflicts, missing return type annotations

### Fixed
- `ParameterizeRule`, `RenameRule`, `ResetRule` now properly inherit from `ReplaceRule`
- Variable naming conflicts in `discovery.py`, `rules.py`, `cli.py` for loops
- `typer.Choice` → `click.Choice` (removed non-existent `typer.Choice` usage)
- `__schema_version__` added to `__init__.__all__`

## [0.1.1] - 2025-12-01

### Added
- Element V6 support (ObjectRepositoryTargetData)
- Cascade support: screen.selector rules cascade to descendant element.scope
- HTML and Markdown output formatters with Jinja templates
- ZIP bundle export (cpmf-prism-pack format)

## [0.1.0] - 2025-10-01

### Added
- Initial release
- Screen V2 (ObjectRepositoryScreenData) parsing and mutation
- URL parameterization with `[varName]` syntax
- TOML-based replacement rules (parameterize, rename, reset)
- CLI commands: inventory, audit, replace, orphans
