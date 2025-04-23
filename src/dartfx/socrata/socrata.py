from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from markdownify import markdownify
import mlcroissant as mlc
import os
from pydantic import BaseModel, Field, PrivateAttr
from typing import Optional
import requests
from xml.sax.saxutils import escape

class SocrataApiError(Exception):
    """Custom exception for Socrata API errors."""

    def __init__(self, message, url, status_code=None, response=None):
        super().__init__(message)
        self.message = message
        self.url = url
        self.status_code = status_code
        self.response = response

    def __str__(self):
        base_message = f"SocrataApiError: {self.message}"
        if self.status_code is not None:
            base_message += f" (Status Code: {self.status_code})"
        if self.response is not None:
            base_message += f" (Response: {self.response})"
        return base_message


SERVERS = {
    "data.calgary.ca": {
        "name": "Calgary Open Data",
        "publisher": ["City of Calgary"],
        "spatial": ["Calgary, Alberta, Canada", "http://sws.geonames.org/5913490"]
    },
    "data.cityofchicago.org": {
        "name": "Chicago Data Portal",
        "publisher": ["City of Chicago"],
        "spatial": ["Chicago, Illinois, USA", "http://sws.geonames.org/4887398"]
    },
    "data.cdc.gov": {
        "name": "U.S. Centers for Disease Control and Prevention",
        "publisher": ["U.S. Centers for Disease Control and Prevention"],
        "spatial": ["United States", "http://sws.geonames.org/6252001"]
    },
    "data.cityofnewyork.us": {
        "name": "NYC Open Data",
        "publisher": ["City of New York", "https://opendata.cityofnewyork.us/"],
        "spatial": ["New York City, New York, USA", "http://sws.geonames.org/5128581"]
    },
    "data.edmonton.ca": {
        "name": "City of Edmonton's Open Data Portal",
        "publisher": ["City of Edmonton"],
        "spatial": ["Edmonton, Alberta, Canada", "http://sws.geonames.org/5946768"]
    },
    "data.ny.gov": {
        "name": "New York State Open Data",
        "publisher": ["New York State"],
        "spatial": ["New York, USA", "http://sws.geonames.org/5128638"]
    },
    "data.sfgov.org": {
        "name": "San Francisco Open Data Portal",
        "publisher": ["City of San Francisco"],
        "spatial": ["San Francisco, California, USA", "http://sws.geonames.org/5391959"]
    },
    "opendata.utah.gov": {
        "name": "State of Utah Open Data Catalog",
        "publisher": ["State of Utah"],
        "spatial": ["Utah, USA", "http://sws.geonames.org/5549030"]
    },
    "data.wa.gov": {
        "name": "Washington State Open Data Portal",
        "publisher": ["Washington state government"],
        "spatial": ["Washington, USA", "http://sws.geonames.org/5815135"]
    },
    "datos.gov.co": {
        "name": "Datos abierrtos de Columbia",
        "publisher": ["Ministerio de Tecnologías de la Información y las Comunicaciones"],
        "spatial": ["Washington, USA", "http://sws.geonames.org/3686110"],
        "languages": ["es"]
    }
}

