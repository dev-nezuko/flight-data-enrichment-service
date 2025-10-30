import math
from typing import Any


def extract_retail_price(data: dict[str, Any]) -> float | None:
    """Return the first best_flights price, None when absent, or raise ValueError if invalid."""
    best_flights = data.get("best_flights") or []
    if not best_flights:
        return None

    price = best_flights[0].get("price")
    if price is None:
        return None
    if isinstance(price, bool):
        raise ValueError("Failed to extract retail price: price must be numeric")
    try:
        value = float(price)
    except (TypeError, ValueError):
        raise ValueError(f"Failed to extract retail price: {price!r} is not numeric") from None
    if not math.isfinite(value) or value < 0:
        raise ValueError("Failed to extract retail price: price must be finite and nonnegative")
    return value
