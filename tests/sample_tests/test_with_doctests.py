def add(a: int, b: int) -> int:
    """Return the sum of a and b.

    >>> add(1, 2)
    3
    >>> add(-1, 1)
    0
    """
    return a + b


class Calculator:
    """A simple calculator with doctests.

    >>> Calculator().mul(3, 4)
    12
    """

    def mul(self, a: int, b: int) -> int:
        """Multiply a and b.

        >>> Calculator().mul(5, 6)
        30
        """
        return a * b