class SocrataServer(BaseModel):
    host: str
    name: str | None = Field(default=None)
    disk_cache_root: str | None = Field(default=None) # a directory will be created here for this server
    _in_memory_cache: dict = PrivateAttr(default_factory=dict)
    
    # attributes not available in Dataset metadata
    publisher: Optional[list[str]] = field(default_factory=list)
    spatial: Optional[list[str]] = field(default_factory=list)

    def model_post_init(self, __context):
        # set metadata for know servers
        if self.host in SERVERS:
            self.name = SERVERS[self.host].get("name",self.host)
            self.publisher = SERVERS[self.host].get("publisher",[])
            self.spatial = SERVERS[self.host].get("spatial",[])
        else:
            self.name = self.host
            self.publisher = [self.host_url]

    @property
    def disk_cache_dir(self):
        if self.disk_cache_root:
            if os.path.isdir(self.disk_cache_root):
                if self.disk_cache_root:
                    path = os.path.join(self.disk_cache_root, self.host)
                    os.makedirs(path, exist_ok=True)
                    return path
            else:
                raise ValueError(f"Cache root directory does not exist: {self.disk_cache_root}")

    @property
    def memory_cache(self):
        return self._in_memory_cache

    @property
    def host_url(self):
        return f"https://{self.host}"
    
    def get_dataset_info(self, dataset_id, refresh=False):
        # check if in memory cache
        if dataset_id in self.memory_cache and not refresh:
            return self.memory_cache[dataset_id]
        # init local file if cache is enabled
        file_name = f"{dataset_id}.json"
        if self.disk_cache_dir:
            file_path = os.path.join(self.disk_cache_dir, file_name)
        if self.disk_cache_dir and os.path.isfile(file_path) and not refresh:
            # load from disk cache
            logging.debug(f"Loading from disk cache {file_path}")
            with open(file_path) as f:
                data = json.load(f)
                self.memory_cache[dataset_id] = data
                return data
        else:
            # retrieve from server
            url = f"https://{self.host}/api/views/{file_name}"
            results = requests.get(url)
            if results.status_code == 200:
                data = results.json()
                # save to disk cache if enabled
                if self.disk_cache_dir: # save to local cache if enabled
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=4)
                # save to in memory cache
                self.memory_cache[dataset_id] = data
                return data
            else:
                raise SocrataApiError("Error getting dataset info", url, results.status_code, results.text)
        return
    
    def search_datasets(self):
        """Calls the Socrata Discovery API

        See https://dev.socrata.com/docs/other/discovery

        Raises:
            SocrataApiError: Error when calling the API
        """
        url = f"https://{self.host}/api/catalog/v1?domains={self.host}&only=datasets"
        results = requests.get(url)
        if results.status_code == 200:
            data = results.json()
            return(data)
        else:
            raise SocrataApiError("Search error", url, results.status_code, results.text)
        
    
