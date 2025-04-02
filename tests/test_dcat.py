
import os
from dartfx.socrata import SocrataServer, SocrataDataset, DcatGenerator

sfo_server = SocrataServer(host="data.sfgov.org")
sfo_dataset_311 = SocrataDataset(server=sfo_server, id="vw6y-z8j6")

def test_sfo_311(tests_dir):
    generator = DcatGenerator(sfo_server)
    generator.add_dataset(sfo_dataset_311)
    print(generator.datasets)
    g = generator.get_graph()
    assert g
    g.serialize(destination=os.path.join(tests_dir, "sfo_311.dcat.ttl"), format="ttl")

