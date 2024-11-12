
import json
import os
from dartfx.socrata import SocrataServer, SocrataDataset

script_dir = os.path.dirname(__file__)
sfo_server = SocrataServer("data.sfgov.org")
sfo_dataset_311 = SocrataDataset(sfo_server, "vw6y-z8j6")

nyc_server= SocrataServer("data.cityofnewyork.us")
nyc_dataset_311 = SocrataDataset(nyc_server, "vfnx-vebw")


def test_sfo_311():
    metadata = sfo_dataset_311.get_croissant()
    assert metadata
    with open(os.path.join(script_dir, "croissant/sfo_311.json"), "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
    print(metadata.issues.report())

def test_nyc_311():
    metadata = nyc_dataset_311.get_croissant()
    assert metadata
    with open(os.path.join(script_dir, "croissant/nyc_311.json"), "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
    print(metadata.issues.report())
