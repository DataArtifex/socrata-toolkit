import json

import pytest
from rdflib import Graph

from dartfx.cdif import (
    CdifDataDescriptionDataset,
    CdifDiscoveryDataset,
    XsdDataType,
    detect_profiles,
    load_cdif,
)
from dartfx.cdif.models.common import (
    CdifInstanceVariable,
    CdifKey,
    DataDownload,
    Statistics,
    WebAPI,
)
from dartfx.socrata import CdifGenerator, SocrataDataset, SocrataServer
from dartfx.socrata.cdif import resolve_serialization_flavor


def test_discovery_single_datasets(
    sfo_server: SocrataServer,
    sfo_dataset_311: SocrataDataset,
    sfo_dataset_police: SocrataDataset,
    nyc_server: SocrataServer,
    nyc_dataset_311: SocrataDataset,
) -> None:
    for srv, ds in [
        (sfo_server, sfo_dataset_311),
        (sfo_server, sfo_dataset_police),
        (nyc_server, nyc_dataset_311),
    ]:
        gen = CdifGenerator(server=srv)
        model = gen.build_discovery(ds)
        assert isinstance(model, CdifDiscoveryDataset)
        assert model.validate_conformance() == []
        assert model.id == ds.landing_page
        assert model.name == ds.name
        assert model.url == ds.landing_page
        assert model.subject_of is not None
        assert model.distribution is not None
        assert any(isinstance(d, DataDownload) for d in model.distribution)
        assert any(isinstance(d, WebAPI) for d in model.distribution)
        assert model.spatial_coverage is not None

        profiles = [p.key for p in detect_profiles(model)]
        assert "discovery" in profiles


def test_dataset_get_cdif_convenience(sfo_dataset_311: SocrataDataset) -> None:
    disc = sfo_dataset_311.get_cdif(profile="discovery")
    assert isinstance(disc, CdifDiscoveryDataset)
    assert disc.validate_conformance() == []

    dd = sfo_dataset_311.get_cdif(profile="data_description")
    assert isinstance(dd, CdifDataDescriptionDataset)
    assert dd.validate_conformance() == []

    with pytest.raises(ValueError, match="Unsupported CDIF profile"):
        sfo_dataset_311.get_cdif(profile="unknown")


def test_data_description_variables_pk_and_stats(
    sfo_server: SocrataServer,
    sfo_dataset_311: SocrataDataset,
) -> None:
    gen = CdifGenerator(server=sfo_server)
    model = gen.build_data_description(
        sfo_dataset_311,
        include_stats=True,
        include_codes=True,
        max_codes=5,
    )
    assert isinstance(model, CdifDataDescriptionDataset)
    assert model.validate_conformance() == []

    profiles = [p.key for p in detect_profiles(model)]
    assert "data_description" in profiles

    # Variables are CdifInstanceVariable instances with mapped physicalDataType
    assert isinstance(model.variable_measured, list)
    assert len(model.variable_measured) == sfo_dataset_311.get_variable_count()
    first_var = model.variable_measured[0]
    assert isinstance(first_var, CdifInstanceVariable)
    assert first_var.name == "service_request_id"
    assert first_var.alternate_name == "CaseID"
    assert first_var.physical_data_type == [XsdDataType.DECIMAL]
    assert first_var.min_value == 240215
    assert first_var.max_value == 101001690764
    assert first_var.role == "UnitIdentifier"
    assert first_var.is_described_by_statistics_collection is not None

    # Primary key derived from rowIdentifierColumnId
    assert isinstance(model.has_primary_key, CdifKey)
    assert isinstance(model.has_primary_key.is_composed_of, list)
    assert len(model.has_primary_key.is_composed_of) == 1
    assert model.has_primary_key.is_composed_of[0].indexes is not None

    # Dataset-level rowCount statistic
    assert isinstance(model.statistics, list)
    assert len(model.statistics) == 1
    assert isinstance(model.statistics[0], Statistics)
    assert model.statistics[0].type_of_statistic == "rowCount"


@pytest.mark.parametrize(
    ("flavor", "expected_rdf_fmt"),
    [
        ("json", None),
        ("json-ld", None),
        ("ttl", "turtle"),
        ("turtle", "turtle"),
        ("xml", "xml"),
        ("n3", "n3"),
    ],
)
def test_serialization_flavors_single_and_multi(
    sfo_server: SocrataServer,
    sfo_dataset_311: SocrataDataset,
    sfo_dataset_police: SocrataDataset,
    flavor: str,
    expected_rdf_fmt: str | None,
) -> None:
    gen = CdifGenerator(server=sfo_server, datasets=[sfo_dataset_311, sfo_dataset_police])

    single_model = gen.build_discovery(sfo_dataset_311)
    single_out = gen.serialize(single_model, flavor=flavor)
    assert single_out.strip()

    multi_models = gen.get_models(profile="data_description", include_stats=True)
    multi_out = gen.serialize(multi_models, flavor=flavor)
    assert multi_out.strip()

    if expected_rdf_fmt is None:
        parsed_single = json.loads(single_out)
        assert parsed_single["@id"] == sfo_dataset_311.landing_page
        loaded = load_cdif(single_out)
        assert isinstance(loaded, CdifDiscoveryDataset)

        parsed_multi = json.loads(multi_out)
        assert "@graph" in parsed_multi
        assert len(parsed_multi["@graph"]) == 2
    else:
        g_single = Graph()
        g_single.parse(data=single_out, format=expected_rdf_fmt)
        assert len(g_single) > 0

        g_multi = Graph()
        g_multi.parse(data=multi_out, format=expected_rdf_fmt)
        assert len(g_multi) > 0


def test_search_results_to_cdif_discovery(sfo_server: SocrataServer) -> None:
    raw_search = sfo_server.search_datasets(q="cases", limit=5)
    gen = CdifGenerator(server=sfo_server)
    models = gen.build_from_search_results(raw_search)
    assert len(models) == 1
    model = models[0]
    assert isinstance(model, CdifDiscoveryDataset)
    assert model.validate_conformance() == []
    assert model.name == "311 Cases"
    assert model.id == "https://data.sfgov.org/d/vw6y-z8j6"


def test_missing_license_falls_back_to_conditions_of_access(
    sfo_server: SocrataServer,
    sfo_dataset_311: SocrataDataset,
) -> None:
    no_license_data = dict(sfo_dataset_311.data)
    no_license_data.pop("license", None)
    no_license_data.pop("licenseId", None)

    ds_copy = SocrataDataset.model_construct(server=sfo_server, id=sfo_dataset_311.id)
    ds_copy._data = no_license_data

    gen = CdifGenerator(server=sfo_server)
    model = gen.build_discovery(ds_copy)
    assert model.license is None
    assert model.conditions_of_access is not None
    assert model.validate_conformance() == []


def test_invalid_flavor_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported serialization flavor"):
        resolve_serialization_flavor("yaml")
