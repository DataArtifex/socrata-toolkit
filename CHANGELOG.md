# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-11-23

### Added
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
