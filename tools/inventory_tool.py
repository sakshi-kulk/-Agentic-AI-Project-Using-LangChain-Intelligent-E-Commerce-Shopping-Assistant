"""Read current stock from SQLite inventory."""

from pathlib import Path

from database import get_stock


def check_inventory(product_id: str, db_path: str | Path | None = None) -> dict:
    if not product_id.strip():
        raise ValueError("Product ID is required.")
    stock = get_stock(product_id, db_path)
    return {"available": stock > 0, "stock": stock}