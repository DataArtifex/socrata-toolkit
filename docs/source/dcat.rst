DCAT Metadata Generation
========================

The Socrata Toolkit provides comprehensive support for generating W3C DCAT (Data Catalog Vocabulary) metadata from Socrata datasets using modern Pydantic-based RDF models.

Overview
--------

Socrata does not natively support DCAT metadata export. This toolkit bridges that gap by mapping Socrata dataset metadata to DCAT vocabulary, enabling interoperability with other data catalog systems and semantic web applications.

**Key Update (February 2026)**: The DCAT generator has been refactored to use Pydantic-based RDF models from ``dartfx-rdf``, providing enhanced type safety, validation, and maintainability.

Architecture
------------

Pydantic-Based Models
~~~~~~~~~~~~~~~~~~~~~

The DCAT generator uses Pydantic models that inherit from ``RdfBaseModel``:

.. code-block:: python

   from dartfx.rdf.pydantic import RdfBaseModel, RdfProperty
   from rdflib import DCAT, DCTERMS
   from typing import Annotated, Optional, List, ClassVar

   class Dataset(RdfBaseModel):
       rdf_type: ClassVar[str] = str(DCAT.Dataset)
       
       id: str
       title: Annotated[Optional[List[str]], RdfProperty(DCTERMS.title)] = None
       description: Annotated[Optional[List[str]], RdfProperty(DCTERMS.description)] = None
       keyword: Annotated[Optional[List[str]], RdfProperty(DCAT.keyword)] = None
       landing_page: Annotated[Optional[List[URIRef]], RdfProperty(DCAT.landingPage)] = None
       # ... additional fields

This approach provides:

* **Type Safety**: Full Pydantic validation of field values
* **RDF Mapping**: Automatic serialization to RDF graphs via ``RdfProperty`` annotations
* **Maintainability**: Clear, declarative model definitions

DCAT Resources
~~~~~~~~~~~~~~~

The toolkit generates the following DCAT resources:

* **dcat:Catalog** - Represents the Socrata server/portal
* **dcat:Dataset** - Represents individual Socrata datasets
* **dcat:Distribution** - Represents data distributions (CSV downloads)
* **dcat:DataService** - Represents the Socrata API endpoints

Usage
-----

Basic DCAT Generation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dartfx.socrata import SocrataServer, SocrataDataset, DcatGenerator

   # Connect to server
   server = SocrataServer(host="data.sfgov.org")
   
   # Create generator
   generator = DcatGenerator(server=server)
   
   # Add datasets
   dataset = SocrataDataset(server=server, id="vw6y-z8j6")
   generator.add_dataset(dataset)
   
   # Generate RDF graph
   graph = generator.get_graph()
   
   # Serialize to Turtle
   ttl = graph.serialize(format='turtle')
   print(ttl)

Multiple Datasets
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Add multiple datasets to a single catalog
   generator = DcatGenerator(server=server)
   generator.add_datasets([
       "vw6y-z8j6",  # Can use dataset IDs
       SocrataDataset(server=server, id="wg3w-h783")  # Or dataset objects
   ])
   
   graph = generator.get_graph()

Export Formats
~~~~~~~~~~~~~~

The generated RDF graph can be serialized to various formats:

.. code-block:: python

   # Turtle
   graph.serialize(format='turtle', destination='catalog.ttl')
   
   # RDF/XML
   graph.serialize(format='xml', destination='catalog.rdf')
   
   # JSON-LD
   graph.serialize(format='json-ld', destination='catalog.jsonld')
   
   # N-Triples
   graph.serialize(format='nt', destination='catalog.nt')

Socrata to DCAT Mappings
-------------------------

Catalog Mappings
~~~~~~~~~~~~~~~~

.. list-table:: DCAT Catalog ← Socrata Server
    :widths: 30 70
    :header-rows: 1

    * - DCAT Property
      - Socrata Source
    * - ``dcterms:title``
      - Server name (from ``SocrataServer.name``)
    * - ``dcterms:publisher``
      - Server host + configured publishers (``SocrataServer.publisher``)
    * - ``dcterms:spatial``
      - Configured spatial coverage (``SocrataServer.spatial``)
    * - ``dcat:dataset``
      - Links to included datasets
    * - ``dcat:service``
      - Links to API services

Dataset Mappings
~~~~~~~~~~~~~~~~

.. list-table:: DCAT Dataset ← Socrata Dataset
    :widths: 30 70
    :header-rows: 1

    * - DCAT Property
      - Socrata Source
    * - ``dcterms:title``
      - ``name``
    * - ``dcterms:description``
      - ``description`` (contains HTML)
    * - ``dcat:keyword``
      - ``tags`` array
    * - ``dcat:landingPage``
      - Generated from host + ``/d/`` + ``id``
    * - ``dcterms:license``
      - ``license.name``, ``license.termsLink``, or ``licenseId``
    * - ``dcterms:modified``
      - ``rowsUpdatedAt`` (preferred) or ``viewLastModified``
    * - ``dcterms:publisher``
      - Server host + configured publishers
    * - ``dcterms:spatial``
      - Server spatial coverage
    * - ``dcat:distribution``
      - Links to CSV distribution

