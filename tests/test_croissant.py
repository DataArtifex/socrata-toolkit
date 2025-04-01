
import json
import os
from dartfx.socrata import SocrataServer, SocrataDataset

sfo_server = SocrataServer(host="data.sfgov.org")
sfo_dataset_311 = SocrataDataset(server=sfo_server, id="vw6y-z8j6")

nyc_server= SocrataServer(host="data.cityofnewyork.us")
nyc_dataset_311 = SocrataDataset(server=nyc_server, id="vfnx-vebw")

def test_sfo_311(tests_dir):
    metadata = sfo_dataset_311.get_croissant()
    assert metadata
    with open(os.path.join(tests_dir, "sfo_311.croissant.json"), "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
    print(metadata.issues.report())

def test_nyc_311(tests_dir):
    metadata = nyc_dataset_311.get_croissant()
    assert metadata
    with open(os.path.join(tests_dir, "nyc_311.croissant.json"), "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
    print(metadata.issues.report())
