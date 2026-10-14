"""Explicitly confirmed, simulated cart operations."""

from pathlib import Path
from typing import Any

from database import add_product_to_cart


def add_to_cart(
    product: dict[str, Any],
    confirmed: bool,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    if not confirmed:
        raise PermissionError("Customer confirmation is required before adding to cart.")
    return add_product_to_cart(product, db_path)