collect_ignore = ["../conftest.py"]

def pytest_ignore_collect(collection_path, config):
    if collection_path.name == "conftest.py" and collection_path.parent.name != "capacity":
        return True
    return False
