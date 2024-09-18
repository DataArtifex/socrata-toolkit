"""
DCAT support for Socrata

"""
from .socrata import SocrataServer, SocrataDataset
from dartfx.rdf import utils
from dartfx.dcat import dcat
from rdflib import Graph

class DcatGenerator:
    server: SocrataServer    
    datasets: list[SocrataDataset]
    uri_generator: utils.UriGenerator
    
    def __init__(self, server: SocrataServer, datasets: list[SocrataDataset|str] = None, uri_generator: utils.UriGenerator   = utils.UuidUrnGenerator()):
        self.server = server
        if not datasets:
            self.datasets = []
        else:
            self.add_datasets(datasets)

    def get_prefixes_ttl(self, dataset: SocrataDataset) -> str:
        prefixes = """
        @prefix hvdn: <https://rdf.highvaluedata.net/dcat#> .
        @prefix catalog: <https://catalog.highvaluedata.net/> .

        @prefix dcat: <http://www.w3.org/ns/dcat#> .
        @prefix dcterms: <http://purl.org/dc/terms/> .
        @prefix foaf: <http://xmlns.com/foaf/0.1/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        """
        return prefixes
    
    def add_dataset(self, dataset: SocrataDataset|str) -> None:
        self.add_datasets([dataset])

    def add_datasets(self, datasets: list[SocrataDataset|str]) -> None:
        for item in datasets:
            if isinstance(item, SocrataDataset):
                self.datasets.append(item)
            elif isinstance(item, str):
                self.datasets.append(SocrataDataset(self.server, item))
            else:
                raise ValueError(f"Unexpected dataset type: {type(item)}")

    def get_graph(self) -> Graph:
        g = Graph()
        
        #
        # Initialize Catalog
        #
        dcat_catalog = dcat.Catalog()
        dcat_catalog.set_uri(self.server.get_urn())
        dcat_catalog.add_title(self.server.name)
        dcat_catalog.add_publisher(f"https://{self.server.host}")
        for value in self.server.publisher:
            dcat_catalog.add_publisher(value)
        for value in self.server.spatial_coverage:
            dcat_catalog.add_spatial(value)
        
        # Loop over datasets
        for socrata_ds in self.datasets:
            #
            # populate DCAT dataset
            #
            dcat_ds = dcat.Dataset()
            dcat_ds.set_uri(socrata_ds.get_urn())
            dcat_ds.add_title(socrata_ds.name)
            
            for keyword in socrata_ds.tags:
                dcat_ds.add_keyword(keyword)
                
            dcat_ds.add_landing_page(socrata_ds.landing_page)
            
            if socrata_ds.license_id:
                dcat_ds.add_license(socrata_ds.license_id)
            if socrata_ds.license_name:
                dcat_ds.add_license(socrata_ds.license_name)
            if socrata_ds.license_link:
                dcat_ds.add_license(socrata_ds.license_link)
            if socrata_ds.rows_updated_at:
                dcat_ds.add_modified_date(socrata_ds.rows_updated_at)
            elif socrata_ds.view_last_modified:
                dcat_ds.add_modified_date(socrata_ds.view_last_modified)
            
            dcat_ds.add_publisher(f"https://{socrata_ds.server.host}")
            for value in socrata_ds.server.publisher:
                dcat_ds.add_publisher(value)

            for value in socrata_ds.server.spatial_coverage:
                dcat_ds.add_spatial(value)

            # add dataset to catalog
            dcat_catalog.add_dataset(dcat_ds)

            #
            # populate DCAT CSV distribution
            #
            dcat_csv = dcat.Distribution()
            dcat_csv.set_uri(dcat_ds.get_uri()+"_csv")
            dcat_csv.add_download_url(socrata_ds.csv_download_url)
            dcat_csv.add_media_type("http://www.iana.org/assignments/media-types/text/csv")

            # add distribution to graph
            dcat_csv.add_to_rdf_graph(g)
            # add distribution dataset
            dcat_ds.add_distribution(dcat_csv)

            #
            # populate DCAT API service
            #
            dcat_api = dcat.DataService()
            dcat_api.set_uri(dcat_ds.get_uri()+"_api")
            dcat_api.add_served_dataset(dcat_ds)
            dcat_api.add_conforms_to(socrata_ds.api_foundry_url)
            dcat_api.add_endpoint_url(socrata_ds.api_endpoint_url)
            dcat_api.add_type("http://rdf.highvaluedata.net/vocab/service_type#SocrataOpenDataAPI")
            
            # add dataset resources to graph
            dcat_ds.add_to_rdf_graph(g)
            dcat_csv.add_to_rdf_graph(g)
            dcat_api.add_to_rdf_graph(g)
        
        # add catalog to graph
        dcat_catalog.add_to_rdf_graph(g)
        return g
    