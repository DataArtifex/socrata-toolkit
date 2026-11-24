import pytest


def test_jquery_sfo_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("jquery")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(tmp_path / "sfo_311_jquery.js", "w") as f:
        f.write(code)


def test_powershell_sfo_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("powershell")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(tmp_path / "sfo_311_powershell.ps1", "w") as f:
        f.write(code)


def test_python_pandas_sfo_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("python-pandas")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(tmp_path / "sfo_311_python-pandas.py", "w") as f:
        f.write(code)


def test_sas_sfo_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("sas")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(tmp_path / "sfo_311_sas.sas", "w") as f:
        f.write(code)


def test_soda_ruby_sfo_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("soda-ruby")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(tmp_path / "sfo_311_soda-ruby.rb", "w") as f:
        f.write(code)


def test_soda_dotnet_sfo_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("soda-dotnet")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(tmp_path / "sfo_311_soda-dotnet.cs", "w") as f:
        f.write(code)


def test_soda_dotnet_stata_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("stata")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    assert "\n. import delimited" not in code
    with open(tmp_path / "sfo_311_stata.do", "w") as f:
        f.write(code)


def test_r_socrata_sfo_311(sfo_dataset_311, sfo_server, tmp_path):
    code = sfo_dataset_311.get_code("r")
    assert "RSocrata" in code
    assert sfo_server.host in code
    assert sfo_dataset_311.id in code
    with open(tmp_path / "sfo_311_r.R", "w") as f:
        f.write(code)


@pytest.mark.parametrize(
    ("env", "expected_marker"),
    [
        ("polars", "import polars as pl"),
        ("requests", "requests.get("),
        ("curl", "curl -sS"),
        ("javascript", "await fetch("),
        ("duckdb", "read_csv("),
    ],
)
def test_new_codegen_environments(sfo_dataset_311, sfo_server, env, expected_marker):
    code = sfo_dataset_311.get_code(
        env,
        options={"limit": 100, "where": "status='Open'", "select": "case_id,status"},
    )
    assert sfo_server.host in code
    assert sfo_dataset_311.id in code
    assert expected_marker in code
    assert "100" in code


def test_codegen_bug_fixes(sfo_dataset_311):
    pandas_code = sfo_dataset_311.get_code("python-pandas")
    assert "{host}" not in pandas_code

    ruby_code = sfo_dataset_311.get_code("soda-ruby")
    assert "#{k}: #{v}" in ruby_code
    assert "#{key}" not in ruby_code

    sas_code = sfo_dataset_311.get_code("sas")
    assert f"https://{sfo_dataset_311.server.host}" in sas_code


def test_unsupported_environment(sfo_dataset_311):
    """Test that unsupported code generation environments raise appropriate errors."""
    with pytest.raises(ValueError, match="Unsupported environment"):
        sfo_dataset_311.get_code("non-existent-language")
