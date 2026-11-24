# Socrata Toolkit

[![Development Status](https://img.shields.io/badge/status-early%20release-orange.svg)](https://github.com/DataArtifex/socrata-toolkit)
[![Documentation](https://img.shields.io/badge/docs-blue)](https://www.dataartifex.org/socrata-toolkit/)
[![Ask DeepWiki](https://img.shields.io/badge/Ask%20DeepWiki-AI%20Docs-5C54E5)](https://deepwiki.com/DataArtifex/socrata-toolkit)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Package Status](https://img.shields.io/badge/PyPI-not%20published-lightgrey)](https://github.com/DataArtifex/socrata-toolkit)
[![CI](https://github.com/DataArtifex/socrata-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/DataArtifex/socrata-toolkit/actions/workflows/test.yml)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg?logo=ruff&logoColor=D7FF64)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

## Overview

The **Socrata Toolkit** (`dartfx-socrata`) is a Python library for working with Socrata open data platforms. It provides a comprehensive set of tools to interact with Socrata datasets and generate rich metadata in multiple standardized formats.

### Key Features

- **Dataset Access**: Retrieve dataset information, metadata, and statistics from Socrata servers
- **DCAT Generation**: Generate W3C DCAT (Data Catalog Vocabulary) metadata using Pydantic-based RDF models
- **CDIF Export**: Generate Cross-Domain Interoperability Framework (CDIF) Discovery and Data Description metadata in JSON-LD, Turtle, RDF/XML, and N3 formats via `dartfx-cdif`
- **DDI-Codebook**: Create DDI-Codebook 2.5 XML documentation for datasets
- **Croissant Metadata**: Generate ML Croissant format metadata for machine learning datasets
- **Code Generation**: Generate data access code in multiple languages (Python, R, Ruby, SAS, Stata, PowerShell, jQuery, .NET)
- **Type Safety**: Built on Pydantic models with full type checking and validation

### Recent Updates

**Pydantic RDF Integration** (February 2026): The DCAT generator has been refactored to use Pydantic-based RDF models from `dartfx-rdf`, providing:

- Enhanced type safety and validation
- Cleaner, more maintainable code
- Automatic RDF serialization via `RdfBaseModel`
- Seamless integration with the DataArtifex RDF ecosystem

## Installation

### Using uv (Recommended)

Once published to [PyPI](https://pypi.org/), you can add the library to a project or install the CLI globally using [uv](https://github.com/astral-sh/uv):

```bash
# Add to an existing uv project
uv add dartfx-socrata

# Or install the CLI globally
uv tool install dartfx-socrata

# Or install into an environment with uv pip
uv pip install dartfx-socrata
```

### Local Development Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/DataArtifex/socrata-toolkit.git
   cd socrata-toolkit
   ```

2. **Sync Dependencies with uv:**

   ```bash
   uv sync --group dev
   ```

   You can then run the CLI or Python scripts directly with `uv run`:

   ```bash
   uv run dartfx-socrata --help
   ```

> **Why uv?** [uv](https://github.com/astral-sh/uv) is an extremely fast Python package and project manager written in Rust. Install it with: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Dependencies

The toolkit requires Python 3.12+ and depends on:

- `dartfx-cdif` - CDIF Discovery and Data Description models
- `dartfx-dcat` - DCAT vocabulary support
- `dartfx-rdf` - RDF and Pydantic integration
- `pydantic>=2` - Data validation
- `mlcroissant>=1.0.16` - Croissant metadata
- `jinja2>=3` - Code generation templates
- `markdownify>=0.13.0` - Markdown conversion

## Usage

### Basic Dataset Access

```python
from dartfx.socrata import SocrataServer, SocrataDataset

# Connect to a Socrata server
server = SocrataServer(host="data.sfgov.org")

# Access a specific dataset
dataset = SocrataDataset(server=server, id="vw6y-z8j6")

# Get dataset information
print(f"Dataset: {dataset.name}")
print(f"Description: {dataset.description}")
print(f"Records: {dataset.get_record_count()}")
print(f"Variables: {dataset.get_variable_count()}")
```

### Generate DCAT Metadata

```python
from dartfx.socrata import DcatGenerator

# Create DCAT generator
generator = DcatGenerator(server=server)
generator.add_dataset(dataset)

# Generate RDF graph
graph = generator.get_graph()

# Serialize to Turtle format
ttl = graph.serialize(format='turtle')
print(ttl)
```

### Generate CDIF Discovery & Data Description Metadata

```python
from dartfx.socrata import CdifGenerator

# CDIF Discovery profile (default JSON-LD)
discovery = dataset.get_cdif(profile="discovery")
print(discovery.to_jsonld())

# CDIF Data Description profile (variables, XSD types, primary keys, stats)
data_desc = dataset.get_cdif(profile="data_description", include_stats=True)
generator = CdifGenerator(server=server)
print(generator.serialize(data_desc, flavor="ttl"))
```

### Generate DDI-Codebook

```python
# Generate DDI-Codebook XML
xml = dataset.get_ddi_codebook()

# Save to file
with open('codebook.xml', 'w') as f:
    f.write(xml)
```

### Generate Croissant Metadata

```python
# Generate Croissant metadata for ML datasets
metadata = dataset.get_croissant(max_codes=100)

# Export to JSON
import json
with open('dataset.croissant.json', 'w') as f:
    json.dump(metadata.to_json(), f, indent=2)
```

### Generate Access Code

```python
# Generate Python pandas code
code = dataset.get_code("python-pandas")
print(code)

# Supported environments:
# - python-pandas
# - soda-ruby
# - soda-dotnet
# - jquery
# - powershell
# - sas
# - stata
```

## Architecture

### Pydantic-Based DCAT Models

The DCAT generator uses Pydantic models that inherit from `RdfBaseModel`:

```python
from dartfx.rdf.pydantic import RdfBaseModel, RdfProperty
from rdflib import DCAT, DCTERMS

class Dataset(RdfBaseModel):
    rdf_type: ClassVar[str] = str(DCAT.Dataset)

    id: str
    title: Annotated[Optional[List[str]], RdfProperty(DCTERMS.title)] = None
    description: Annotated[Optional[List[str]], RdfProperty(DCTERMS.description)] = None
    # ... additional fields
```

This approach provides:

- **Type Safety**: Full Pydantic validation
- **RDF Mapping**: Automatic serialization to RDF graphs
- **Maintainability**: Clear, declarative model definitions

## Testing

Run the test suite and checks with `uv`:

```bash
uv run pytest tests/
uv run ruff check src tests
uv run pyrefly check src tests
```

Test coverage includes:

- DCAT generation and RDF validation
- DDI-Codebook XML schema validation
- Croissant metadata generation
- Code generation for all supported languages

## Roadmap

- [ ] Publish to PyPI
- [ ] Add support for DCAT-AP profiles
- [ ] Expand code generation templates
- [ ] Add data quality metrics
- [ ] Support for Socrata data transformations
- [ ] Integration with additional metadata standards

## Contributing

We welcome contributions! Please review our [Governance](GOVERNANCE.md) document to understand the project's decision-making process and contribution guidelines.

Here's how to get started:

1. Fork the repository
2. Create your feature branch: `git checkout -b my-new-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `uv run pytest tests/`
5. Commit your changes: `git commit -am 'Add some feature'`
6. Push to the branch: `git push origin my-new-feature`
7. Submit a pull request

Please ensure your code follows the existing style and includes appropriate tests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- Built on the [Socrata Open Data API](https://dev.socrata.com/)
- Part of the [DataArtifex](https://github.com/DataArtifex) ecosystem
- Uses [Pydantic](https://pydantic.dev/) for data validation
- Integrates with [RDFLib](https://rdflib.readthedocs.io/) for RDF operations
