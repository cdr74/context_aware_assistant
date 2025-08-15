class Calculator:
    """A simple calculator supporting basic and advanced operations."""

    def add(self, a: float, b: float) -> float:
        return a + b

    def subtract(self, a: float, b: float) -> float:
        return a - b

    def multiply(self, a: float, b: float) -> float:
        return a * b

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        return a / b

    def power(self, a: float, b: float) -> float:
        """Raise a to the power of b."""
        return a ** b
