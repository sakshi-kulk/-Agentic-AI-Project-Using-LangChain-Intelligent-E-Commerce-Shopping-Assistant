"""LangGraph state shared by the shopping workflow nodes."""

from typing import Any, TypedDict


class ShoppingState(TypedDict, total=False):
    customer_requirement: str
    budget: float
    preferred_ram: str
    requirements: dict[str, Any]
    products: list[dict[str, Any]]
    comparison: list[dict[str, Any]]
    inventory: dict[str, dict[str, Any]]
    budget_validation: dict[str, dict[str, Any]]
    faq_answers: dict[str, str]
    recommendation: dict[str, Any] | None
    recommendation_reason: str
    status: str
    errors: list[str]
    confirm_add_to_cart: bool
    selected_product_id: str | None
    cart: dict[str, Any] | None
    db_path: str | None