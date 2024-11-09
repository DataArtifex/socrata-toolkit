
import json
from dartfx.socrata import SocrataServer, SocrataDataset

sfo_server = SocrataServer("data.sfgov.org")
sfo_dataset_311 = SocrataDataset(sfo_server, "vw6y-z8j6")


def test_croissant_sfo_311():
    metadata = sfo_dataset_311.get_croissant()
    assert metadata
    content = metadata.to_json()
    content = json.dumps(content, indent=2)
    print(content)
    print(metadata.issues.report())
