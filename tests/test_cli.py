import json
from pathlib import Path

from typer.testing import CliRunner

from dartfx.socrata.__about__ import __version__
from dartfx.socrata.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
    assert "dartfx-socrata version:" in result.stdout


def test_cli_servers_table() -> None:
    result = runner.invoke(app, ["servers"])
    assert result.exit_code == 0
    assert "data.sfgov.org" in result.stdout
    assert "San Francisco" in result.stdout


def test_cli_servers_filter() -> None:
    result = runner.invoke(app, ["servers", "-q", "calgary"])
    assert result.exit_code == 0
    assert "data.calgary.ca" in result.stdout
    assert "data.sfgov.org" not in result.stdout


def test_cli_servers_json() -> None:
    result = runner.invoke(app, ["servers", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    hosts = [item["hostname"] for item in data]
    assert "data.sfgov.org" in hosts


def test_cli_servers_csv() -> None:
    result = runner.invoke(app, ["servers", "--format", "csv"])
    assert result.exit_code == 0
    assert "hostname,name,publisher,spatial,url" in result.stdout
    assert "data.sfgov.org" in result.stdout


def test_cli_servers_markdown() -> None:
    result = runner.invoke(app, ["servers", "--markdown"])
    assert result.exit_code == 0
    assert "| Portal Name | Hostname | Publisher | Spatial Coverage |" in result.stdout
    assert "data.sfgov.org" in result.stdout


def test_cli_servers_output_file(tmp_path: Path) -> None:
    out_file = tmp_path / "servers.json"
    result = runner.invoke(app, ["servers", "--json", "-o", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert isinstance(data, list)


def test_cli_info() -> None:
    result = runner.invoke(app, ["info", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "San Francisco" in result.stdout
    assert "Online" in result.stdout


def test_cli_info_json() -> None:
    result = runner.invoke(app, ["info", "data.sfgov.org", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["hostname"] == "data.sfgov.org"
    assert data["online"] is True
    assert data["total_datasets"] == 1


def test_cli_search_table() -> None:
    result = runner.invoke(app, ["search", "cases", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "vw6y-z8j6" in result.stdout
    assert "311 Cases" in result.stdout


def test_cli_search_json() -> None:
    result = runner.invoke(app, ["search", "cases", "--json", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "results" in data
    assert data["resultSetSize"] == 1


def test_cli_search_csv() -> None:
    result = runner.invoke(app, ["search", "cases", "--format", "csv", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "id,name,category,views,updated,description,permalink" in result.stdout
    assert "vw6y-z8j6" in result.stdout


def test_cli_search_markdown() -> None:
    result = runner.invoke(app, ["search", "cases", "--md", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "vw6y-z8j6" in result.stdout
    assert "| ID | Title / Dataset | Category | Views | Updated |" in result.stdout


def test_cli_dataset_table() -> None:
    result = runner.invoke(app, ["dataset", "vw6y-z8j6", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "311 Cases" in result.stdout
    assert "Columns / Variables for vw6y-z8j6" in result.stdout


def test_cli_dataset_json() -> None:
    result = runner.invoke(app, ["dataset", "vw6y-z8j6", "--json", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data.get("id") == "vw6y-z8j6"
    assert "columns" in data


def test_cli_dataset_markdown() -> None:
    result = runner.invoke(app, ["dataset", "vw6y-z8j6", "--markdown", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "# 311 Cases" in result.stdout


def test_cli_dataset_alias_show() -> None:
    result = runner.invoke(app, ["show", "vw6y-z8j6", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "311 Cases" in result.stdout


def test_cli_variables_table() -> None:
    result = runner.invoke(app, ["variables", "vw6y-z8j6", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "CaseID" in result.stdout
    assert "Variables Schema" in result.stdout


def test_cli_variables_json() -> None:
    result = runner.invoke(app, ["variables", "vw6y-z8j6", "--json", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    field_names = [v["field_name"] for v in data]
    assert "service_request_id" in field_names


def test_cli_variables_csv() -> None:
    result = runner.invoke(app, ["variables", "vw6y-z8j6", "--format", "csv", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "position,field_name,label,data_type" in result.stdout
    assert "service_request_id" in result.stdout


def test_cli_variables_markdown() -> None:
    result = runner.invoke(app, ["variables", "vw6y-z8j6", "--markdown", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "Variables for Dataset" in result.stdout
    assert "`service_request_id`" in result.stdout


def test_cli_variables_include_hidden() -> None:
    result = runner.invoke(app, ["variables", "vw6y-z8j6", "--include-hidden", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert ":@comp" in result.stdout
    assert "Variables Schema" in result.stdout


def test_cli_export_dcat_turtle() -> None:
    result = runner.invoke(app, ["export", "vw6y-z8j6", "-f", "dcat", "-r", "turtle", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "@prefix dcat:" in result.stdout or "dcat:Dataset" in result.stdout or "dcat:Catalog" in result.stdout


def test_cli_export_dcat_file(tmp_path: Path) -> None:
    out_file = tmp_path / "catalog.ttl"
    result = runner.invoke(app, ["export", "vw6y-z8j6", "-f", "dcat", "-o", str(out_file), "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "dcat:Dataset" in content or "dcat:Catalog" in content


def test_cli_export_croissant() -> None:
    result = runner.invoke(app, ["export", "vw6y-z8j6", "-f", "croissant", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data.get("@type") == "sc:Dataset" or "recordSet" in data or "name" in data


def test_cli_export_ddi() -> None:
    result = runner.invoke(app, ["export", "vw6y-z8j6", "-f", "ddi", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "<codeBook" in result.stdout
    assert "</codeBook>" in result.stdout


def test_cli_export_markdown() -> None:
    result = runner.invoke(app, ["export", "vw6y-z8j6", "-f", "markdown", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "# 311 Cases" in result.stdout


def test_cli_export_json() -> None:
    result = runner.invoke(app, ["export", "vw6y-z8j6", "-f", "json", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data.get("id") == "vw6y-z8j6"


def test_cli_code_python() -> None:
    result = runner.invoke(app, ["code", "vw6y-z8j6", "-e", "python", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "pandas" in result.stdout
    assert "sodapy" in result.stdout
    assert "vw6y-z8j6" in result.stdout


def test_cli_code_r() -> None:
    result = runner.invoke(app, ["code", "vw6y-z8j6", "-e", "r", "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert "RSocrata" in result.stdout or "read.socrata" in result.stdout


def test_cli_code_file(tmp_path: Path) -> None:
    out_script = tmp_path / "fetch.py"
    result = runner.invoke(app, ["code", "vw6y-z8j6", "-e", "python", "-o", str(out_script), "-s", "data.sfgov.org"])
    assert result.exit_code == 0
    assert out_script.exists()
    assert "pandas" in out_script.read_text()


def test_cli_code_invalid_env() -> None:
    result = runner.invoke(app, ["code", "vw6y-z8j6", "-e", "cobol", "-s", "data.sfgov.org"])
    assert result.exit_code != 0
    assert "Unknown environment 'cobol'" in result.stdout


def test_cli_dataset_not_found() -> None:
    result = runner.invoke(app, ["dataset", "non-existent-id", "-s", "data.sfgov.org"])
    assert result.exit_code != 0
    assert "Error fetching dataset" in result.stdout