Distribution Mappings
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: DCAT Distribution ← Socrata Export
    :widths: 30 70
    :header-rows: 1

    * - DCAT Property
      - Socrata Source
    * - ``dcat:downloadURL``
      - Generated CSV download URL (``/resource/{id}.csv``)
    * - ``dcat:mediaType``
      - ``text/csv`` (IANA media type)

DataService Mappings
~~~~~~~~~~~~~~~~~~~~

.. list-table:: DCAT DataService ← Socrata API
    :widths: 30 70
    :header-rows: 1

    * - DCAT Property
      - Socrata Source
    * - ``dcat:endpointURL``
      - Generated API endpoint (``/resource/{id}.json``)
    * - ``dcat:servesDataset``
      - Link to parent dataset
    * - ``dcterms:conformsTo``
      - Socrata Foundry documentation URL
    * - ``dcterms:type``
      - Custom service type URI (``SocrataOpenDataAPI``)

Example Output
--------------

Here's an example of generated DCAT metadata in Turtle format:

.. code-block:: turtle

   @prefix dcat: <http://www.w3.org/ns/dcat#> .
   @prefix dcterms: <http://purl.org/dc/terms/> .
   @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

   <https://data.sfgov.org> a dcat:Catalog ;
       dcterms:publisher "City of San Francisco",
           "https://data.sfgov.org" ;
       dcterms:spatial "San Francisco, California, USA" ;
       dcterms:title "San Francisco Open Data Portal" ;
       dcat:dataset <https://data.sfgov.org/d/vw6y-z8j6> ;
       dcat:service <https://data.sfgov.org/resource/vw6y-z8j6.json> .

   <https://data.sfgov.org/d/vw6y-z8j6> a dcat:Dataset ;
       dcterms:title "311 Cases" ;
       dcterms:description "Dataset contains SF311 cases..." ;
       dcterms:license "PDDL" ;
       dcterms:modified "2026-02-06T04:06:12"^^xsd:dateTime ;
       dcat:keyword "311", "calls", "case" ;
       dcat:landingPage <https://data.sfgov.org/d/vw6y-z8j6> ;
       dcat:distribution <https://data.sfgov.org/resource/vw6y-z8j6.csv> .

   <https://data.sfgov.org/resource/vw6y-z8j6.csv> a dcat:Distribution ;
       dcat:downloadURL <https://data.sfgov.org/resource/vw6y-z8j6.csv> ;
       dcat:mediaType <http://www.iana.org/assignments/media-types/text/csv> .

   <https://data.sfgov.org/resource/vw6y-z8j6.json> a dcat:DataService ;
       dcterms:conformsTo <https://dev.socrata.com/foundry/data.sfgov.org/vw6y-z8j6> ;
       dcat:endpointURL <https://data.sfgov.org/resource/vw6y-z8j6.json> ;
       dcat:servesDataset <https://data.sfgov.org/d/vw6y-z8j6> .

Best Practices
--------------

Server Configuration
~~~~~~~~~~~~~~~~~~~~

Configure server metadata for richer DCAT output:

.. code-block:: python

   server = SocrataServer(
       host="data.sfgov.org",
       name="San Francisco Open Data Portal",
       publisher=["City of San Francisco"],
       spatial=["San Francisco, California, USA", "http://sws.geonames.org/5391959"]
   )

Batch Processing
~~~~~~~~~~~~~~~~

For processing multiple datasets efficiently:

.. code-block:: python

   # Get all dataset IDs from search
   results = server.search_datasets(query="311")
   dataset_ids = [r['resource']['id'] for r in results]
   
   # Generate catalog
   generator = DcatGenerator(server=server)
   generator.add_datasets(dataset_ids)
   graph = generator.get_graph()

Integration with RDF Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The generated graphs are standard ``rdflib.Graph`` objects and can be used with any RDF tools:

.. code-block:: python

   from rdflib import DCAT, DCTERMS
   
   # Query the graph
   for dataset in graph.subjects(predicate=RDF.type, object=DCAT.Dataset):
       title = graph.value(subject=dataset, predicate=DCTERMS.title)
       print(f"Dataset: {title}")
   
   # Merge with other graphs
   other_graph = Graph()
   other_graph.parse("external_catalog.ttl", format="turtle")
   graph += other_graph

See Also
--------

* :doc:`metadata` - Socrata metadata structure
* :doc:`api/dcat` - DCAT API reference
* `W3C DCAT Specification <https://www.w3.org/TR/vocab-dcat-3/>`_
* `dartfx-rdf Documentation <https://github.com/DataArtifex/rdf-toolkit>`_
