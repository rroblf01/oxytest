import oxytest as pytest

pytestmark = pytest.mark.xfail()

def test_assert_eq():
    x = 1
    y = 2
    assert x == y

def test_assert_in():
    items = [1, 2, 3]
    assert 5 in items

def test_assert_is():
    a = None
    assert a is not None

def test_assert_not_eq():
    a = 10
    b = 10
    assert a != b

def test_assert_lt():
    a = 5
    b = 3
    assert a < b

def test_assert_gt():
    a = 2
    b = 10
    assert a > b

def test_raise_value_error():
    raise ValueError("something went wrong")

def test_raise_type_error():
    raise TypeError("bad type")

def test_complex_expression():
    result = [1, 2, 3]
    expected = [1, 2, 4]
    assert result == expected