class SocrataDataset(BaseModel):
    server: SocrataServer
    id: str
    _data: dict 
    _variables: list["SocrataVariable"] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context):
        self._data = self.server.get_dataset_info(self.id)
        if self.asset_type != 'dataset':
            raise ValueError(f"Unexpected asset type: {self.asset_type}. Must be 'dataset'.")

    @property
    def api_foundry_url(self):
        return f"https://dev.socrata.com/foundry/{self.server.host}/{self.id}"

    @property
    def api_endpoint_url(self):
        return f"https://{self.server.host}/resource/{self.id}.json"


    @property   
    def csv_download_url(self):
        return f"https://{self.server.host}/resource/{self.id}.csv"

    @property   
    def data(self):
        return self._data

    @property
    def asset_type(self):
        return self._data.get("assetType")

    @property
    def description(self):
        return self._data.get("description")

    @property
    def landing_page(self):
        #category = self._data.get("category").replace(" ", "-")
        #name = self._data.get("name").replace(" ", "-")
        #return f"https://{self.server.host}/{category}/{name}/{self.id}"
        return f"https://{self.server.host}/d/{self.id}"

    @property
    def license(self):
        """Combines available license properties or returns Unknown if not available"""
        license_terms = [x for x in [self.license_name, self.license_id, self.license_link] if x is not None]
        if license_terms:
            license = ', '.join(license_terms)
        else:
            license = ['Unknown']
        return license

    @property
    def license_id(self):
        if self._data.get("licenseId"):
            return self._data.get("licenseId")
        
    @property
    def license_name(self):
        if self._data.get("license"):
            return self._data["license"].get("name")
        
    @property
    def license_link(self):
        if self._data.get("license"):
            return self._data["license"].get("termsLink")

    @property
    def name(self):
        return self._data.get("name")

    @property
    def publication_date(self) -> datetime:
        if self._data.get("publicationDate"):
            return datetime.fromtimestamp(self._data.get("publicationDate"))

    @property
    def rows_updated_at(self) -> datetime:
        if self._data.get("rowsUpdatedAt"):
            return datetime.fromtimestamp(self._data.get("rowsUpdatedAt"))

    @property
    def tags(self):
        return self._data.get("tags")
    
    @property
    def variables(self) -> list["SocrataVariable"]:
        if not self._variables:
            self._variables = []
            for index, column in enumerate(self._data["columns"]):
                self._variables.append(SocrataVariable(dataset=self, index=index))
        return self._variables

    @property
    def view_last_modified(self) -> datetime:
        if self._data.get("viewLastModified"):
            return datetime.fromtimestamp(self._data["viewLastModified"])

    def get_code(self, environment, options: dict = None, *args, **kwargs) -> str:
        code = None

        if environment == "jquery":
            code = """
$.ajax({{
    url: "https://{host}/resource/{dataset_id}.json",
    type: "GET",
    data: {{
      "$limit" : 5000,
      "$$app_token" : "YOURAPPTOKENHERE"
    }}
}}).done(function(data) {{
  alert("Retrieved " + data.length + " records from the dataset!");
  console.log(data);
}});
"""
        elif environment == "powershell":
            code = """
$url = "https://{host}/resource/{dataset_id}"
$apptoken = "YOURAPPTOKENHERE"

# Set header to accept JSON
$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add("Accept","application/json")
$headers.Add("X-App-Token",$apptoken)

$results = Invoke-RestMethod -Uri $url -Method get -Headers $headers
            """
        elif environment == "python-pandas":
            code = """
#!/usr/bin/env python

# make sure to install these packages before running:
# pip install pandas
# pip install sodapy

import pandas as pd
from sodapy import Socrata

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
client = Socrata("{host}", None)

# Example authenticated client (needed for non-public datasets):
# client = Socrata({host},
#                  MyAppToken,
#                  username="user@example.com",
#                  password="AFakePassword")

# First 2000 results, returned as JSON from API / converted to Python list of
# dictionaries by sodapy.
results = client.get("{dataset_id}", limit=2000)

# Convert to pandas DataFrame
results_df = pd.DataFrame.from_records(results)

print(results_df)
            """
        elif environment == "r-socrata":
            code = """
## Install the required package with:
## install.packages("RSocrata")

library("RSocrata")

df <- read.socrata(
  "https://{host}/resource/{dataset_id}.json",
  app_token = "YOURAPPTOKENHERE",
  email     = "user@example.com",
  password  = "fakepassword"
)            
            """
        elif environment == "sas":
            code = """
filename datain url 'http://{host}/resource/{dataset_id}.csv?$limit=5000&$$app_token=YOURAPPTOKENHERE';
proc import datafile=datain out=dataout dbms=csv replace;
  getnames=yes;
run;
            """     
        elif environment == "soda-ruby":
            code = """
#!/usr/bin/env ruby

require 'soda/client'

client = SODA::Client.new({{:domain => "{host}", :app_token => "YOURAPPTOKENHERE"}})

results = client.get("{dataset_id}", :$limit => 5000)

puts "Got #{{results.count}} results. Dumping first results:"
results.first.each do |k, v|
  puts "#{{key}}: #{{value}}"
end
            """
        elif environment == "soda-dotnet":
            code = """
using System;
using System.Linq;

// Install the package from Nuget first:
// PM> Install-Package CSM.SodaDotNet
using SODA;

var client = new SodaClient("https://{host}", "YOURAPPTOKENHERE");

// Get a reference to the resource itself
// The result (a Resouce object) is a generic type
// The type parameter represents the underlying rows of the resource
// and can be any JSON-serializable class
var dataset = client.GetResource("{dataset_id}");

// Resource objects read their own data
var rows = dataset.GetRows(limit: 5000);

Console.WriteLine("Got {{0}} results. Dumping first results:", rows.Count());

foreach (var keyValue in rows.First())
{{
    Console.WriteLine(keyValue);
}}            
            """
        elif environment == "stata":
            code = """
clear
. import delimited "https://{host}/resource/{dataset_id}.csv?%24limit=5000&%24%24app_token=YOURAPPTOKENHERE"            
            """
        # FORMAT CODE
        if code:
            code = code.format(host=self.server.host, dataset_id=self.id)
        return code

    def get_croissant(self, include_computed=False, include_codes=True, max_codes=100) -> mlc.Metadata:
        context = mlc.Context()
        context.is_live_dataset = True
        # selected variables
        selected_variables = []
        selected_variables_names = []
        for variable in self.variables:
            if variable.is_deleted:
                continue
            if variable.is_computed and not include_computed:
                continue
            selected_variables.append(variable)
            selected_variables_names.append(variable.name)
        # metadata
        publishers = []
        for publisher in self.server.publisher:
            publishers.append(mlc.Organization(name=publisher, url=self.server.host))
        metadata = mlc.Metadata(ctx=context, 
            id=self.id,
            name=self.name,
            description=markdownify(self.description) if self.description else None,
            cite_as = f'{self.name}, {self.server.name}, {self.landing_page}',
            date_modified = self.rows_updated_at,
            date_published = self.publication_date,
            license = self.license,
            publisher=publishers,
            version = int(self.rows_updated_at.timestamp())
        )
        # distribution
        distribution = []
        content_url = self.csv_download_url
        if not include_computed:
            content_url += f'?$select={",".join(selected_variables_names)}'
        csv_file = mlc.FileObject(ctx=context, 
            id=self.id+'.csv',
            name=self.name+'.csv',
            content_url=content_url,
            encoding_formats=mlc.EncodingFormat.CSV
        )
        distribution.append(csv_file)
        metadata.distribution = distribution
        # fields and record set
        fields = []
        classifications_record_sets = []
        for variable in selected_variables:
            field = mlc.Field(ctx=context,
                id=variable.name,
                name=variable.name,
                description=variable.label,
                source=mlc.Source(file_object=csv_file.id, extract=mlc.Extract(ctx=context, column=variable.name))
            )
            field.data_types.append(variable.croissant_data_type)
            fields.append(field)
            # classifications
            if include_codes:
                if variable.cached_content: # we have statistics
                    if variable.top: # we have top codes
                        classification_id = f"{variable.name}_codes"
                        value_field_id = f"{classification_id}/value"
                        freq_field_id = f"{classification_id}/freq"
                        classification_fields = [
                            mlc.Field(ctx=context, id=value_field_id, description="Code value"),
                            mlc.Field(ctx=context, id=freq_field_id, name="freq", description="Code frequency"),
                        ]
                        # codes
                        classification_records = []
                        code_count = 0
                        for code in variable.top:
                            code_count += 1
                            classification_records.append({
                                value_field_id: str(code.get("item")),
                                freq_field_id: code.get("count")
                            })
                            if code_count >= max_codes:
                                break
                        # create record set
                        classification_record_set = mlc.RecordSet(id=classification_id, fields=classification_fields)
                        classification_record_set.description = f"Top {min(len(variable.top), max_codes)} values and frequencies for {field.name}."
                        if variable.cardinality and variable.cardinality <= max_codes:
                            # complete data
                            classification_record_set.data = classification_records
                        else:
                            # partial data
                            classification_record_set.examples = classification_records
                            if variable.cardinality:
                                classification_record_set.description = f"This is partial list. The full list has {variable.cardinality} codes."
                            else:
                                classification_record_set.description = "This may be a partial list. The variable cardinality is unknown."
                        classifications_record_sets.append(classification_record_set)
                        # add classification reference to the variable
                        field.references = mlc.Source(
                            id=f"{classification_id}/value"
                        )
        # create data file record set
        data_record_set = mlc.RecordSet(fields=fields) 
        record_sets = [data_record_set] + classifications_record_sets
        metadata.record_sets = record_sets


        return metadata

    def get_ddi_codebook(self, category_count_threshold=500, codebook_version="2.5") -> str:
        """Generate DDI-Codebook XML for this dataset.

        Returns:
            str: XML codebook
        """
        uid = f"socrata_{self.server.host}_{self.id}"
        urn = f"urn:socrata:{self.server.host}:{self.id}"
        xml = f'<codeBook ID="{uid}" ddiCodebookUrn="{urn}" version="{codebook_version}" xmlns="ddi:codebook:{codebook_version.replace(".", "_")}">'
        # docDscr
        xml += '<docDscr>'
        xml += '<citation>'
        xml += '<titlStmt>'
        xml += f'<titl>{escape(self.name)}</titl>'
        xml += f'<IDNo agency="socrata.com">{self.server.host}-{self.id}</IDNo>'
        xml += '</titlStmt>'
        xml += '<prodStmt>'
        prodDate = datetime.now().isoformat()[:-7]
        xml += f'<prodDate date="{prodDate}">{prodDate}</prodDate>'
        xml += '<software version="0.1.0">Data Artifex - Socrata (dartfx-socrata)</software>'
        xml += '</prodStmt>'
        xml += '</citation>'
        xml += '</docDscr>'
        # stdyDscr
        xml += '<stdyDscr>'
        xml += '<citation>'
        xml += '<titlStmt>'
        xml += f'<titl>{escape(self.name)}</titl>'
        xml += f'<IDNo agency="socrata.com">{self.server.host}-{self.id}</IDNo>'
        xml += '</titlStmt>'
        xml += '<prodStmt>'
        xml += '<software>Socrata</software>'
        xml += '</prodStmt>'
        xml += '</citation>'
        if self.description:
            xml += '<stdyInfo>'
            xml += f'<abstract><![CDATA[{escape(self.description)}]]></abstract>'
            xml += '</stdyInfo>'
        xml += '</stdyDscr>'
        # fileDscr
        xml += '<fileDscr ID="F1">'
        xml += '<fileTxt>'
        xml += f'<fileName>{self.name}</fileName>'
        xml += '<dimensns>'
        xml += f'<caseQnty>{self.get_record_count()}</caseQnty>'
        xml += f'<varQnty>{self.get_variable_count()}</varQnty>'
        xml += '</dimensns>'
        xml += '<fileType>socrata</fileType>'
        xml += '</fileTxt>'
        xml += '</fileDscr>'
        # dataDscr
        xml += '<dataDscr>'
        for var in self.variables:
            if var.is_hidden:
                continue
            xml += f'<var ID="V{var.id}" name="{var.name}" files="F1">'
            xml += f'<labl>{escape(var.label)}</labl>'
            if var.socrata_data_type == 'number':
                type = 'numeric'
            else:
                type = 'character'
            if var.cached_content:
                # summary statistics
                xml += f'<sumStat type="other" otherType="count">{var.count}</sumStat>' if var.count else ''
                xml += f'<sumStat type="min">{escape(var.smallest)}</sumStat>' if var.smallest else ''
                xml += f'<sumStat type="max">{escape(var.largest)}</sumStat>' if var.largest else ''
                xml += f'<sumStat type="other" otherType="cardinality">{var.cardinality}</sumStat>' if var.cardinality else ''
                xml += f'<sumStat type="vald">{var.non_null}</sumStat>' if var.non_null else ''
                xml += f'<sumStat type="invd">{var.null}</sumStat>' if var.null else ''
                if var.top and var.cardinality <=  category_count_threshold:
                    for item in var.top:
                        xml += '<catgry>'
                        xml += f'<catValu>{escape(str(item["item"]))}</catValu>'
                        xml += f'<labl>{escape(str(item["item"]))}</labl>' # Socrata does not provide category labels. Use code value.
                        xml += f'<catStat type="freq">{item["count"]}</catStat>'
                        xml += '</catgry>'                    
            xml += f'<varFormat type="{type}" schema="other" formatname="socrata">{var.socrata_data_type}</varFormat>'
            xml += '</var>'
        xml += '<notes type="dartfx" subject="variables">Be wary that Socrata does not provide category labels and by default only lists information on the top/most used codes. The DDI var/catgry sets may therefore be incomplete.</notes>'
        xml += '</dataDscr>'
        xml += '</codeBook>'
        return xml

    def get_variable_count(self, exclude_hidden=True, exclude_deleted=True, exclude_computed=True) -> int:
        count = 0
        for variable in self.variables:
            if variable.is_hidden and exclude_hidden:
                continue
            else:
                if variable.is_deleted and exclude_deleted:
                    continue
                if variable.is_computed and exclude_computed:
                    continue
            count += 1
        return count
    
    def get_markdown(self, sections=[]):
        md = f"# {markdownify(self.name)}\n\n"
        if self.description:
            md += f"{markdownify(self.description)}\n\n"
        if not sections or 'variables' in sections:
            md += f"\n## Variables\n\n"
            md += "| Name | Label | Type | Info |\n"
            md += "|---|---|---|---|\n"
            for variable in self.variables:
                if variable.is_hidden:
                    continue
                md += f"| {variable.name} | {variable.label} | {variable.socrata_data_type}"
                info = ""
                if variable.cardinality:
                    info += f"Cardinality: {variable.cardinality:,}"
                if variable.top:
                    values = []
                    for entry in variable.top[:3]:
                        values.append(str(entry.get("item")))
                    if info:
                        info += "<br/>"
                    info += f"Examples: {', '.join(values)}"
                if not info:
                    info = "-"
                md += f" | {info} |\n"
        return md

    def get_record_count(self):
        variable0 = self.variables[0]
        if variable0.cached_content:
            count = variable0.cached_content.get("count")
            return count

