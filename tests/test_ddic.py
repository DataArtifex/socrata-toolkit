import os
from xml.dom import minidom

import pytest
from lxml import etree as ET


@pytest.fixture
def ddi_schema(tests_dir):
    xml_schema_doc = ET.parse(os.path.join(tests_dir, "ddi_2_5_1/schemas", "codebook.xsd"))
    xml_schema = ET.XMLSchema(xml_schema_doc)
    return xml_schema


def test_sfo_311_ddi_codebook(sfo_server, sfo_dataset_311, ddi_schema, tmp_path):
    xml_str = sfo_dataset_311.get_ddi_codebook()
    assert xml_str
    # save to tmp_path (pretty printed)
    with open(tmp_path / "sfo_311.ddic.xml", "w") as f:
        dom = minidom.parseString(xml_str)
        f.write(dom.toprettyxml())
    # validate codebook
    xml_doc = ET.fromstring(xml_str)
    ddi_schema.assertValid(xml_doc)

    # Content verification using XPath
    ns = {"d": "ddi:codebook:2_5"}

    # Verify title is present
    titles = xml_doc.xpath("//d:titlStmt/d:titl/text()", namespaces=ns)
    assert len(titles) > 0, "No title found in DDI codebook"
    assert sfo_dataset_311.name in titles, f"Expected title '{sfo_dataset_311.name}' not found"

    # Verify IDNo is correct
    idnos = xml_doc.xpath("//d:titlStmt/d:IDNo/text()", namespaces=ns)
    expected_id = f"{sfo_server.host}-{sfo_dataset_311.id}"
    assert expected_id in idnos, f"Expected ID '{expected_id}' not found"

    # Verify variables are present
    vars = xml_doc.xpath("//d:dataDscr/d:var", namespaces=ns)
    assert len(vars) > 0, "No variables found in DDI codebook"

    # Verify at least one variable has correct attributes
    var_names = [v.get("name") for v in vars]
    assert len(var_names) > 0, "No variable names found"
    # Check that first visible variable is included
    first_var = next((v for v in sfo_dataset_311.variables if not v.is_hidden), None)
    if first_var:
        assert first_var.name in var_names, f"Expected variable '{first_var.name}' not found"
