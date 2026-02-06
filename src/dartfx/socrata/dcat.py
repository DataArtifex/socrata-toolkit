from __future__ import annotations
from datetime import datetime
from typing import Annotated, List, Optional, Union, cast, ClassVar
from rdflib import DCAT, DCTERMS, FOAF, URIRef, Namespace, Graph
from dartfx.rdf.pydantic import RdfBaseModel, RdfProperty
from .socrata import SocrataServer, SocrataDataset
from dartfx.rdf import utils as rdfutils

# Extra namespaces used in Socrata DCAT
HVDN = Namespace("https://rdf.highvaluedata.net/dcat#")
CATALOG = Namespace("https://catalog.highvaluedata.net/")

class DcatBaseModel(RdfBaseModel):
    """Base class for DCAT Pydantic models with shared prefixes."""
    rdf_prefixes: ClassVar[dict[str, Union[str, Namespace]]] = {
        "dcat": DCAT,
        "dcterms": DCTERMS,
        "foaf": FOAF,
        "hvdn": HVDN,
    }

class Distribution(DcatBaseModel):
    """Pydantic model for dcat:Distribution."""
    rdf_type: ClassVar[str] = str(DCAT.Distribution)
    
    id: str
    title: Annotated[Optional[List[str]], RdfProperty(DCTERMS.title)] = None
    description: Annotated[Optional[List[str]], RdfProperty(DCTERMS.description)] = None
    download_url: Annotated[Optional[List[URIRef]], RdfProperty(DCAT.downloadURL)] = None
    media_type: Annotated[Optional[List[URIRef]], RdfProperty(DCAT.mediaType)] = None
    format: Annotated[Optional[List[str]], RdfProperty(DCTERMS["format"])] = None

class Dataset(DcatBaseModel):
    """Pydantic model for dcat:Dataset."""
    rdf_type: ClassVar[str] = str(DCAT.Dataset)
    
    id: str
    title: Annotated[Optional[List[str]], RdfProperty(DCTERMS.title)] = None
    description: Annotated[Optional[List[str]], RdfProperty(DCTERMS.description)] = None
    keyword: Annotated[Optional[List[str]], RdfProperty(DCAT.keyword)] = None
    landing_page: Annotated[Optional[List[URIRef]], RdfProperty(DCAT.landingPage)] = None
    license: Annotated[Optional[List[Union[URIRef, str]]], RdfProperty(DCTERMS.license)] = None
    publisher: Annotated[Optional[List[Union[URIRef, str]]], RdfProperty(DCTERMS.publisher)] = None
    spatial: Annotated[Optional[List[Union[URIRef, str]]], RdfProperty(DCTERMS.spatial)] = None
    modified: Annotated[Optional[List[datetime]], RdfProperty(DCTERMS.modified)] = None
    distribution: Annotated[Optional[List[Distribution]], RdfProperty(DCAT.distribution)] = None

class DataService(DcatBaseModel):
    """Pydantic model for dcat:DataService."""
    rdf_type: ClassVar[str] = str(DCAT.DataService)
    
    id: str
    endpoint_url: Annotated[Optional[List[URIRef]], RdfProperty(DCAT.endpointURL)] = None
    serves_dataset: Annotated[Optional[List[Dataset]], RdfProperty(DCAT.servesDataset)] = None
    endpoint_description: Annotated[Optional[List[str]], RdfProperty(DCAT.endpointDescription)] = None
    conforms_to: Annotated[Optional[List[URIRef]], RdfProperty(DCTERMS.conformsTo)] = None
    type: Annotated[Optional[List[URIRef]], RdfProperty(DCTERMS.type)] = None

class Catalog(DcatBaseModel):
    """Pydantic model for dcat:Catalog."""
    rdf_type: ClassVar[str] = str(DCAT.Catalog)
    
    id: str
    title: Annotated[Optional[List[str]], RdfProperty(DCTERMS.title)] = None
    publisher: Annotated[Optional[List[Union[URIRef, str]]], RdfProperty(DCTERMS.publisher)] = None
    spatial: Annotated[Optional[List[Union[URIRef, str]]], RdfProperty(DCTERMS.spatial)] = None
    dataset: Annotated[Optional[List[Dataset]], RdfProperty(DCAT.dataset)] = None
    service: Annotated[Optional[List[DataService]], RdfProperty(DCAT.service)] = None
    homepage: Annotated[Optional[List[URIRef]], RdfProperty(FOAF.homepage)] = None

class DcatGenerator:
    server: SocrataServer    
    datasets: list[SocrataDataset]
    uri_generator: rdfutils.UriGenerator
    
    def __init__(self, server: SocrataServer, datasets: list[SocrataDataset|str] = None, uri_generator: rdfutils.UriGenerator = rdfutils.UuidUrnGenerator()):
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
                self.datasets.append(SocrataDataset(server=self.server, id=item))
            else:
                raise ValueError(f"Unexpected dataset type: {type(item)}")

    def get_graph(self) -> Graph:
        #
        # Initialize Catalog
        #
        catalog = Catalog(
            id=f"https://{self.server.host}",
            title=[self.server.name] if self.server.name else [],
            publisher=[f"https://{self.server.host}"] + self.server.publisher,
            spatial=self.server.spatial or [],
            dataset=[],
            service=[]
        )
        
        # Loop over datasets
        for socrata_ds in self.datasets:
            #
            # populate DCAT dataset
            #
            dcat_ds = Dataset(
                id=socrata_ds.landing_page,
                title=[socrata_ds.name],
                description=[socrata_ds.description] if socrata_ds.description else [],
                keyword=socrata_ds.tags or [],
                landing_page=[URIRef(socrata_ds.landing_page)],
                publisher=[f"https://{socrata_ds.server.host}"] + (socrata_ds.server.publisher or []),
                spatial=socrata_ds.server.spatial or [],
                distribution=[]
            )

            # License
            licenses = []
            if socrata_ds.license_id: licenses.append(socrata_ds.license_id)
            if socrata_ds.license_name: licenses.append(socrata_ds.license_name)
            if socrata_ds.license_link: licenses.append(socrata_ds.license_link)
            dcat_ds.license = licenses

            # Dates
            if socrata_ds.rows_updated_at:
                dcat_ds.modified = [socrata_ds.rows_updated_at]
            elif socrata_ds.view_last_modified:
                dcat_ds.modified = [socrata_ds.view_last_modified]
            
            # add dataset to catalog
            catalog.dataset.append(dcat_ds)

            #
            # populate DCAT CSV distribution
            #
            dcat_csv = Distribution(
                id=socrata_ds.csv_download_url,
                download_url=[URIRef(socrata_ds.csv_download_url)],
                media_type=[URIRef("http://www.iana.org/assignments/media-types/text/csv")]
            )
            # add distribution to dataset
            dcat_ds.distribution.append(dcat_csv)

            #
            # populate DCAT API service
            #
            dcat_api = DataService(
                id=socrata_ds.api_endpoint_url,
                endpoint_url=[URIRef(socrata_ds.api_endpoint_url)],
                serves_dataset=[dcat_ds],
                conforms_to=[URIRef(socrata_ds.api_foundry_url)],
                type=[URIRef("https://highvaluedata.net/vocab/service_type#SocrataOpenDataAPI")]
            )
            # add service to catalog
            catalog.service.append(dcat_api)
        
        # return the graph
        return catalog.to_rdf_graph()
    