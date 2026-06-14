def test_pass():
    assert 1 + 1 == 2

def test_fail():
    assert 2 + 2 == 4

def test_with_output():
    print("Hello from test!")
    assert True

def test_string():
    assert "hello".upper() == "HELLO"

def test_math():
    assert abs(-5) == 5
    assert pow(2, 3) == 8

def test_list():
    items = [1, 2, 3]
    assert len(items) == 3
    assert items[0] == 1
    assert items[-1] == 3

def test_dict():
    d = {"a": 1, "b": 2}
    assert d["a"] == 1
    assert d.get("c", 3) == 3

def test_slow():
    import time
    time.sleep(0.05)
    assert True

def test_error():
    pass  # This test passes, error test is separate
