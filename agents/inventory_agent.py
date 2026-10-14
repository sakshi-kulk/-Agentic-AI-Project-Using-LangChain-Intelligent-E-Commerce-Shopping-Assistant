"""Inventory availability agent."""

from pathlib import Path

from tools.inventory_tool import check_inventory


def run_inventory_agent(
    products: list[dict], db_path: str | Path | None = None
) -> dict[str, dict]:
    return {
        str(product["product_id"]): check_inventory(str(product["product_id"]), db_path)
        for product in products
    }