from dartfx.socrata import SocrataServer, SocrataDataset


sfo_server = SocrataServer("data.sfgov.org")

sfo_dataset_311 = SocrataDataset(sfo_server, "vw6y-z8j6")

def test_jquery_sfo_311():
    code = sfo_dataset_311.get_code("jquery")
    assert code

def test_powershell_sfo_311():
    code = sfo_dataset_311.get_code("powershell")
    assert code

def test_python_pandas_sfo_311():
    code = sfo_dataset_311.get_code("python-pandas")
    assert code

def test_sas_sfo_311():
    code = sfo_dataset_311.get_code("sas")
    assert code

def test_soda_ruby_sfo_311():
    code = sfo_dataset_311.get_code("soda-ruby")
    assert code

def test_soda_dotnet_sfo_311():
    code = sfo_dataset_311.get_code("soda-dotnet")
    assert code

def test_soda_dotnet_stata_311():
    code = sfo_dataset_311.get_code("soda-stata")
    assert code
