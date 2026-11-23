from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal

from markdownify import markdownify
from rdflib import Graph, URIRef

from dartfx.cdif import CdifDataDescriptionDataset, CdifDiscoveryDataset, XsdDataType
from dartfx.cdif.models._base import CdifBaseModel, _compact_curie
from dartfx.cdif.models.common import (
    Action,
    CatalogRecord,
    Category,
    CategoryStatistics,
    CdifInstanceVariable,
    CdifKey,
    ComponentPosition,
    DataCatalog,
    DataDownload,
    DefinedTerm,
    EntryPoint,
    Identifier,
    ObjectReference,
    Organization,
    Place,
    Reference,
    Statistics,
    StatisticsCollection,
    VariableMeasured,
    WebAPI,
)
from dartfx.cdif.namespaces import CDIF_PREFIXES

from .socrata import SocrataDataset, SocrataServer, SocrataVariable

CDIF_DISCOVERY_PROFILE_URI = "https://w3id.org/cdif/discovery/1.1"
CDIF_DATA_DESCRIPTION_PROFILE_URI = "https://w3id.org/cdif/data_description/1.1"

SOCRATA_DATATYPES_VOCAB = "https://dev.socrata.com/docs/datatypes"

SOCRATA_TO_XSD_TYPE: dict[str, XsdDataType] = {
    "number": XsdDataType.DECIMAL,
    "money": XsdDataType.DECIMAL,
    "percent": XsdDataType.DECIMAL,
    "stars": XsdDataType.DECIMAL,
    "calendar_date": XsdDataType.DATE_TIME,
    "date": XsdDataType.DATE,
    "checkbox": XsdDataType.BOOLEAN,
    "boolean": XsdDataType.BOOLEAN,
    "flag": XsdDataType.BOOLEAN,
    "url": XsdDataType.ANY_URI,
    "text": XsdDataType.STRING,
    "point": XsdDataType.STRING,
    "location": XsdDataType.STRING,
    "polygon": XsdDataType.STRING,
    "line": XsdDataType.STRING,
    "multipolygon": XsdDataType.STRING,
    "multipoint": XsdDataType.STRING,
    "multiline": XsdDataType.STRING,
    "phone": XsdDataType.STRING,
    "email": XsdDataType.STRING,
    "html": XsdDataType.STRING,
    "document": XsdDataType.STRING,
    "photo": XsdDataType.STRING,
}

_FLAVOR_MAP: dict[str, tuple[str, str]] = {
    "json": ("json", "json"),
    "json-ld": ("json-ld", "jsonld"),
    "jsonld": ("json-ld", "jsonld"),
    "ttl": ("turtle", "ttl"),
    "turtle": ("turtle", "ttl"),
    "xml": ("pretty-xml", "xml"),
    "rdf": ("pretty-xml", "xml"),
    "pretty-xml": ("pretty-xml", "xml"),
    "n3": ("n3", "n3"),
    "nt": ("nt", "nt"),
}


def resolve_serialization_flavor(flavor: str | None, default: str = "json-ld") -> tuple[str, str]:
    """Normalize a CLI/API serialization flavor into ``(target_format, file_extension)``.

    Args:
        flavor: Requested serialization flavor (e.g. ``'json'``, ``'json-ld'``, ``'ttl'``, ``'xml'``, ``'n3'``).
        default: Default flavor when ``flavor`` is ``None``.

    Returns:
        Tuple of ``(target_format, file_extension)``.
    """
    key = (flavor or default).strip().lower()
    if key not in _FLAVOR_MAP:
        supported = ", ".join(["json", "json-ld", "ttl", "xml", "n3"])
        raise ValueError(f"Unsupported serialization flavor '{flavor}'. Supported: {supported}")
    return _FLAVOR_MAP[key]


