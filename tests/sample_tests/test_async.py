import oxytest as pytest


async def test_async_basic():
    result = await async_add(1, 2)
    assert result == 3


async def test_async_fail():
    result = await async_add(5, 5)
    assert result == 10


async def test_async_string():
    value = await async_upper("hello")
    assert value == "HELLO"


async def test_async_list():
    items = await async_get_items()
    assert len(items) == 3
    assert items[0] == "a"


async def test_async_nested():
    result = await async_add(await async_add(1, 2), 3)
    assert result == 6


class TestAsyncClass:
    async def test_async_method(self):
        result = await async_add(10, 20)
        assert result == 30

    async def test_another_method(self):
        value = await async_upper("world")
        assert value == "WORLD"


async def async_add(a, b):
    return a + b


async def async_upper(s):
    return s.upper()


async def async_get_items():
    return ["a", "b", "c"]


@pytest.fixture
async def async_data():
    result = await async_get_items()
    return result


async def test_with_async_fixture(async_data):
    assert async_data == ["a", "b", "c"]
    assert len(async_data) == 3


@pytest.fixture
async def async_gen_data():
    items = await async_get_items()
    yield items


async def test_with_async_gen_fixture(async_gen_data):
    assert async_gen_data == ["a", "b", "c"]
