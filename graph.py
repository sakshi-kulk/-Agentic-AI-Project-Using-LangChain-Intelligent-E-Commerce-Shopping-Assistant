"""LangGraph orchestration for the shopping assistant workflow."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.budget_agent import run_budget_agent
from agents.comparison_agent import run_comparison_agent
from agents.faq_agent import run_faq_agent
from agents.inventory_agent import run_inventory_agent
from agents.recommendation_agent import rank_products
from agents.search_agent import extract_requirements
from database import PRODUCTS_PATH
from state import ShoppingState
from tools.cart_tool import add_to_cart
from tools.product_search_tool import search_products


def _append_error(state: ShoppingState, message: str) -> list[str]:
    return [*state.get("errors", []), message]


def search_products_node(state: ShoppingState) -> dict[str, Any]:
    requirement = state.get("customer_requirement", "").strip()
    budget = state.get("budget")
    if not requirement:
        return {"products": [], "requirements": {}, "status": "invalid_input", "errors": _append_error(state, "Enter a shopping requirement.")}
    if budget is None or float(budget) <= 0:
        return {"products": [], "requirements": {}, "status": "invalid_budget", "errors": _append_error(state, "Budget must be greater than zero.")}
    try:
        requirements = extract_requirements(requirement, state.get("preferred_ram", ""))
        products = search_products(
            float(budget),
            requirements["use_case"],
            requirements["preferred_ram"],
            state.get("catalog_path", PRODUCTS_PATH),
        )
        return {"products": products, "requirements": requirements, "status": "search_complete"}
    except Exception as error:
        return {"products": [], "requirements": {}, "status": "error", "errors": _append_error(state, f"Product search failed: {error}")}


def compare_products_node(state: ShoppingState) -> dict[str, Any]:
    try:
        return {"comparison": run_comparison_agent(state.get("products", []))}
    except Exception as error:
        return {"comparison": [], "errors": _append_error(state, f"Product comparison failed: {error}")}


def check_inventory_node(state: ShoppingState) -> dict[str, Any]:
    try:
        return {"inventory": run_inventory_agent(state.get("products", []), state.get("db_path"))}
    except Exception as error:
        return {"inventory": {}, "errors": _append_error(state, f"Inventory check failed: {error}")}


def validate_budget_node(state: ShoppingState) -> dict[str, Any]:
    try:
        results = run_budget_agent(state.get("products", []), float(state.get("budget", 0)))
        return {"budget_validation": results}
    except Exception as error:
        return {"budget_validation": {}, "errors": _append_error(state, f"Budget validation failed: {error}")}


def retrieve_faqs_node(state: ShoppingState) -> dict[str, Any]:
    eligible = [
        product
        for product in state.get("products", [])
        if state.get("inventory", {}).get(str(product["product_id"]), {}).get("available")
        and state.get("budget_validation", {}).get(str(product["product_id"]), {}).get("within_budget")
    ]
    try:
        return {"faq_answers": run_faq_agent(eligible)}
    except Exception as error:
        return {"faq_answers": {}, "errors": _append_error(state, f"FAQ retrieval failed: {error}")}


def generate_recommendation_node(state: ShoppingState) -> dict[str, Any]:
    if state.get("status") in {"invalid_input", "invalid_budget", "error"}:
        return {
            "recommendation": None,
            "recommendation_reason": state.get("errors", ["Shopping request could not be processed."])[-1],
            "status": state["status"],
        }
    winner, reason = rank_products(
        state.get("products", []),
        state.get("inventory", {}),
        state.get("budget_validation", {}),
        state.get("requirements", {}).get("preferred_ram", state.get("preferred_ram", "")),
    )
    status = "recommended" if winner else (
        "no_products" if not state.get("products") else "unavailable"
    )
    return {"recommendation": winner, "recommendation_reason": reason, "status": status}


def cart_confirmation_node(state: ShoppingState) -> dict[str, Any]:
    if not state.get("confirm_add_to_cart"):
        return {"status": "awaiting_confirmation" if state.get("recommendation") else state.get("status", "no_products")}
    selected_id = state.get("selected_product_id")
    product = next(
        (item for item in state.get("products", []) if str(item["product_id"]) == str(selected_id)),
        None,
    )
    if product is None:
        return {"status": "cart_error", "errors": _append_error(state, "Select a matching product before confirming the cart.")}
    if not state.get("inventory", {}).get(str(selected_id), {}).get("available"):
        return {"status": "cart_error", "errors": _append_error(state, "The selected product is out of stock.")}
    if not state.get("budget_validation", {}).get(str(selected_id), {}).get("within_budget"):
        return {"status": "cart_error", "errors": _append_error(state, "The selected product exceeds your budget.")}
    return {"status": "confirmation_received", "selected_product_id": str(selected_id)}


def add_to_cart_node(state: ShoppingState) -> dict[str, Any]:
    product = next(
        (item for item in state.get("products", []) if str(item["product_id"]) == str(state.get("selected_product_id"))),
        None,
    )
    if not product:
        return {"status": "cart_error", "errors": _append_error(state, "Selected product could not be found.")}
    try:
        cart = add_to_cart(product, confirmed=True, db_path=state.get("db_path"))
        return {"cart": cart, "status": "cart_added"}
    except Exception as error:
        return {"status": "cart_error", "errors": _append_error(state, f"Cart creation failed: {error}")}


def _route_after_search(state: ShoppingState) -> str:
    return "compare_products" if state.get("products") else "generate_recommendation"


def _route_after_confirmation(state: ShoppingState) -> str:
    if state.get("confirm_add_to_cart") and state.get("status") == "confirmation_received":
        return "add_to_cart"
    return END


def build_graph():
    workflow = StateGraph(ShoppingState)
    workflow.add_node("search_products", search_products_node)
    workflow.add_node("compare_products", compare_products_node)
    workflow.add_node("check_inventory", check_inventory_node)
    workflow.add_node("validate_budget", validate_budget_node)
    workflow.add_node("retrieve_faqs", retrieve_faqs_node)
    workflow.add_node("generate_recommendation", generate_recommendation_node)
    workflow.add_node("cart_confirmation", cart_confirmation_node)
    workflow.add_node("add_to_cart", add_to_cart_node)
    workflow.add_edge(START, "search_products")
    workflow.add_conditional_edges(
        "search_products",
        _route_after_search,
        {"compare_products": "compare_products", "generate_recommendation": "generate_recommendation"},
    )
    workflow.add_edge("compare_products", "check_inventory")
    workflow.add_edge("check_inventory", "validate_budget")
    workflow.add_edge("validate_budget", "retrieve_faqs")
    workflow.add_edge("retrieve_faqs", "generate_recommendation")
    workflow.add_edge("generate_recommendation", "cart_confirmation")
    workflow.add_conditional_edges(
        "cart_confirmation",
        _route_after_confirmation,
        {"add_to_cart": "add_to_cart", END: END},
    )
    workflow.add_edge("add_to_cart", END)
    return workflow.compile()


shopping_graph = build_graph()


def run_shopping_workflow(
    customer_requirement: str,
    budget: float,
    preferred_ram: str = "",
    confirm_add_to_cart: bool = False,
    selected_product_id: str | None = None,
    db_path: str | None = None,
    catalog_path: str | None = None,
) -> ShoppingState:
    initial_state: ShoppingState = {
        "customer_requirement": customer_requirement,
        "budget": budget,
        "preferred_ram": preferred_ram,
        "confirm_add_to_cart": confirm_add_to_cart,
        "selected_product_id": selected_product_id,
        "db_path": db_path,
        "errors": [],
    }
    if catalog_path:
        initial_state["catalog_path"] = catalog_path
    return shopping_graph.invoke(initial_state)