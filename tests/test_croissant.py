
import json
import os
from dartfx.socrata import SocrataServer, SocrataDataset

sfo_server = SocrataServer(host="data.sfgov.org")
sfo_dataset_311 = SocrataDataset(server=sfo_server, id="vw6y-z8j6")

nyc_server= SocrataServer(host="data.cityofnewyork.us")
nyc_dataset_311 = SocrataDataset(server=nyc_server, id="vfnx-vebw")

def test_sfo_311(tests_dir):
    metadata = sfo_dataset_311.get_croissant(max_codes=10)
    assert metadata
    assert metadata.name == sfo_dataset_311.name, "Metadata name doesn't match dataset name"
    assert metadata.id == sfo_dataset_311.id, "Metadata ID doesn't match dataset ID"
    
    # Verify distribution exists
    assert len(metadata.distribution) > 0, "No distributions found"
    assert metadata.distribution[0].name == sfo_dataset_311.name + '.csv', "Distribution name incorrect"
    
    # Verify record sets exist
    assert len(metadata.record_sets) > 0, "No record sets found"
    
    with open(os.path.join(tests_dir, "sfo_311.croissant.json"), "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
    print(metadata.issues.report())

def test_nyc_311(tests_dir):
    metadata = nyc_dataset_311.get_croissant(include_codes=False) # test no codes
    assert metadata
    assert metadata.name == nyc_dataset_311.name, "Metadata name doesn't match dataset name"
    
    # When include_codes=False, should only have the main data record set
    assert len(metadata.record_sets) == 1, f"Expected 1 record set, got {len(metadata.record_sets)}"
    
    with open(os.path.join(tests_dir, "nyc_311.croissant.json"), "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
    print(metadata.issues.report())
