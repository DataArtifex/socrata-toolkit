import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

from dartfx.socrata import SocrataDataset, SocrataServer


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv_path = Path(__file__).parent / "../.env"
    load_dotenv(dotenv_path=dotenv_path)


@pytest.fixture(scope="session")
def tests_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture(scope="session")
def fixtures_dir(tests_dir: Path) -> Path:
    return tests_dir / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def mock_socrata_network(fixtures_dir: Path):
    """Fallback network mock to guarantee tests never fail due to offline/sandboxed environments."""
    original_get = None

    def mock_get(url, *args, **kwargs):
        for dataset_id in ["vw6y-z8j6", "vfnx-vebw", "wg3w-h783"]:
            if f"/api/views/{dataset_id}" in url:
                fixture_file = fixtures_dir / f"{dataset_id}.json"
                if fixture_file.exists():
                    mock_resp = MagicMock()
                    mock_resp.status_code = 200
                    with open(fixture_file) as f:
                        mock_resp.json.return_value = json.load(f)
                    mock_resp.text = fixture_file.read_text()
                    return mock_resp
        if "/api/catalog/v1" in url:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            catalog_data = {
                "results": [
                    {
                        "resource": {
                            "id": "vw6y-z8j6",
                            "name": "311 Cases",
                            "description": "311 Cases in San Francisco",
                            "updatedAt": "2024-01-01T00:00:00.000Z",
                            "createdAt": "2016-01-01T00:00:00.000Z",
                            "page_views": {"page_views_total": 54200},
                            "type": "dataset",
                        },
                        "classification": {
                            "domain_category": "City Infrastructure",
                            "categories": ["Infrastructure"],
                            "domain_tags": ["311", "cases", "service"],
                        },
                        "metadata": {"domain": "data.sfgov.org"},
                        "permalink": "https://data.sfgov.org/d/vw6y-z8j6",
                    }
                ],
                "resultSetSize": 1,
            }
            mock_resp.json.return_value = catalog_data
            mock_resp.text = json.dumps(catalog_data)
            return mock_resp
        if original_get:
            return original_get(url, *args, **kwargs)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        return mock_resp

    with patch("requests.get", side_effect=mock_get):
        yield


@pytest.fixture(scope="session")
def sfo_server(fixtures_dir: Path) -> SocrataServer:
    return SocrataServer(host="data.sfgov.org", disk_cache_dir=str(fixtures_dir))


@pytest.fixture(scope="session")
def nyc_server(fixtures_dir: Path) -> SocrataServer:
    return SocrataServer(host="data.cityofnewyork.us", disk_cache_dir=str(fixtures_dir))


@pytest.fixture(scope="session")
def sfo_dataset_311(sfo_server: SocrataServer) -> SocrataDataset:
    return SocrataDataset(server=sfo_server, id="vw6y-z8j6")


@pytest.fixture(scope="session")
def sfo_dataset_police(sfo_server: SocrataServer) -> SocrataDataset:
    return SocrataDataset(server=sfo_server, id="wg3w-h783")


@pytest.fixture(scope="session")
def nyc_dataset_311(nyc_server: SocrataServer) -> SocrataDataset:
    return SocrataDataset(server=nyc_server, id="vfnx-vebw")
