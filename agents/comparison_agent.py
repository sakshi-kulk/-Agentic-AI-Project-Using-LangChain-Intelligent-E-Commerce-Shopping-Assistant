"""Product comparison agent."""

from tools.comparison_tool import compare_products


def run_comparison_agent(products: list[dict]) -> list[dict]:
    return compare_products(products).to_dict(orient="records")