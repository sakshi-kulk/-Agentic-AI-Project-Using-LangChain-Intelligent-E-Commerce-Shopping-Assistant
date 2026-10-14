"""Budget validation agent."""

from tools.budget_tool import validate_budget


def run_budget_agent(products: list[dict], budget: float) -> dict[str, dict]:
    return {
        str(product["product_id"]): validate_budget(float(product["price"]), budget)
        for product in products
    }