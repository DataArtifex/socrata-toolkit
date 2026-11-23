from rdflib import DCAT, DCTERMS, Graph, URIRef

from dartfx.dcat import dcat_ap, dcat_ap_hvd, dcat_us
from dartfx.socrata import DcatGenerator, DcatProfile


def test_sfo_311(sfo_server, sfo_dataset_311, tmp_path):
    generator = DcatGenerator(sfo_server)
    generator.add_dataset(sfo_dataset_311)

    g = generator.get_graph()
    assert isinstance(g, Graph)

    # Verify Catalog
    catalog_uri = URIRef(f"https://{sfo_server.host}")
    assert (catalog_uri, None, DCAT.Catalog) in g
    assert (catalog_uri, DCTERMS.title, None) in g

    # Verify Dataset
    ds_uri = URIRef(sfo_dataset_311.landing_page)
    assert (ds_uri, None, DCAT.Dataset) in g
    assert (ds_uri, DCTERMS.title, None) in g
    assert (catalog_uri, DCAT.dataset, ds_uri) in g

    # Verify Distribution
    dist_uri = URIRef(sfo_dataset_311.csv_download_url)
    assert (dist_uri, None, DCAT.Distribution) in g
    assert (ds_uri, DCAT.distribution, dist_uri) in g
    assert (dist_uri, DCAT.downloadURL, dist_uri) in g

    # Verify DataService
    svc_uri = URIRef(sfo_dataset_311.api_endpoint_url)
    assert (svc_uri, None, DCAT.DataService) in g
    assert (catalog_uri, DCAT.service, svc_uri) in g
    assert (svc_uri, DCAT.servesDataset, ds_uri) in g
    assert (svc_uri, DCAT.endpointURL, svc_uri) in g

    # Save for manual inspection
    g.serialize(destination=str(tmp_path / "sfo_311.dcat.ttl"), format="ttl")


def test_multi_dataset(sfo_server, sfo_dataset_311, sfo_dataset_police):
    generator = DcatGenerator(sfo_server)
    generator.add_datasets([sfo_dataset_311, sfo_dataset_police])

    g = generator.get_graph()

    catalog_uri = URIRef(f"https://{sfo_server.host}")
    datasets = list(g.objects(catalog_uri, DCAT.dataset))

    assert len(datasets) == 2
    assert URIRef(sfo_dataset_311.landing_page) in datasets
    assert URIRef(sfo_dataset_police.landing_page) in datasets

    # Verify both have titles
    for ds in datasets:
        assert (ds, DCTERMS.title, None) in g


def test_dcat_profiles(sfo_server, sfo_dataset_311):
    # Default profile is DCAT-US 3.0
    gen_default = DcatGenerator(sfo_server, [sfo_dataset_311])
    assert gen_default.profile == DcatProfile.US
    g_us = gen_default.get_graph()
    ds_uri = URIRef(sfo_dataset_311.landing_page)
    assert (ds_uri, dcat_us.DCAT_US.accessRestriction, None) in g_us

    # W3C DCAT 3 profile omits DCAT-US accessRestriction
    g_w3c = gen_default.get_graph(profile="w3c")
    assert (ds_uri, DCAT.landingPage, None) in g_w3c
    assert (ds_uri, dcat_us.DCAT_US.accessRestriction, None) not in g_w3c

    # DCAT-AP profile
    g_ap = DcatGenerator(sfo_server, [sfo_dataset_311], profile="ap").get_graph()
    assert (ds_uri, DCAT.landingPage, None) in g_ap

    # DCAT-AP HVD profile adds HVD legislation and accessURL
    g_hvd = DcatGenerator(sfo_server, [sfo_dataset_311], profile="ap-hvd").get_graph()
    assert (ds_uri, dcat_ap.DCATAP.applicableLegislation, URIRef(dcat_ap_hvd.HVD_REGULATION)) in g_hvd
    dist_uri = URIRef(sfo_dataset_311.csv_download_url)
    assert (dist_uri, DCAT.accessURL, dist_uri) in g_hvd
