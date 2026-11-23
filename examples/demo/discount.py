def discount_price(price: float, discount_percent: float) -> float:
    """Return the price after applying a percentage discount."""
    # Intentional defect: subtracting 10 is not the same as applying 10 percent.
    return price - discount_percent
