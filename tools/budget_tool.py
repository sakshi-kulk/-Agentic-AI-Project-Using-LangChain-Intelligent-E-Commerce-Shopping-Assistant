"""Validate product prices against a customer's stated budget."""


def validate_budget(price: float, budget: float) -> dict:
    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")
    if price < 0:
        raise ValueError("Product price cannot be negative.")
    return {"within_budget": float(price) <= float(budget), "price": float(price)}