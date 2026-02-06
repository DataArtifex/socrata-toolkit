Data Artifex Socrata Toolkit
============================

Welcome to the **Socrata Toolkit** documentation! This Python library provides comprehensive tools for working with Socrata open data platforms, enabling you to access datasets, generate rich metadata, and create standardized documentation.

Overview
--------

Socrata is an open data platform designed to help government agencies and organizations publish, manage, and share data effectively. It is used by a wide range of government agencies and organizations worldwide to manage and share open data. 

The Socrata Open Data Catalog, also known as the Open Data Network, is a global search engine and discovery tool for open datasets. Socrata offers a comprehensive API called the `Socrata Open Data API (SODA) <https://dev.socrata.com/>`_ for accessing and interacting with datasets hosted on Socrata-powered open data portals.

**Note:** The Socrata platform was acquired by Tyler Technologies for $150 million, about triple the amount of investor funding Socrata had raised since its launch in 2007.

Key Features
------------

The Socrata Toolkit provides:

* **Dataset Access**: Retrieve dataset information, metadata, and statistics from Socrata servers
* **DCAT Generation**: Generate W3C DCAT (Data Catalog Vocabulary) metadata using Pydantic-based RDF models
* **DDI-Codebook**: Create DDI-Codebook 2.5 XML documentation for datasets
* **Croissant Metadata**: Generate ML Croissant format metadata for machine learning datasets
* **Code Generation**: Generate data access code in multiple languages (Python, Ruby, SAS, Stata, PowerShell, jQuery, .NET)
* **Type Safety**: Built on Pydantic models with full type checking and validation

Recent Updates
--------------

**Pydantic RDF Integration (February 2026)**: The DCAT generator has been refactored to use Pydantic-based RDF models from ``dartfx-rdf``, providing:

* Enhanced type safety and validation
* Cleaner, more maintainable code
* Automatic RDF serialization via ``RdfBaseModel``
* Seamless integration with the DataArtifex RDF ecosystem

Quick Start
-----------

Installation
~~~~~~~~~~~~

**Using uv (recommended):**

.. code-block:: bash

   uv pip install dartfx-socrata

**Using pip:**

.. code-block:: bash

   pip install dartfx-socrata

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from dartfx.socrata import SocrataServer, SocrataDataset, DcatGenerator

   # Connect to a Socrata server
   server = SocrataServer(host="data.sfgov.org")

   # Access a specific dataset
   dataset = SocrataDataset(server=server, id="vw6y-z8j6")

   # Get dataset information
   print(f"Dataset: {dataset.name}")
   print(f"Records: {dataset.get_record_count()}")

   # Generate DCAT metadata
   generator = DcatGenerator(server=server)
   generator.add_dataset(dataset)
   graph = generator.get_graph()

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   installation
   quickstart
   metadata
   dcat

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/socrata
   api/dcat
   api/models

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources:

   examples
   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
