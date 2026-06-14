import oxytest as pytest

def test_with_params():
    params = [1, 2, 3, 4, 5]
    for p in params:
        assert p > 0

@pytest.mark.parametrize("input_val,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (10, 20),
])
def test_double(input_val, expected):
    assert input_val * 2 == expected

@pytest.mark.parametrize("text,length", [
    ("hello", 5),
    ("world!", 6),
    ("", 0),
])
def test_length(text, length):
    assert len(text) == length
