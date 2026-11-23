from __future__ import annotations

from enum import StrEnum
from typing import Any

from rdflib import Graph, Namespace, URIRef

from dartfx.dcat import dcat, dcat_ap, dcat_ap_hvd, dcat_us

from .socrata import SocrataDataset, SocrataServer

# Extra namespaces used in Socrata DCAT
HVDN = Namespace("https://rdf.highvaluedata.net/dcat#")
CATALOG = Namespace("https://catalog.highvaluedata.net/")


class DcatProfile(StrEnum):
    """Supported DCAT application profiles."""

    US = "us"
    W3C = "w3c"
    AP = "ap"
    AP_HVD = "ap-hvd"


_PROFILE_ALIASES: dict[str, DcatProfile] = {
    "us": DcatProfile.US,
    "dcat-us": DcatProfile.US,
    "w3c": DcatProfile.W3C,
    "dcat": DcatProfile.W3C,
    "ap": DcatProfile.AP,
    "dcat-ap": DcatProfile.AP,
    "ap-hvd": DcatProfile.AP_HVD,
    "dcat-ap-hvd": DcatProfile.AP_HVD,
    "hvd": DcatProfile.AP_HVD,
}


def resolve_dcat_profile(profile: DcatProfile | str | None) -> DcatProfile:
    """Normalize a DCAT profile name or alias to ``DcatProfile`` (defaulting to ``us``)."""
    if profile is None:
        return DcatProfile.US
    if isinstance(profile, DcatProfile):
        return profile
    key = profile.strip().lower()
    if key in _PROFILE_ALIASES:
        return _PROFILE_ALIASES[key]
    valid = ", ".join(p.value for p in DcatProfile)
    raise ValueError(f"Unsupported DCAT profile '{profile}'. Supported: {valid}")


