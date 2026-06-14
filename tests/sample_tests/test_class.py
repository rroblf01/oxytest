class TestMath:
    def test_addition(self):
        assert 1 + 2 == 3

    def test_subtraction(self):
        assert 5 - 3 == 2

    def test_multiplication(self):
        assert 3 * 4 == 12

    def test_division(self):
        assert 10 / 2 == 5


class TestString:
    def test_upper(self):
        assert "foo".upper() == "FOO"

    def test_lower(self):
        assert "BAR".lower() == "bar"

    def test_strip(self):
        assert "  hello  ".strip() == "hello"


class TestComplexSetup:
    def test_with_setup(self):
        data = list(range(100))
        assert len(data) == 100
        assert sum(data) == 4950