def _typed[M: CdifBaseModel](model: M) -> M:
    """Populate ``rdf_types_jsonld`` from ``model.rdf_type`` so nested JSON-LD blocks emit ``@type``."""
    raw_type = model.rdf_type
    if raw_type is not None and model.rdf_types_jsonld is None:
        if isinstance(raw_type, (list, tuple, set)):
            model.rdf_types_jsonld = [_compact_curie(t) for t in raw_type]
        elif isinstance(raw_type, (str, URIRef)):
            model.rdf_types_jsonld = [_compact_curie(raw_type)]
    return model


def _clean_description(raw: str | None) -> str | None:
    """Convert Socrata HTML descriptions into clean Markdown text."""
    if not raw:
        return None
    cleaned = markdownify(raw).strip()
    return cleaned or None


def _parse_numeric(value: Any) -> int | float | None:
    """Safely parse numeric strings/numbers from Socrata cachedContents."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if "." in text or "e" in text.lower():
                return float(text)
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return None
    return None


def _parse_int(value: Any) -> int | None:
    """Safely parse integer strings/values."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _dedupe_strings(values: Sequence[str | None]) -> list[str]:
    """Deduplicate non-empty strings while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if not item:
            continue
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


class CdifGenerator:
    """Generate CDIF Discovery and Data Description metadata for Socrata datasets."""

    server: SocrataServer
    datasets: list[SocrataDataset]

    def __init__(self, server: SocrataServer, datasets: list[SocrataDataset | str] | None = None):
        """Initialize the CDIF generator.

        Args:
            server: The Socrata server to generate metadata for.
            datasets: Optional list of SocrataDataset instances or dataset ID strings.
        """
        self.server = server
        self.datasets = []
        if datasets:
            self.add_datasets(datasets)

    def add_dataset(self, dataset: SocrataDataset | str) -> None:
        """Add a dataset to the generator."""
        self.add_datasets([dataset])

    def add_datasets(self, datasets: list[SocrataDataset | str]) -> None:
        """Add multiple datasets to the generator."""
        for item in datasets:
            if isinstance(item, SocrataDataset):
                self.datasets.append(item)
            elif isinstance(item, str):
                self.datasets.append(SocrataDataset(server=self.server, id=item))
            else:
                raise ValueError(f"Unexpected dataset type: {type(item)}")

    def _build_publisher_org(self, host: str | None = None) -> Organization:
        """Build the publisher/provider schema:Organization from portal registry metadata."""
        target_host = host or self.server.host
        if target_host == self.server.host and self.server.custodian:
            custodian = self.server.custodian
            name = str(custodian.get("name") or self.server.name or target_host)
            ror = custodian.get("ror")
            url = custodian.get("url")
            identifier = f"https://ror.org/{ror}" if ror else None
            return _typed(
                Organization(
                    id=identifier or (str(url) if url else f"https://{target_host}"),
                    name=name,
                    identifier=identifier,
                    same_as=str(url) if url else None,
                )
            )
        if target_host == self.server.host and self.server.publisher:
            pub_name = self.server.publisher[0]
            return _typed(
                Organization(
                    id=f"https://{target_host}",
                    name=pub_name,
                    same_as=f"https://{target_host}",
                )
            )
        return _typed(
            Organization(
                id=f"https://{target_host}",
                name=target_host,
                same_as=f"https://{target_host}",
            )
        )

    def _build_spatial_coverage(self) -> list[Place] | None:
        """Build schema:spatialCoverage Place entries from server geocoverage metadata."""
        geocov = self.server.geocoverage
        if not geocov:
            if self.server.spatial:
                return [_typed(Place(name=self.server.spatial[0]))]
            return None
        description = geocov.get("description")
        geonames = [str(g) for g in (geocov.get("geonames") or []) if g]
        if not description and not geonames:
            return None
        place = _typed(
            Place(
                name=str(description) if description else None,
                identifier=geonames if geonames else None,
            )
        )
        return [place]

    def _build_distributions(
        self,
        name: str,
        csv_url: str,
        api_url: str,
        foundry_url: str,
        terms_of_service: str,
    ) -> list[DataDownload | WebAPI]:
        """Build schema:DataDownload (CSV) and schema:WebAPI (SODA JSON API) distributions."""
        download = _typed(
            DataDownload(
                name=f"{name} (CSV)",
                description="Full dataset download in CSV format via Socrata resource endpoint.",
                content_url=csv_url,
                encoding_format=["text/csv"],
            )
        )
        entry_point = _typed(
            EntryPoint(
                name="Socrata Open Data API (SODA) JSON Endpoint",
                url_template=api_url,
                http_method="GET",
                content_type="application/json",
                encoding_format="application/json",
            )
        )
        action = _typed(
            Action(
                name="Query Dataset Records",
                target=entry_point,
            )
        )
        web_api = _typed(
            WebAPI(
                service_type="Socrata Open Data API (SODA)",
                terms_of_service=terms_of_service,
                documentation=foundry_url,
                potential_action=[action],
            )
        )
        return [download, web_api]

    def _build_catalog_record(
        self,
        landing_page: str,
        profile_uri: str,
        date_modified: str,
        host: str | None = None,
    ) -> CatalogRecord:
        """Build the required schema:subjectOf dcat:CatalogRecord declaring CDIF conformance."""
        target_host = host or self.server.host
        catalog_name = self.server.name if target_host == self.server.host and self.server.name else target_host
        catalog_url = f"https://{target_host}"
        data_catalog = _typed(
            DataCatalog(
                id=catalog_url,
                name=catalog_name,
                url=catalog_url,
            )
        )
        return _typed(
            CatalogRecord(
                id=f"{landing_page}#metadata",
                additional_type=[ObjectReference(id="dcat:CatalogRecord")],
                about=ObjectReference(id=landing_page),
                conforms_to=[ObjectReference(id=profile_uri)],
                included_in_data_catalog=[data_catalog],
                sd_date_published=date_modified,
            )
        )

    def _resolve_license_or_access(
        self,
        dataset: SocrataDataset,
    ) -> tuple[list[Reference | ObjectReference | str] | None, str | None, str]:
        """Resolve schema:license or schema:conditionsOfAccess plus WebAPI termsOfService."""
        if dataset.license_link:
            label = dataset.license_name or dataset.license_id or "Dataset License"
            lic_ref: list[Reference | ObjectReference | str] = [_typed(Reference(name=label, url=dataset.license_link))]
            return lic_ref, None, dataset.license_link
        if dataset.license_name or dataset.license_id:
            label = dataset.license_name or dataset.license_id or "Dataset License"
            return [label], None, label

        grants = dataset.data.get("grants")
        is_public = False
        if isinstance(grants, list):
            for grant in grants:
                if isinstance(grant, dict) and "public" in (grant.get("flags") or []):
                    is_public = True
                    break
        if is_public:
            access_note = f"Public read access via {self.server.host_url}; no explicit license specified."
        else:
            access_note = f"Access conditions governed by portal terms at {self.server.host_url}."
        return None, access_note, self.server.host_url

    def _build_keywords(self, dataset: SocrataDataset) -> list[DefinedTerm | str] | None:
        """Combine Socrata tags, category, and server domains into CDIF schema:keywords."""
        items: list[DefinedTerm | str] = []
        seen: set[str] = set()
        if dataset.category:
            seen.add(dataset.category)
            items.append(_typed(DefinedTerm(name=dataset.category)))
        for kw in _dedupe_strings(list(dataset.tags or []) + list(self.server.domains or [])):
            if kw not in seen:
                seen.add(kw)
                items.append(kw)
        return items or None

    def _build_dataset_common_kwargs(
        self,
        dataset: SocrataDataset,
        profile_uri: str,
    ) -> dict[str, Any]:
        """Build common Core + Discovery fields shared by Discovery and Data Description models."""
        dt_modified = dataset.rows_updated_at or dataset.view_last_modified or dataset.created_at
        date_modified = dt_modified.isoformat() if dt_modified else datetime.now(UTC).isoformat()
        date_published = dataset.publication_date.isoformat() if dataset.publication_date else None

        license_val, access_val, tos_val = self._resolve_license_or_access(dataset)
        publisher_org = self._build_publisher_org()
        creator_val: list[Organization] | None = None
        if dataset.attribution:
            creator_val = [
                _typed(
                    Organization(
                        name=dataset.attribution,
                        same_as=dataset.attribution_link,
                    )
                )
            ]

        return {
            "id": dataset.landing_page,
            "name": dataset.name,
            "description": _clean_description(dataset.description),
            "identifier": _typed(
                Identifier(
                    property_id="socrata",
                    value=dataset.id,
                    url=dataset.landing_page,
                )
            ),
            "date_modified": date_modified,
            "date_published": date_published,
            "license": license_val,
            "conditions_of_access": access_val,
            "url": dataset.landing_page,
            "distribution": self._build_distributions(
                name=dataset.name,
                csv_url=dataset.csv_download_url,
                api_url=dataset.api_endpoint_url,
                foundry_url=dataset.api_foundry_url,
                terms_of_service=tos_val,
            ),
            "keywords": self._build_keywords(dataset),
            "creator": creator_val,
            "publisher": [publisher_org],
            "provider": [publisher_org],
            "spatial_coverage": self._build_spatial_coverage(),
            "subject_of": self._build_catalog_record(
                landing_page=dataset.landing_page,
                profile_uri=profile_uri,
                date_modified=date_modified,
            ),
        }

    def build_discovery(
        self,
        dataset: SocrataDataset,
        include_variables: bool = True,
        include_computed: bool = False,
    ) -> CdifDiscoveryDataset:
        """Build a CDIF Discovery profile model (``CdifDiscoveryDataset``) from a SocrataDataset."""
        kwargs = self._build_dataset_common_kwargs(dataset, CDIF_DISCOVERY_PROFILE_URI)
        if include_variables:
            variables = dataset.get_variables(
                exclude_hidden=not include_computed,
                exclude_deleted=True,
                exclude_computed=not include_computed,
            )
            var_models = [
                _typed(
                    VariableMeasured(
                        id=f"{dataset.landing_page}#var-{var.name}",
                        name=var.name,
                        alternate_name=var.label if var.label != var.name else None,
                        description=var.description,
                        property_id=_typed(
                            DefinedTerm(
                                name=var.socrata_data_type,
                                term_code=var.socrata_render_type,
                                in_defined_term_set=SOCRATA_DATATYPES_VOCAB,
                            )
                        ),
                    )
                )
                for var in variables
            ]
            if var_models:
                kwargs["variable_measured"] = var_models

        model = CdifDiscoveryDataset(
            **kwargs,
            jsonld_context=CdifDiscoveryDataset.default_jsonld_context(),
        )
        model.validate_conformance(strict=True)
        return model

    def _build_variable_statistics(
        self,
        var: SocrataVariable,
        include_codes: bool,
        max_codes: int,
    ) -> StatisticsCollection | None:
        """Translate Socrata column cachedContents into CDIF StatisticsCollection."""
        if not var.cached_content:
            return None

        stats_list: list[Statistics] = []
        for stat_name, raw_val in [
            ("count", var.count),
            ("nonNullCount", var.non_null),
            ("nullCount", var.null),
            ("cardinality", var.cardinality),
        ]:
            if raw_val is not None:
                stats_list.append(
                    _typed(
                        Statistics(
                            type_of_statistic=stat_name,
                            statistic=[{"@type": "cdi:Statistic", "cdi:value": raw_val}],
                        )
                    )
                )

        if include_codes and var.top:
            cat_stats: list[CategoryStatistics] = []
            for entry in var.top[:max_codes]:
                item_val = str(entry.get("item", ""))
                freq_val = _parse_int(entry.get("count"))
                stat_payload: dict[str, Any] = {
                    "@type": "cdi:Statistic",
                    "cdi:value": freq_val if freq_val is not None else entry.get("count"),
                }
                cat_stats.append(
                    _typed(
                        CategoryStatistics(
                            for_value=_typed(Category(name=item_val, display_label=item_val)),
                            type_of_statistic="frequency",
                            statistic=[stat_payload],
                        )
                    )
                )
            if cat_stats:
                stats_list.append(
                    _typed(
                        Statistics(
                            type_of_statistic="categoryFrequency",
                            statistic=[{"@type": "cdi:Statistic", "cdi:value": len(cat_stats)}],
                            has_category_statistics=cat_stats,
                        )
                    )
                )

        if not stats_list:
            return None
        return _typed(StatisticsCollection(has_statistics=stats_list))

    def build_data_description(
        self,
        dataset: SocrataDataset,
        include_computed: bool = False,
        include_stats: bool = True,
        include_codes: bool = False,
        max_codes: int = 20,
    ) -> CdifDataDescriptionDataset:
        """Build a CDIF Data Description profile model (``CdifDataDescriptionDataset``)."""
        kwargs = self._build_dataset_common_kwargs(dataset, CDIF_DATA_DESCRIPTION_PROFILE_URI)
        variables = dataset.get_variables(
            exclude_hidden=not include_computed,
            exclude_deleted=True,
            exclude_computed=not include_computed,
        )

        row_id_col = dataset.row_identifier_column_id
        pk_var_uri: str | None = None
        instance_vars: list[CdifInstanceVariable] = []

        for var in variables:
            var_uri = f"{dataset.landing_page}#var-{var.name}"
            is_pk = row_id_col is not None and var.id == row_id_col
            if is_pk:
                pk_var_uri = var_uri

            xsd_type = SOCRATA_TO_XSD_TYPE.get(var.socrata_data_type, XsdDataType.STRING)
            min_val: int | float | None = None
            max_val: int | float | None = None
            if var.socrata_data_type in ("number", "money", "percent", "stars"):
                min_val = _parse_numeric(var.smallest)
                max_val = _parse_numeric(var.largest)

            stats_coll = (
                self._build_variable_statistics(var, include_codes=include_codes, max_codes=max_codes)
                if include_stats
                else None
            )

            instance_vars.append(
                _typed(
                    CdifInstanceVariable(
                        id=var_uri,
                        name=var.name,
                        alternate_name=var.label if var.label != var.name else None,
                        description=var.description,
                        physical_data_type=[xsd_type],
                        property_id=_typed(
                            DefinedTerm(
                                name=var.socrata_data_type,
                                term_code=var.socrata_render_type,
                                in_defined_term_set=SOCRATA_DATATYPES_VOCAB,
                            )
                        ),
                        role="UnitIdentifier" if is_pk else None,
                        min_value=min_val,
                        max_value=max_val,
                        is_described_by_statistics_collection=stats_coll,
                    )
                )
            )

        kwargs["variable_measured"] = instance_vars

        if pk_var_uri:
            kwargs["has_primary_key"] = _typed(
                CdifKey(
                    is_composed_of=[
                        _typed(
                            ComponentPosition(
                                indexes=ObjectReference(id=pk_var_uri),
                                value=1,
                            )
                        )
                    ]
                )
            )

        if include_stats:
            row_count = dataset.get_record_count()
            if row_count is None and dataset.variables:
                row_count = dataset.variables[0].count
            if row_count is not None:
                kwargs["statistics"] = [
                    _typed(
                        Statistics(
                            type_of_statistic="rowCount",
                            statistic=[{"@type": "cdi:Statistic", "cdi:value": row_count}],
                        )
                    )
                ]

        model = CdifDataDescriptionDataset(
            **kwargs,
            jsonld_context=CdifDataDescriptionDataset.default_jsonld_context(),
        )
        model.validate_conformance(strict=True)
        return model

    def build_from_search_result(self, item: dict[str, Any]) -> CdifDiscoveryDataset:
        """Map a single Socrata Discovery API (``/api/catalog/v1``) result item to ``CdifDiscoveryDataset``."""
        res = item.get("resource") or {}
        classification = item.get("classification") or {}
        meta = item.get("metadata") or {}

        ds_id = str(res.get("id") or item.get("id") or "")
        host = str(meta.get("domain") or self.server.host)
        landing_page = str(item.get("permalink") or item.get("link") or f"https://{host}/d/{ds_id}")
        name = str(res.get("name") or res.get("title") or ds_id)
        description = _clean_description(res.get("description"))

        date_modified = str(
            res.get("updatedAt")
            or res.get("data_updated_at")
            or res.get("metadata_updated_at")
            or res.get("createdAt")
            or datetime.now(UTC).isoformat()
        )
        date_published = str(res["createdAt"]) if res.get("createdAt") else None

        raw_license = meta.get("license") or res.get("license")
        license_val: list[Reference | ObjectReference | str] | None = None
        access_val: str | None = None
        if isinstance(raw_license, str) and raw_license.strip():
            license_val = [raw_license.strip()]
            tos_val = raw_license.strip()
        else:
            access_val = f"Access conditions governed by portal terms at https://{host}."
            tos_val = f"https://{host}"

        # Keywords from classification tags & categories
        kw_items: list[DefinedTerm | str] = []
        seen_kw: set[str] = set()
        domain_cat = classification.get("domain_category")
        if isinstance(domain_cat, str) and domain_cat.strip():
            seen_kw.add(domain_cat.strip())
            kw_items.append(_typed(DefinedTerm(name=domain_cat.strip())))
        raw_tags = (
            list(classification.get("domain_tags") or [])
            + list(classification.get("tags") or [])
            + list(classification.get("categories") or [])
        )
        for tag in _dedupe_strings([str(t) for t in raw_tags if t]):
            if tag not in seen_kw:
                seen_kw.add(tag)
                kw_items.append(tag)

        # Lightweight VariableMeasured when Discovery API provides column arrays
        col_fields = res.get("columns_field_name") or []
        col_names = res.get("columns_name") or []
        col_types = res.get("columns_datatype") or []
        col_descs = res.get("columns_description") or []
        var_models: list[VariableMeasured] = []
        for idx, field_name in enumerate(col_fields):
            if not field_name or str(field_name).startswith(":@computed"):
                continue
            label = str(col_names[idx]) if idx < len(col_names) and col_names[idx] else None
            desc = str(col_descs[idx]) if idx < len(col_descs) and col_descs[idx] else None
            dtype = str(col_types[idx]) if idx < len(col_types) and col_types[idx] else None
            var_models.append(
                _typed(
                    VariableMeasured(
                        id=f"{landing_page}#var-{field_name}",
                        name=str(field_name),
                        alternate_name=label if label != str(field_name) else None,
                        description=desc,
                        property_id=(
                            _typed(DefinedTerm(name=dtype, in_defined_term_set=SOCRATA_DATATYPES_VOCAB))
                            if dtype
                            else None
                        ),
                    )
                )
            )

        publisher_org = self._build_publisher_org(host=host)
        spatial_cov = self._build_spatial_coverage() if host == self.server.host else None

        csv_url = f"https://{host}/resource/{ds_id}.csv"
        api_url = f"https://{host}/resource/{ds_id}.json"
        foundry_url = f"https://dev.socrata.com/foundry/{host}/{ds_id}"

        model = CdifDiscoveryDataset(
            id=landing_page,
            name=name,
            description=description,
            identifier=_typed(Identifier(property_id="socrata", value=ds_id, url=landing_page)),
            date_modified=date_modified,
            date_published=date_published,
            license=license_val,
            conditions_of_access=access_val,
            url=landing_page,
            distribution=self._build_distributions(
                name=name,
                csv_url=csv_url,
                api_url=api_url,
                foundry_url=foundry_url,
                terms_of_service=tos_val,
            ),
            keywords=kw_items or None,
            publisher=[publisher_org],
            provider=[publisher_org],
            spatial_coverage=spatial_cov,
            variable_measured=var_models or None,
            subject_of=self._build_catalog_record(
                landing_page=landing_page,
                profile_uri=CDIF_DISCOVERY_PROFILE_URI,
                date_modified=date_modified,
                host=host,
            ),
            jsonld_context=CdifDiscoveryDataset.default_jsonld_context(),
        )
        model.validate_conformance(strict=True)
        return model

    def build_from_search_results(self, results_data: dict[str, Any]) -> list[CdifDiscoveryDataset]:
        """Map a Socrata Discovery API response dictionary into a list of ``CdifDiscoveryDataset`` models."""
        results = results_data.get("results") or []
        return [self.build_from_search_result(item) for item in results]

    def get_models(
        self,
        profile: Literal["discovery", "data_description"] | str = "discovery",
        include_computed: bool = False,
        include_stats: bool = True,
        include_codes: bool = False,
        max_codes: int = 20,
    ) -> list[CdifDiscoveryDataset | CdifDataDescriptionDataset]:
        """Generate CDIF models for all registered datasets."""
        normalized = profile.strip().lower().replace("-", "_")
        models: list[CdifDiscoveryDataset | CdifDataDescriptionDataset] = []
        for ds in self.datasets:
            if normalized in ("discovery", "cdif_discovery"):
                models.append(self.build_discovery(ds, include_computed=include_computed))
            elif normalized in ("data_description", "datadescription", "cdif_data_description"):
                models.append(
                    self.build_data_description(
                        ds,
                        include_computed=include_computed,
                        include_stats=include_stats,
                        include_codes=include_codes,
                        max_codes=max_codes,
                    )
                )
            else:
                raise ValueError(f"Unsupported CDIF profile: {profile}")
        return models

    def to_jsonld(
        self,
        models: CdifBaseModel | Sequence[CdifBaseModel],
        indent: int = 2,
    ) -> str:
        """Serialize one or multiple CDIF models to a framed JSON-LD string."""
        if isinstance(models, CdifBaseModel):
            return models.to_jsonld(indent=indent, include_context=True)

        model_list = list(models)
        if len(model_list) == 1:
            return model_list[0].to_jsonld(indent=indent, include_context=True)

        envelope = {
            "@context": CdifDiscoveryDataset.default_jsonld_context(),
            "@graph": [m.to_jsonld_dict(include_context=False) for m in model_list],
        }
        return json.dumps(envelope, indent=indent)

    def to_rdf_graph(self, models: CdifBaseModel | Sequence[CdifBaseModel]) -> Graph:
        """Convert one or multiple CDIF models into a unified ``rdflib.Graph``."""
        graph = Graph()
        for prefix, ns in CDIF_PREFIXES.items():
            graph.bind(prefix, ns, override=True, replace=True)
        jsonld_str = self.to_jsonld(models)
        if jsonld_str:
            graph.parse(data=jsonld_str, format="json-ld")
        for prefix, ns in CDIF_PREFIXES.items():
            graph.bind(prefix, ns, override=True, replace=True)
        return graph

    def serialize(
        self,
        models: CdifBaseModel | Sequence[CdifBaseModel],
        flavor: str = "json-ld",
        indent: int = 2,
    ) -> str:
        """Serialize one or multiple CDIF models using the requested serialization flavor."""
        target_format, _ = resolve_serialization_flavor(flavor, default="json-ld")
        if target_format in ("json", "json-ld"):
            return self.to_jsonld(models, indent=indent)

        graph = self.to_rdf_graph(models)
        raw = graph.serialize(format=target_format)
        return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
