
import json
import os
from dartfx.socrata import SocrataServer, SocrataDataset

script_dir = os.path.dirname(__file__)
sfo_server = SocrataServer("data.sfgov.org")
sfo_dataset_311 = SocrataDataset(sfo_server, "vw6y-z8j6")


def test_croissant_sfo_311():
    metadata = sfo_dataset_311.get_croissant()
    assert metadata
    with open(os.path.join(script_dir, "croissant/sfo_311.json"), "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
    print(metadata.issues.report())
