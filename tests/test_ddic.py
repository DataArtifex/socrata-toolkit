from dartfx.socrata import SocrataServer, SocrataDataset
from lxml import etree as ET
import pytest
import os
from xml.dom import minidom

sfo_server = SocrataServer("data.sfgov.org")
sfo_dataset_311 = SocrataDataset(sfo_server, "vw6y-z8j6")

@pytest.fixture
def ddi_schema(tests_dir):
    xml_schema_doc = ET.parse(os.path.join(tests_dir, 'ddi_2_5_1/schemas','codebook.xsd'))
    xml_schema = ET.XMLSchema(xml_schema_doc)
    return xml_schema

def test_sfo_311_ddi_codebook(tests_dir, ddi_schema):
    xml_str = sfo_dataset_311.get_ddi_codebook()
    assert xml_str
    # save to file (pretty printed)
    with open(os.path.join(tests_dir, 'vw6y-z8j6.ddic.xml'),'w') as f:
        dom = minidom.parseString(xml_str)
        f.write(dom.toprettyxml())
    # validate codebook
    xml_doc = ET.fromstring(xml_str)
    ddi_schema.assertValid(xml_doc)
    
