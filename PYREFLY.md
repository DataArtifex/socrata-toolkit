# PYREFLY Migration Guide

This document describes the recommended, low-risk migration path for replacing mypy with pyrefly in this repository.

## Goals
- Move type checking from mypy to pyrefly.
- Keep CI and local workflows green during migration.
- Avoid a risky one-shot switch.

## Environment Profiles

This template supports two local development modes.

### Profile A: Monorepo Shared Environment (default in this repo)

- A parent/shared environment is activated before working in this package.
- Use `--active` for local `uv run` commands.
- Use `uv sync --inexact` to avoid pruning sibling-project packages.

### Profile B: Standalone Project Environment

- The package has its own local project environment.
- Do not use `--active`.
- Use normal exact sync behavior.

Quick command mapping:

```text
Monorepo:   uv sync --group dev --active --inexact
Standalone: uv sync --group dev

Monorepo:   uv run --active pyrefly check src tests
Standalone: uv run pyrefly check src tests
```

## Shared Template Strategy (One Pre-commit File)

Because this repository is a template, keep a single `.pre-commit-config.yaml` for all contributors.

Use a small wrapper script (`scripts/precommit_uv_run.sh`) as the hook entry:

- If `VIRTUAL_ENV` is set, it runs `uv run --active ...` (monorepo/shared-env mode).
- If `VIRTUAL_ENV` is not set, it runs `uv run ...` (standalone mode).

This avoids maintaining separate pre-commit configs for different project layouts.

## Monorepo Environment Note

This package lives inside a monorepo and should use the parent/shared virtual environment.

- Do not create or rely on a local package `.venv`.
- For local commands, use `uv --active` mode so `uv` uses the active environment.
- Avoid running plain `uv run ...` locally in this package; it may create a local `.venv`.
- In a shared monorepo environment, use `uv sync --inexact` to avoid pruning packages installed by sibling projects.

Before running local commands, make sure the shared monorepo environment is actually active:

```bash
echo "$VIRTUAL_ENV"
```

If this is empty, `uv run --active ...` may fall back to the project environment path and create a local `.venv`.

### Why `uv sync --active` can remove sibling packages

In this monorepo setup, `--active` only changes the target environment. It does not change `sync` reconciliation behavior.

- `uv sync --active` is still exact by default.
- Exact sync prunes packages not declared by the current package's `pyproject.toml`.
- In a shared environment, this can remove dependencies required by sibling projects.

Use this local command pattern instead:

```bash
uv sync --group dev --active --inexact
```

Also expected warning context:

- If `VIRTUAL_ENV` points to the monorepo environment but the current package has a project `.venv` path, `uv` may warn about a mismatch.
- `--active` tells `uv` to target the active environment explicitly.

Examples:

```bash
uv sync --group dev --active --inexact
uv run --active pyrefly check src tests
```

## Current Baseline

- pyrefly check currently succeeds on src and tests.
- Pre-commit is configured with local hooks for Ruff and pyrefly in `.pre-commit-config.yaml`.
- CI type checking uses pyrefly in `.github/workflows/test.yml`.
