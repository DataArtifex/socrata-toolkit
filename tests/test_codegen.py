from dartfx.socrata import SocrataServer, SocrataDataset
import os
import pytest

sfo_server = SocrataServer(host="data.sfgov.org")

sfo_dataset_311 = SocrataDataset(server=sfo_server, id="vw6y-z8j6")

def test_jquery_sfo_311(tests_dir):
    code = sfo_dataset_311.get_code("jquery")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(os.path.join(tests_dir, "sfo_311_jquery.js"), "w") as f:
        f.write(code)

def test_powershell_sfo_311(tests_dir):
    code = sfo_dataset_311.get_code("powershell")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(os.path.join(tests_dir, "sfo_311_powershell.ps1"), "w") as f:
        f.write(code)

def test_python_pandas_sfo_311(tests_dir):
    code = sfo_dataset_311.get_code("python-pandas")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(os.path.join(tests_dir, "sfo_311_python-pandas.py"), "w") as f:
        f.write(code)

def test_sas_sfo_311(tests_dir):
    code = sfo_dataset_311.get_code("sas")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(os.path.join(tests_dir, "sfo_311_sas.sas"), "w") as f:
        f.write(code)

def test_soda_ruby_sfo_311(tests_dir):
    code = sfo_dataset_311.get_code("soda-ruby")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(os.path.join(tests_dir, "sfo_311_soda-ruby.rb"), "w") as f:
        f.write(code)

def test_soda_dotnet_sfo_311(tests_dir):
    code = sfo_dataset_311.get_code("soda-dotnet")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(os.path.join(tests_dir, "sfo_311_soda-dotnet.cs"), "w") as f:
        f.write(code)

def test_soda_dotnet_stata_311(tests_dir):
    code = sfo_dataset_311.get_code("stata")
    assert code
    assert sfo_server.host in code, f"Host '{sfo_server.host}' not found in generated code"
    assert sfo_dataset_311.id in code, f"Dataset ID '{sfo_dataset_311.id}' not found in generated code"
    with open(os.path.join(tests_dir, "sfo_311_stata.do"), "w") as f:
        f.write(code)

def test_unsupported_environment():
    """Test that unsupported code generation environments raise appropriate errors."""
    with pytest.raises(ValueError, match="Unsupported environment"):
        sfo_dataset_311.get_code("non-existent-language")
