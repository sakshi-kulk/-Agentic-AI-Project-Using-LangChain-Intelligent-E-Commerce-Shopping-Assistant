"""Build a presentation-ready comparison of product specifications."""

import pandas as pd


COMPARISON_COLUMNS = [
    "product_name",
    "price",
    "processor",
    "ram",
    "storage",
    "battery_life",
    "rating",
]


def compare_products(products: list[dict]) -> pd.DataFrame:
    if not products:
        return pd.DataFrame(columns=COMPARISON_COLUMNS)
    missing = set(COMPARISON_COLUMNS) - set(products[0])
    if missing:
        raise ValueError(f"Products are missing comparison fields: {', '.join(sorted(missing))}")
    return pd.DataFrame(products)[COMPARISON_COLUMNS].reset_index(drop=True)