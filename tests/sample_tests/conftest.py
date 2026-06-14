import oxytest as pytest


@pytest.fixture
def sample_data():
    return {"key": "value", "numbers": [1, 2, 3]}


@pytest.fixture
def counter():
    return iter(range(100))
