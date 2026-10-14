"""Search the local product catalog using budget, use case, and RAM."""

from pathlib import Path

import pandas as pd

from database import PRODUCTS_PATH


def search_products(
    budget: float,
    use_case: str = "",
    preferred_ram: str = "",
    catalog_path: str | Path = PRODUCTS_PATH,
) -> list[dict]:
    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")
    products = pd.read_csv(catalog_path)
    if products.empty:
        return []
    matches = products.loc[
        (products["category"].str.casefold() == "laptop")
        & (pd.to_numeric(products["price"], errors="coerce") <= float(budget))
    ].copy()
    if preferred_ram:
        ram_gb = "".join(character for character in preferred_ram if character.isdigit())
        if ram_gb:
            matches = matches.loc[
                matches["ram"].astype(str).str.extract(r"(\d+)", expand=False) == ram_gb
            ]
    # The catalog contains laptops only; use-case intent is ranked downstream.
    return matches.sort_values(["rating", "price"], ascending=[False, True]).to_dict(
        orient="records"
    )