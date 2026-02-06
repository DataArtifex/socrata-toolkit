import os
from pathlib import Path
from rdflib import Graph, DCAT, DCTERMS, FOAF, URIRef
from dartfx.socrata import SocrataServer, SocrataDataset, DcatGenerator

sfo_server = SocrataServer(host="data.sfgov.org")
sfo_dataset_311 = SocrataDataset(server=sfo_server, id="vw6y-z8j6")
# A second dataset for testing multiple datasets in a catalog
sfo_dataset_police = SocrataDataset(server=sfo_server, id="wg3w-h783")

def test_sfo_311(tests_dir: Path):
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
    g.serialize(destination=os.path.join(tests_dir, "sfo_311.dcat.ttl"), format="ttl")

def test_multi_dataset(tests_dir: Path):
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

