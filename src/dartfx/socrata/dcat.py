from __future__ import annotations
from typing import List, Union
from rdflib import URIRef, Namespace, Graph
from dartfx.dcat.dcat import Catalog, Dataset, Distribution, DataService
from .socrata import SocrataServer, SocrataDataset

# Extra namespaces used in Socrata DCAT
HVDN = Namespace("https://rdf.highvaluedata.net/dcat#")
CATALOG = Namespace("https://catalog.highvaluedata.net/")

class DcatGenerator:
    """Generate DCAT metadata for Socrata datasets using official dartfx.dcat Pydantic models."""
    
    server: SocrataServer    
    datasets: list[SocrataDataset]
    
    def __init__(self, server: SocrataServer, datasets: list[SocrataDataset|str] = None):
        """Initialize the DCAT generator.
        
        Args:
            server: The Socrata server to generate metadata for
            datasets: Optional list of datasets to include (can be SocrataDataset instances or ID strings)
        """
        self.server = server
        self.datasets = []
        if datasets:
            self.add_datasets(datasets)
        
    def add_dataset(self, dataset: Union[SocrataDataset, str]) -> None:
        """Add a dataset to the catalog.
        
        Args:
            dataset: Either a SocrataDataset instance or a dataset ID string
        """
        self.add_datasets([dataset])
        
    def add_datasets(self, datasets: List[Union[SocrataDataset, str]]) -> None:
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
    
    def get_graph(self) -> Graph:
        """Generate an RDF graph containing DCAT metadata for all datasets.
        
        Uses the official dartfx.dcat Pydantic models with their helper methods
        for cleaner, more maintainable code.
        
        Returns:
            RDFLib Graph containing the DCAT metadata
        """
        # Create catalog using official dartfx.dcat model
        catalog_uri = f"https://{self.server.host}"
        catalog = Catalog(id=catalog_uri)
        
        # Add catalog metadata using helper methods
        if self.server.name:
            catalog.add_title(self.server.name)
        
        # Add publishers
        catalog.add_publisher(f"https://{self.server.host}")
        if self.server.publisher:
            for pub in self.server.publisher:
                catalog.add_publisher(pub)
                
        # Add spatial coverage
        if self.server.spatial:
            for spatial in self.server.spatial:
                catalog.spatial.append(spatial)
        
        # Process each dataset
        for socrata_ds in self.datasets:
            # Create Dataset using official dartfx.dcat model
            dataset = Dataset(id=socrata_ds.landing_page)
            
            # Add dataset metadata using helper methods
            if socrata_ds.name:
                dataset.add_title(socrata_ds.name)
            
            if socrata_ds.description:
                dataset.add_description(socrata_ds.description)
            
            # Add keywords
            if socrata_ds.tags:
                for tag in socrata_ds.tags:
                    dataset.add_keyword(tag)
            
            # Landing page
            dataset.add_landing_page(URIRef(socrata_ds.landing_page))
            
            # License
            if socrata_ds.license_id:
                dataset.add_license(socrata_ds.license_id)
            if socrata_ds.license_name:
                dataset.add_license(socrata_ds.license_name)
            if socrata_ds.license_link:
                dataset.add_license(socrata_ds.license_link)
            
            # Modified date
            if socrata_ds.rows_updated_at:
                dataset.add_modified_date(socrata_ds.rows_updated_at)
            elif socrata_ds.view_last_modified:
                dataset.add_modified_date(socrata_ds.view_last_modified)
            
            # Publishers
            dataset.add_publisher(f"https://{socrata_ds.server.host}")
            if socrata_ds.server.publisher:
                for pub in socrata_ds.server.publisher:
                    dataset.add_publisher(pub)
            
            # Spatial coverage
            if socrata_ds.server.spatial:
                for spatial in socrata_ds.server.spatial:
                    dataset.spatial.append(spatial)
            
            # Create Distribution (CSV download) using official dartfx.dcat model
            distribution = Distribution(id=socrata_ds.csv_download_url)
            distribution.add_download_url(URIRef(socrata_ds.csv_download_url))
            distribution.add_media_type(URIRef("http://www.iana.org/assignments/media-types/text/csv"))
            
            # Add distribution to dataset
            dataset.distribution.append(distribution)
            
            # Create DataService (API endpoint) using official dartfx.dcat model
            service = DataService(id=socrata_ds.api_endpoint_url)
            service.endpointURL.append(URIRef(socrata_ds.api_endpoint_url))
            service.servesDataset.append(dataset)
            
            # Add conformance to Socrata Foundry docs
            service.conformsTo.append(URIRef(socrata_ds.api_foundry_url))
            
            # Add service type
            service_type_uri = URIRef("https://highvaluedata.net/vocab/service_type#SocrataOpenDataAPI")
            service.type.append(service_type_uri)
            
            # Add dataset and service to catalog using helper methods
            catalog.add_dataset(dataset)
            catalog.add_service(service)
        
        # Convert to RDF graph using the Pydantic model's built-in method
        return catalog.to_rdf_graph()