# CDIF Metadata Crosswalk & Export Guide

The **Socrata Toolkit** (`dartfx-socrata`) supports exporting Socrata dataset and catalog search metadata compliant with the **Cross-Domain Interoperability Framework (CDIF)** 2026 specification using `dartfx-cdif` (`CdifDiscoveryDataset` and `CdifDataDescriptionDataset`).

---

## Supported CDIF Profiles

| Profile Format | CLI Flag (`--format`) | Python Class | Canonical Conformance URI | Scope |
| :--- | :--- | :--- | :--- | :--- |
| **CDIF Discovery** | `cdif-discovery` (or `cdif`, `cdif-disco`) | `CdifDiscoveryDataset` | `https://w3id.org/cdif/discovery/1.1` | Core dataset identity, licensing/access, distributions (`DataDownload` & `WebAPI`), portal provenance, spatial coverage, keywords, and lightweight variable descriptors. |
| **CDIF Data Description** | `cdif-data-description` (or `cdif-data`) | `CdifDataDescriptionDataset` | `https://w3id.org/cdif/data_description/1.1` | Extends Discovery with DDI-CDI `cdi:InstanceVariable` definitions, XSD physical data types, numeric bounds, primary keys (`cdif:hasPrimaryKey`), and dataset/variable summary & category statistics. |

---

## Serialization Flavors (`--flavor`)

CDIF and DCAT outputs support multiple RDF and JSON-LD serializations via the `--flavor` CLI option or `CdifGenerator.serialize(..., flavor=...)`:

| Flavor | Target Format | File Extension | Description |
| :--- | :--- | :--- | :--- |
| `json-ld` *(default)* | `json-ld` | `.jsonld` | Framed CDIF JSON-LD with `@context` and `@type` declarations (single object or `@graph` envelope for multiple datasets). |
| `json` | `json` | `.json` | Framed JSON-LD serialized with `.json` extension. |
| `ttl` | `turtle` | `.ttl` | W3C RDF Turtle syntax with canonical CDIF namespace prefixes (`schema:`, `cdif:`, `cdi:`, `dcat:`, `dcterms:`, etc.). |
| `xml` | `pretty-xml` | `.xml` | RDF/XML serialized syntax. |
| `n3` | `n3` | `.n3` | Notation3 (N3) RDF syntax. |

---

## 1. Crosswalk: Socrata View API → CDIF Discovery (`CdifDiscoveryDataset`)

Source: Socrata `/api/views/{id}.json` (`SocrataDataset`) enriched with portal registry metadata (`src/dartfx/socrata/data/servers.yaml` via `SocrataServer`).

### Core & Discovery Dataset Properties

| CDIF Property | Requirement | Socrata Source | Mapping & Fallback Behavior |
| :--- | :--- | :--- | :--- |
| `@id` | **Required** | `dataset.landing_page` | Canonical landing page URL: `https://{host}/d/{id}`. |
| `@type` | **Required** | Fixed | `["schema:Dataset"]` (automatically emitted). |
| `@context` | **Required** | `CdifDiscoveryDataset.default_jsonld_context()` | Canonical CDIF 2026 prefix bindings (`schema`, `dcterms`, `prov`, `dqv`, `geosparql`, `spdx`, `time`, `sf`, `cdi`, `cdif`, `csvw`, `dcat`, `skos`, `bios`). |
| `schema:name` | **Required** | `view.name` | Dataset title (falls back to `view.id` if missing). |
| `schema:identifier` | **Required** | `view.id`, `dataset.landing_page` | `schema:PropertyValue` (`Identifier`) with `schema:propertyID="socrata"`, `schema:value="{id}"`, `schema:url="{landing_page}"`. |
| `schema:dateModified` | **Required** | `view.rowsUpdatedAt` → `view.viewLastModified` → `view.createdAt` | ISO-8601 timestamp using the first available timestamp (or current UTC time if none present). |
| `schema:datePublished` | Optional | `view.publicationDate` | ISO-8601 timestamp when published. |
| `schema:description` | Recommended | `view.description` | HTML converted to clean Markdown via `markdownify`. |
| `schema:license` / `schema:conditionsOfAccess` | **AnyOf Required (1)** | `view.license.name`, `view.license.termsLink`, `view.licenseId`, `view.grants` | If `license.termsLink` exists → `schema:license` as `schema:CreativeWork` (`Reference`) with `schema:name` and `schema:url`. Else if `license.name` or `licenseId` exists → `schema:license` string. If no license is declared → `schema:conditionsOfAccess` generated from `view.grants` (public read vs portal terms). |
| `schema:url` / `schema:distribution` | **AnyOf Required (2)** | `dataset.landing_page`, `csv_download_url`, `api_endpoint_url`, `api_foundry_url` | Both populated: `schema:url` = landing page, and `schema:distribution` contains both a `schema:DataDownload` (CSV) and a `schema:WebAPI` (SODA JSON API). |
| `schema:keywords` | Recommended | `view.category`, `view.tags`, `server.domains` | `view.category` mapped as `schema:DefinedTerm`, merged and deduplicated with `view.tags` and `server.domains` strings. |
| `schema:creator` | Optional | `view.attribution`, `view.attributionLink` | `schema:Organization` with `schema:name=attribution` and `schema:sameAs=attributionLink` (when present). |
| `schema:publisher` & `schema:provider` | Recommended | `server.custodian` / `server.publisher` | `schema:Organization` built from `servers.yaml` `custodian` (`name`, `url`, and `https://ror.org/{ror}` when available), falling back to `server.host`. |
| `schema:spatialCoverage` | Discovery Ext. | `server.geocoverage` | `schema:Place` with `schema:name=geocoverage.description` and `schema:identifier=geocoverage.geonames` URIs. |
| `schema:variableMeasured` | Discovery Ext. | `view.columns[]` (excluding hidden/deleted) | Lightweight `schema:PropertyValue` (`VariableMeasured`) objects carrying `schema:name`, `schema:alternateName`, `schema:description`, and `schema:propertyID` (`DefinedTerm` referencing `https://dev.socrata.com/docs/datatypes`). |
| `schema:subjectOf` | **Required** | Generated `CatalogRecord` | Typed `schema:Dataset` with `schema:additionalType` = `dcat:CatalogRecord`, `@id="{landing_page}#metadata"`, `schema:about` = `{landing_page}`, `dcterms:conformsTo` = profile URI, `schema:sdDatePublished` = `dateModified`, and `schema:includedInDataCatalog` = portal `schema:DataCatalog`. |

