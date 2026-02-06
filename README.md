# Socrata Toolkit

[![PyPI - Version](https://img.shields.io/pypi/v/dartfx-socrata.svg)](https://pypi.org/project/dartfx-socrata)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/dartfx-socrata.svg)](https://pypi.org/project/dartfx-socrata)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)

**This project is in its early development stages, so stability is not guaranteed, and documentation is limited. We welcome your feedback and contributions as we refine and expand this project together!**

## Overview

The **Socrata Toolkit** (`dartfx-socrata`) is a Python library for working with Socrata open data platforms. It provides a comprehensive set of tools to interact with Socrata datasets and generate rich metadata in multiple standardized formats.

### Key Features

- **Dataset Access**: Retrieve dataset information, metadata, and statistics from Socrata servers
- **DCAT Generation**: Generate W3C DCAT (Data Catalog Vocabulary) metadata using Pydantic-based RDF models
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

### PyPI Release

Once stable, this package will be officially released and distributed through [PyPI](https://pypi.org/).

**Using uv (recommended):**

```bash
uv pip install dartfx-socrata
```

**Using pip:**

```bash
pip install dartfx-socrata
```

### Local Installation

For development or early access, install the package locally:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/DataArtifex/socrata-toolkit.git
   cd socrata-toolkit
   ```

2. **Install the Package:**

   **Using uv (recommended):**
   
   ```bash
   uv pip install -e .
   ```
   
   **Using pip:**
   
   ```bash
   pip install -e .
   ```

> **Why uv?** [uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver written in Rust. It's significantly faster than pip and provides better dependency resolution. Install uv with: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Dependencies

The toolkit requires Python 3.10+ and depends on:
- `dartfx-rdf` - RDF and Pydantic integration
- `dartfx-dcat` - DCAT vocabulary support
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

Run the test suite:

```bash
pytest tests/
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
4. Ensure all tests pass: `pytest tests/`
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
