# Implementation Details

This document describes the technical architecture and implementation of the **Socrata Toolkit** (`dartfx-socrata`), with particular focus on the command-line interface (CLI), catalog discovery, metadata transformations, and Data Artifex ecosystem practices.

## Architecture Overview

```
src/dartfx/socrata/
├── __about__.py           # Dynamic package version
├── __init__.py            # Public package API exports
├── __main__.py            # Entry point for python -m dartfx.socrata
├── cli.py                 # Typer & Rich CLI implementation
├── dcat.py                # W3C DCAT metadata generator via dartfx-dcat
├── socrata.py             # Core Socrata client models & discovery
└── templates/             # Jinja2 templates for multi-language codegen
    ├── generate_jquery.j2
    ├── generate_powershell.j2
    ├── generate_python-pandas.j2
    ├── generate_r-socrata.j2
    ├── generate_sas.j2
    ├── generate_soda-dotnet.j2
    ├── generate_soda-ruby.j2
    └── generate_stata.j2
```

## CLI Architecture (`cli.py`)

The CLI is built with **Typer** and styled with **Rich**, adhering strictly to Data Artifex standards:

### 1. Robust Argument & IO Normalization
- **Smart Dashes Sanitization**: `_normalize_smart_dashes()` intercepts macOS typography quirks (en-dashes, em-dashes, minus signs) and normalizes them to standard CLI option dashes (`--`).
- **Dynamic Console Proxy**: `_ConsoleProxy` ensures that Rich's `Console` binds dynamically to active standard input/output streams per command execution, avoiding stream closure issues during testing or subprocess isolation.
- **Output Sanitization**: `_write_or_print()` handles output routing—writing cleanly to disk when `--output / -o` is specified (including automatic file naming with `AUTO`), or streaming to stdout via `typer.echo()` / `console.print_json()` to support shell pipes.

### 2. Command Surface

| Command | Aliases | Description |
|---|---|---|
| `version` | - | Print package version. |
| `servers` | `list` | Enumerate known Socrata open data portals with publisher and spatial coverage. |
| `info` | - | Probe a Socrata server's live health, catalog dataset counts, and metadata. |
| `search` | `catalog` | Search the Socrata Discovery API (`/api/catalog/v1`) with full query, category, sort, and pagination support. |
| `dataset` | `show`, `inspect` | Display comprehensive metadata and schema summary for a dataset ID. |
| `variables` | `columns` | Detailed column inspection (types, render types, cardinality, nullability, examples). |
| `export` | `metadata` | Export dataset metadata to standard formats: W3C DCAT (Turtle, JSON-LD, XML, N-Triples), ML Croissant, DDI-Codebook 2.5, Markdown, or JSON. |
| `code` | `codegen` | Generate client data access scripts (Python, R, Ruby, Stata, SAS, .NET, PowerShell, jQuery). |

### 3. Output Formats

Commands supporting tabular data provide structured output across 4 formats:
- `table`: Formatted Rich table with ANSI color coding, column justification, and clickable URLs.
- `json`: Pretty-printed JSON representation.
- `csv`: Comma-separated values stream for piping to spreadsheets or CLI tools.
- `markdown` / `md`: GitHub Flavored Markdown table.

## Socrata Discovery & Catalog Integration (`socrata.py`)

- **Discovery API**: `SocrataServer.search_datasets()` targets `/api/catalog/v1?search_context={host}&only=datasets`. Supports parameters:
  - `q`: Free-text keyword search
  - `limit` / `offset`: Pagination controls
  - `categories`: Domain category filter
  - `order` & `sort_order`: Sorting across `updatedAt`, `createdAt`, `name`, `page_views_total`, etc.
- **Portal Registry**: `SERVERS` dictionary cataloging known municipal, state, and federal open data portals (NYC, SF, Chicago, CDC, Utah, Washington, Austin, Seattle, Colorado, Los Angeles, Colombia, etc.).
- **Caching**: Multi-tiered cache supporting both in-memory session caching and persistent filesystem disk cache (`disk_cache_root` / `disk_cache_dir`).

## Metadata Transformation Pipeline

1. **W3C DCAT (`dcat.py`)**:
   - Built on `dartfx.dcat` Pydantic models (`Catalog`, `Dataset`, `Distribution`, `DataService`).
   - Supports multi-dataset catalog aggregation into a unified RDF graph.
   - Serializes to Turtle (`ttl`), JSON-LD, RDF/XML (`pretty-xml`), or N-Triples (`nt`).
2. **ML Croissant (`socrata.py`)**:
   - Generates machine-learning-ready Croissant metadata via `mlcroissant`.
   - Maps Socrata data types to Croissant data types (`DataType.FLOAT`, `DataType.DATE`, `DataType.TEXT`, `DataType.URL`).
   - Converts variable categorical statistics (top codes and frequencies) into Croissant `RecordSet` classification tables.
3. **DDI-Codebook 2.5 (`socrata.py`)**:
   - Generates DDI 2.5 XML documentation (`codeBook`, `docDscr`, `stdyDscr`, `fileDscr`, `dataDscr`).
   - Translates column summary statistics (`sumStat` count, min, max, cardinality, valid, invalid) and code frequencies (`catgry`).
4. **Code Generation (`templates/`)**:
   - Jinja2 templates render client code using official libraries (`sodapy`, `RSocrata`, `soda-ruby`, etc.).