class DcatGenerator:
    """Generate DCAT metadata for Socrata datasets using dartfx.dcat Pydantic models.

    Defaults to the DCAT-US 3.0 profile (``us``), and supports W3C DCAT 3 (``w3c``),
    DCAT-AP 3.0.1 (``ap``), and DCAT-AP HVD 3.0.0 (``ap-hvd``).
    """

    server: SocrataServer
    datasets: list[SocrataDataset]
    profile: DcatProfile

    def __init__(
        self,
        server: SocrataServer,
        datasets: list[SocrataDataset | str] | None = None,
        profile: DcatProfile | str = DcatProfile.US,
    ):
        """Initialize the DCAT generator.

        Args:
            server: The Socrata server to generate metadata for.
            datasets: Optional list of datasets to include (can be SocrataDataset instances or ID strings).
            profile: DCAT profile to generate (``us`` [default], ``w3c``, ``ap``, ``ap-hvd``).
        """
        self.server = server
        self.profile = resolve_dcat_profile(profile)
        self.datasets = []
        if datasets:
            self.add_datasets(datasets)

    def add_dataset(self, dataset: SocrataDataset | str) -> None:
        """Add a dataset to the catalog.

        Args:
            dataset: Either a SocrataDataset instance or a dataset ID string
        """
        self.add_datasets([dataset])

    def add_datasets(self, datasets: list[SocrataDataset | str]) -> None:
        """Add multiple datasets to the catalog.

        Args:
            datasets: List of SocrataDataset instances or dataset ID strings
        """
        for item in datasets:
            if isinstance(item, SocrataDataset):
                self.datasets.append(item)
            elif isinstance(item, str):
                self.datasets.append(SocrataDataset(server=self.server, id=item))
            else:
                raise ValueError(f"Unexpected dataset type: {type(item)}")

    @staticmethod
    def _model_classes(profile: DcatProfile) -> tuple[type[Any], type[Any], type[Any], type[Any]]:
        """Return ``(Catalog, Dataset, Distribution, DataService)`` classes for the profile."""
        if profile == DcatProfile.US:
            cat_cls: type[Any] = getattr(dcat_us, "Catalog", dcat.Catalog)
            ds_cls: type[Any] = getattr(dcat_us, "Dataset", dcat.Dataset)
            dist_cls: type[Any] = getattr(dcat_us, "Distribution", dcat.Distribution)
            return cat_cls, ds_cls, dist_cls, dcat.DataService
        if profile == DcatProfile.AP:
            return dcat_ap.Catalog, dcat_ap.Dataset, dcat_ap.Distribution, dcat_ap.DataService
        if profile == DcatProfile.AP_HVD:
            return dcat_ap_hvd.Catalog, dcat_ap_hvd.Dataset, dcat_ap_hvd.Distribution, dcat_ap_hvd.DataService
        return dcat.Catalog, dcat.Dataset, dcat.Distribution, dcat.DataService

    def get_graph(self, profile: DcatProfile | str | None = None) -> Graph:
        """Generate an RDF graph containing DCAT metadata for all datasets.

        Args:
            profile: Optional profile override (``us``, ``w3c``, ``ap``, ``ap-hvd``).

        Returns:
            RDFLib Graph containing the DCAT metadata.
        """
        active_profile = resolve_dcat_profile(profile) if profile is not None else self.profile
        catalog_cls, dataset_cls, distribution_cls, service_cls = self._model_classes(active_profile)

        catalog_uri = f"https://{self.server.host}"
        catalog = catalog_cls(id=catalog_uri)

        if self.server.name:
            catalog.add_title(self.server.name)

        catalog.add_publisher(f"https://{self.server.host}")
        if self.server.publisher:
            for pub in self.server.publisher:
                catalog.add_publisher(pub)

        if self.server.spatial:
            for spatial in self.server.spatial:
                catalog.spatial.append(spatial)

        if active_profile == DcatProfile.AP_HVD:
            catalog.add_applicable_legislation(dcat_ap_hvd.HVD_REGULATION)

        for socrata_ds in self.datasets:
            dataset = dataset_cls(id=socrata_ds.landing_page)

            if socrata_ds.name:
                dataset.add_title(socrata_ds.name)

            if socrata_ds.description:
                dataset.add_description(socrata_ds.description)

            if socrata_ds.tags:
                for tag in socrata_ds.tags:
                    dataset.add_keyword(tag)

            dataset.add_landing_page(URIRef(socrata_ds.landing_page))

            if socrata_ds.license_id:
                dataset.add_license(socrata_ds.license_id)
            if socrata_ds.license_name:
                dataset.add_license(socrata_ds.license_name)
            if socrata_ds.license_link:
                dataset.add_license(socrata_ds.license_link)

            if socrata_ds.rows_updated_at:
                dataset.add_modified_date(socrata_ds.rows_updated_at)
            elif socrata_ds.view_last_modified:
                dataset.add_modified_date(socrata_ds.view_last_modified)

            dataset.add_publisher(f"https://{socrata_ds.server.host}")
            if socrata_ds.server.publisher:
                for pub in socrata_ds.server.publisher:
                    dataset.add_publisher(pub)

            if socrata_ds.server.spatial:
                for spatial in socrata_ds.server.spatial:
                    dataset.spatial.append(spatial)

            # DCAT-US 3.0 accessRestriction from Socrata grants
            if active_profile == DcatProfile.US:
                grants = socrata_ds.data.get("grants")
                if isinstance(grants, list) and any(
                    isinstance(g, dict) and "public" in (g.get("flags") or []) for g in grants
                ):
                    dataset.add_access_restriction(
                        dcat_us.AccessRestriction(
                            id=f"{socrata_ds.landing_page}#access",
                            restrictionStatus="public",
                        )
                    )

            # Create Distribution (CSV download)
            distribution = distribution_cls(id=socrata_ds.csv_download_url)
            distribution.add_download_url(URIRef(socrata_ds.csv_download_url))
            distribution.add_media_type(URIRef("http://www.iana.org/assignments/media-types/text/csv"))

            if active_profile == DcatProfile.AP_HVD:
                distribution.add_access_url(URIRef(socrata_ds.csv_download_url))
                distribution.make_hvd_compliant()
                dataset.add_applicable_legislation(dcat_ap_hvd.HVD_REGULATION)

            dataset.distribution.append(distribution)

            # Create DataService (API endpoint)
            service = service_cls(id=socrata_ds.api_endpoint_url)
            service.endpointURL.append(URIRef(socrata_ds.api_endpoint_url))
            service.servesDataset.append(dataset)
            service.conformsTo.append(URIRef(socrata_ds.api_foundry_url))

            service_type_uri = URIRef("https://highvaluedata.net/vocab/service_type#SocrataOpenDataAPI")
            service.type.append(service_type_uri)

            if active_profile == DcatProfile.AP_HVD:
                service.add_applicable_legislation(dcat_ap_hvd.HVD_REGULATION)

            catalog.add_dataset(dataset)
            catalog.add_service(service)

        graph = catalog.to_rdf_graph()
        if active_profile == DcatProfile.US:
            graph.bind("dcat-us", dcat_us.DCAT_US, override=True)
        elif active_profile in (DcatProfile.AP, DcatProfile.AP_HVD):
            graph.bind("dcatap", dcat_ap.DCATAP, override=True)
        return graph
