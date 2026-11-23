# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-11-23

### Added
- Rich interactive CLI (`dartfx-socrata`, `socrata`) built with Typer and Rich (`servers`/`list`, `info`, `search`/`catalog`, `dataset`/`show`/`inspect`, `variables`/`columns`, `metadata`, `export`, `code`/`codegen`, `version`), displaying `--help` automatically when invoked without arguments.
- Community-maintained Socrata portals registry (`data/servers.yaml`, bundled as package data) with 62 verified worldwide portals, custodian ROR identifiers, GeoNames coverage, and domain tags (`load_bundled_servers_yaml()`, `get_known_servers()`).
- CDIF metadata export via `dartfx-cdif` (`CdifGenerator`, `SocrataDataset.get_cdif()`), supporting **CDIF Discovery** (`cdif-discovery` / `cdif`) and **CDIF Data Description** (`cdif-data-description`) profiles, plus `cdif-discovery` output in `search`.
- Multi-profile DCAT support (`us`, `w3c`, `ap`, `ap-hvd`) in `DcatGenerator` and `--flavor` CLI option (`json`, `json-ld`, `ttl`, `xml`, `n3`) for metadata serialization.
- Dedicated `export` command for dataset data records (CSV/JSON) with SoQL query options (`--limit`, `--where`, `--select`, `--order`).
- Crosswalk documentation (`docs/source/cdif.md`), technical architecture guide (`IMPLEMENTATION.md`), and expanded test suites (`tests/test_cli.py`, `tests/test_cdif.py`).

### Changed
- Made `metadata` the canonical command for metadata export with the native Socrata JSON format (`socrata`) as default; reserved `export` for data records.
- Replaced hardcoded `SERVERS` constant with dynamic loading from `data/servers.yaml` (preserving `SERVERS` for backward compatibility).
- Replaced `mypy` with `pyrefly` for static type checking across source, tests, pre-commit, and CI workflows.

### Fixed
- Resolved `pyrefly` type-checking errors and warnings across `cdif.py`, `cli.py`, `dcat.py`, and `socrata.py`, and added `types-PyYAML` dev dependency.
- Normalized ANSI color codes in CLI help tests for reliable execution in CI environments.
- Updated `.pre-commit-config.yaml` fixture exclusions and executable permissions on `scripts/precommit_uv_run.sh`.

## [0.0.1] - 2026-11-23

### Added
- CDIF metadata export via `dartfx-cdif` (`CdifGenerator` and `SocrataDataset.get_cdif()`), supporting both **CDIF Discovery** (`cdif-discovery` / `cdif`) and **CDIF Data Description** (`cdif-data-description`) profiles.
- `--flavor` CLI option (`json`, `json-ld`, `ttl`, `xml`, `n3`) for multi-serialization metadata outputs (`metadata` and `search`).
- `cdif-discovery` output format in `socrata search --format`.
- Comprehensive Socrata-to-CDIF crosswalk documentation (`docs/source/cdif.md`) and unit/CLI tests (`tests/test_cdif.py`).
- Rich interactive Command-Line Interface (`dartfx-socrata`, `socrata`) built with Typer and Rich.
- `servers` (`list`): Command to list and filter known worldwide Socrata open data portals.
- `info`: Command to inspect portal status, metadata, and probe catalog dataset volume.
- `search` (`catalog`): Command to query the Socrata Discovery API with free-text keyword search, domain categories, sorting, and pagination.
- `dataset` (`show`, `inspect`): Command to display dataset metadata overview, licensing, URLs, and column summaries.
- `variables` (`columns`): Command to inspect detailed variable schema, data types, render types, cardinality, and top value distributions.
- `export` (`metadata`): Command to export dataset metadata to W3C DCAT (Turtle, JSON-LD, XML, N-Triples), ML Croissant, DDI-Codebook 2.5, Markdown, or JSON.
- `code` (`codegen`): Command to generate client access scripts in Python (pandas/sodapy), R (RSocrata), Stata, SAS, Ruby, .NET, PowerShell, and jQuery.
- Multi-format output support (`table`, `json`, `csv`, `markdown`) and file export (`--output / -o`).
- Comprehensive CLI test suite (`tests/test_cli.py`) with 33 test cases.
- Dedicated `IMPLEMENTATION.md` detailing technical architecture.
- Package entry points in `pyproject.toml` for `dartfx-socrata` and `socrata`.