### Distribution Sub-Objects

| CDIF Class | CDIF Property | Socrata Source |
| :--- | :--- | :--- |
| `schema:DataDownload` | `schema:contentUrl` | `https://{host}/resource/{id}.csv` |
| `schema:DataDownload` | `schema:encodingFormat` | `["text/csv"]` |
| `schema:WebAPI` | `schema:serviceType` | `"Socrata Open Data API (SODA)"` |
| `schema:WebAPI` | `schema:termsOfService` | Resolved `license.termsLink`, license string, or portal URL |
| `schema:WebAPI` | `schema:documentation` | `https://dev.socrata.com/foundry/{host}/{id}` |
| `schema:WebAPI` | `schema:potentialAction` (`schema:Action`) | `schema:EntryPoint` with `schema:urlTemplate="https://{host}/resource/{id}.json"`, `schema:httpMethod="GET"`, `schema:contentType="application/json"` |

---

## 2. Crosswalk: Socrata Schema → CDIF Data Description (`CdifDataDescriptionDataset`)

In addition to all Discovery properties above (with `dcterms:conformsTo` set to `https://w3id.org/cdif/data_description/1.1`), the Data Description profile maps Socrata column definitions (`columns[]`), row identifiers (`rowIdentifierColumnId`), and cached column statistics (`cachedContents`) to DDI-CDI structures:

### Dataset-Level Data Description Properties

| CDIF Property | Requirement | Socrata Source | Mapping |
| :--- | :--- | :--- | :--- |
| `schema:variableMeasured` | **Required** | `view.columns[]` (filtered by visibility) | List of `CdifInstanceVariable` (`cdi:InstanceVariable`) objects. |
| `cdif:hasPrimaryKey` | Optional | `view.rowIdentifierColumnId` (or `metadata.rowIdentifier`) | `cdif:Key` with `cdif:isComposedOf` containing `cdi:ComponentPosition(cdi:indexes={"@id": var_uri}, cdi:value=1)` when the row identifier matches an included column. |
| `cdif:statistics` | Optional | `dataset.get_record_count()` (`columns[0].cachedContents.count`) | Dataset-level `cdi:Statistics` (`cdif:typeOfStatistic="rowCount"`) when `--include-stats` is enabled. |

### Variable-Level Properties (`CdifInstanceVariable` / `cdi:InstanceVariable`)

| CDIF Property | Socrata Column Source | Mapping |
| :--- | :--- | :--- |
| `@id` | `column.fieldName` | `https://{host}/d/{id}#var-{fieldName}` |
| `@type` | Fixed | `["cdi:InstanceVariable"]` |
| `schema:name` | `column.fieldName` | Machine-readable column name (`SocrataVariable.name`). |
| `schema:alternateName` | `column.name` | Human-readable display label (`SocrataVariable.label`, omitted if identical to `fieldName`). |
| `schema:description` | `column.description` | Column description text. |
| `cdif:physicalDataType` | `column.dataTypeName` | Mapped to canonical `XsdDataType` CURIE (see data type table below). |
| `schema:propertyID` | `column.dataTypeName`, `column.renderTypeName` | `schema:DefinedTerm` (`name=dataTypeName`, `termCode=renderTypeName`, `inDefinedTermSet="https://dev.socrata.com/docs/datatypes"`). |
| `cdif:role` | `view.rowIdentifierColumnId == column.id` | `"UnitIdentifier"` when the column is the dataset row identifier. |
| `schema:minValue` / `schema:maxValue` | `cachedContents.smallest` / `cachedContents.largest` | Numeric `int`/`float` bounds for numeric column types (`number`, `money`, `percent`, `stars`). |
| `cdif:isDescribedBy_StatisticsCollection` | `cachedContents` (`count`, `non_null`, `null`, `cardinality`, `top`) | `cdi:StatisticsCollection` containing `cdi:Statistics` bundles for `count`, `nonNullCount`, `nullCount`, `cardinality`, and optional `categoryFrequency` (`cdi:CategoryStatistics` from `top[]` when `--include-codes` is enabled). |