class SocrataVariable(BaseModel):
    """Helper class to process/use Socrata dataset variables (columns).

    This uses a standard terminology and hides Socrata proprietary attribute names.

    """
    dataset: SocrataDataset
    index: int

    @property
    def cached_content(self):
        return self.data.get('cachedContents')

    @property
    def cardinality(self):
        if self.cached_content and self.cached_content.get('cardinality'):
            return int(self.cached_content.get('cardinality'))


    @property
    def count(self):
        if self.cached_content and self.cached_content.get('count'):
            return int(self.cached_content.get('count'))

    @property
    def croissant_data_type(self):
        # https://dev.socrata.com/docs/datatypes
        if self.socrata_data_type == 'number':
            return mlc.DataType.FLOAT
        elif self.socrata_data_type == 'calendar_date':
            return mlc.DataType.DATE
        elif self.socrata_data_type =='point':
            return mlc.DataType.TEXT
        elif self.socrata_data_type =='url':
            return mlc.DataType.URL
        return mlc.DataType.TEXT
        
    @property
    def data(self):
        return self.dataset._data["columns"][self.index]

    @property
    def id(self):
        """The variable is which is always a number"""
        return self.data["id"]

    @property
    def is_computed(self):
        """The name, which is the 'fieldname' property, starts with ':@computed'"""
        return self.name.startswith(":@computed")

    @property
    def is_deleted(self):
        """The label, which is the 'name' property, starts with 'DELETE -'"""
        return self.label.startswith("DELETE -")

    @property
    def is_hidden(self):
        """Is either computed or deleted"""
        return self.is_computed or self.is_deleted

    @property
    def is_visible(self):
        """Not hdden"""
        return not self.is_hidden

    @property
    def label(self):
        # Note that the 'name' property is actually the variable label
        # Be aware that variables marked for deletion, that are hidden from users, have a 'name' that starts with 'DELETE -'
        return self.data["name"]

    @property
    def largest(self):
        if self.cached_content:
            return self.cached_content.get('largest')

    @property
    def name(self):
        # Note that the 'filedName' property is actually the variable name
        # Be aware that compute variables, that are hidden from users, start with :@computed
        return self.data["fieldName"]

    @property
    def non_null(self):
        if self.cached_content and self.cached_content.get('non_null'):
            return int(self.cached_content.get('non_null'))

    @property
    def null(self):
        if self.cached_content and self.cached_content.get('null'):
            return int(self.cached_content.get('null'))

    @property
    def position(self):
        return self.data["position"]

    @property
    def smallest(self):
        if self.cached_content:
            return self.cached_content.get('smallest')

    @property
    def socrata_data_type(self):
        return self.data["dataTypeName"]

    @property
    def generic_data_type(self):
        #TODO: implement
        return None
        
    @property
    def socrata_render_type(self):
        return self.data["renderTypeName"]


    @property
    def top(self):
        if self.cached_content and self.cached_content.get('top'):
            return self.cached_content.get('top')
