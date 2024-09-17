Socrata Metadata
================

The API provides access to metadata on its resources. 

Dataset
-------

Dataset metadata can be found at <host/api/views/<id>.json

Examples:

* `San Francisco 311 Calls  <https://data.sfgov.org/api/views/vw6y-z8j6.json>`_
* `Calgary waste and recycle collection schedule <https://data.calgary.ca/api/views/jq4t-b745.json>`_

.. list-table:: DCAT Dataset / Socrata Dataset Mappings
    :widths: 25 75
    :header-rows: 1

    * - Topic
      - Properties
    * - Identification
      - `id`, `name`, `description` (contains HTML), `tableId`, `oid`
    * - Admin
      - `attribution`, `grants` (object), `license`, `license.name`, `license.termsLink`, `licenseId`, `approvals` (see object), `owner` (object), `tableAuthor` (object)
    * - Classifiers
      - `assetType` (dataset is what we support), `displayType` (table), `category`, `provenance` (official), `tags`, `viewType` (tabular)
    * - Metadata
      - | The `metadata` property holds several properties of interests
        | `customFields` (object), `rdfSubject` & `rdfClass`, `availableDisplayTypes`, `renderTypeConfig`
    * - Statistics
      - `averageRating`, `downloadCount`, `numberOfComments`, `totalTimesRated`, `viewCount`
    * - System
      - `hideFromCatalog`, `hideFromDataJson`, `locale`, `locked`, `newBackend`, `publicationAppendEnabled`, `publicationGroup`, `publicationStage` (published), `rowClass`, `rowsUpdatedBy`, `flags`
    * - Time
      - `createdAt`, `publicationDate`, `rowsUpdatedAt`, `viewLastModified`
    * - Variables
      - |  The `columns` property holds information of the variables. 
        |  Each entry holds a `cachedContent` property with descriptive statistics, including frquencies for the top 10 most used values.





