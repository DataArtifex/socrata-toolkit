import json


def test_sfo_311(sfo_dataset_311, tmp_path):
    metadata = sfo_dataset_311.get_croissant(max_codes=10)
    assert metadata
    assert metadata.name == sfo_dataset_311.name, "Metadata name doesn't match dataset name"
    assert metadata.id == sfo_dataset_311.id, "Metadata ID doesn't match dataset ID"

    # Verify distribution exists
    assert len(metadata.distribution) > 0, "No distributions found"
    assert metadata.distribution[0].name == sfo_dataset_311.name + ".csv", "Distribution name incorrect"

    # Verify record sets exist
    assert len(metadata.record_sets) > 0, "No record sets found"

    with open(tmp_path / "sfo_311.croissant.json", "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)


def test_nyc_311(nyc_dataset_311, tmp_path):
    metadata = nyc_dataset_311.get_croissant(include_codes=False)  # test no codes
    assert metadata
    assert metadata.name == nyc_dataset_311.name, "Metadata name doesn't match dataset name"

    # When include_codes=False, should only have the main data record set
    assert len(metadata.record_sets) == 1, f"Expected 1 record set, got {len(metadata.record_sets)}"

    with open(tmp_path / "nyc_311.croissant.json", "w") as f:
        json.dump(metadata.to_json(), f, indent=4, default=str)