### Socrata Data Type → XSD Physical Data Type (`cdif:physicalDataType`)

| Socrata `dataTypeName` | `XsdDataType` CURIE |
| :--- | :--- |
| `number`, `money`, `percent`, `stars` | `xsd:decimal` |
| `calendar_date` | `xsd:dateTime` |
| `date` | `xsd:date` |
| `checkbox`, `boolean`, `flag` | `xsd:boolean` |
| `url` | `xsd:anyURI` |
| `text`, `point`, `location`, `polygon`, `line`, `multipolygon`, `multipoint`, `multiline`, `phone`, `email`, `html`, `document`, `photo`, *(other)* | `xsd:string` |

---

## 3. Crosswalk: Socrata Discovery API (`/api/catalog/v1`) → CDIF Discovery (`socrata search`)

When running `socrata search --format cdif-discovery`, each search hit returned by `/api/catalog/v1` is mapped directly without extra HTTP calls:

| CDIF Property | Socrata Search API Field |
| :--- | :--- |
| `@id` / `schema:url` | `permalink` or `link` or `https://{metadata.domain}/d/{resource.id}` |
| `schema:name` | `resource.name` or `resource.title` |
| `schema:description` | `resource.description` (markdownified) |
| `schema:identifier` | `Identifier(property_id="socrata", value=resource.id, url=landing_page)` |
| `schema:dateModified` | `resource.updatedAt` → `resource.data_updated_at` → `resource.createdAt` |
| `schema:datePublished` | `resource.createdAt` |
| `schema:license` / `schema:conditionsOfAccess` | `metadata.license` / `resource.license`, or fallback portal access statement |
| `schema:keywords` | `classification.domain_category` (`DefinedTerm`) + `domain_tags` + `tags` + `categories` |
| `schema:variableMeasured` | Constructed from `resource.columns_field_name[]`, `columns_name[]`, `columns_datatype[]`, `columns_description[]` when provided by the catalog response |
| `schema:publisher` / `schema:spatialCoverage` | Resolved from `SocrataServer` portal registry when `metadata.domain` matches `server.host` |

---

## Usage Examples

### Command-Line Interface (`socrata`)

```bash
# Export CDIF Discovery metadata as framed JSON-LD (default flavor)
socrata metadata vw6y-z8j6 -s data.sfgov.org -f cdif-discovery

# Export CDIF Discovery as Turtle (.ttl) and save to a file
socrata metadata vw6y-z8j6 -s data.sfgov.org -f cdif-discovery --flavor ttl -o vw6y-z8j6.cdif.ttl

# Export CDIF Data Description with variables, physical types, primary key, and statistics
socrata metadata vw6y-z8j6 -s data.sfgov.org -f cdif-data-description --flavor json-ld

# Export CDIF Data Description including top category frequencies, serialized as RDF/XML
socrata metadata vw6y-z8j6 -s data.sfgov.org -f cdif-data-description --include-codes --max-codes 10 --flavor xml

# Export multiple datasets into a single CDIF JSON-LD @graph or unified RDF graph
socrata metadata vw6y-z8j6 wg3w-h783 -s data.sfgov.org -f cdif-discovery --flavor n3

# Search a Socrata catalog and export hits directly as CDIF Discovery
socrata search "311" -s data.sfgov.org --limit 10 -f cdif-discovery --flavor json-ld
```

### Python API

```python
from dartfx.socrata import CdifGenerator, SocrataDataset, SocrataServer

server = SocrataServer(host="data.sfgov.org")
dataset = SocrataDataset(server=server, id="vw6y-z8j6")

# Quick export directly from SocrataDataset
discovery_model = dataset.get_cdif(profile="discovery")
assert discovery_model.validate_conformance() == []
print(discovery_model.to_jsonld())

# Data Description profile with variables, stats, and category frequencies
dd_model = dataset.get_cdif(profile="data_description", include_stats=True, include_codes=True)
assert dd_model.validate_conformance() == []

# Multi-dataset generation and serialization via CdifGenerator
generator = CdifGenerator(server=server, datasets=["vw6y-z8j6", "wg3w-h783"])
models = generator.get_models(profile="discovery")
turtle_str = generator.serialize(models, flavor="ttl")
```
