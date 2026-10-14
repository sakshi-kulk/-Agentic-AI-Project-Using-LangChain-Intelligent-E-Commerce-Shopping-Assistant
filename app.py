"""Streamlit interface for the agentic shopping assistant."""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agents.comparison_agent import run_comparison_agent
from database import get_cart_items, get_database_path, initialize_database
from graph import run_shopping_workflow


load_dotenv()
st.set_page_config(page_title="AI Shopping Assistant", page_icon="🛍️", layout="wide")
st.markdown(
    """
    <style>
    :root { --ink: #172e26; --leaf: #17694d; --lime: #dff26a; --paper: #f5f7f1; --coral: #e66b4e; }
    .stApp { background: radial-gradient(ellipse at 94% 2%, #e5efcf 0, transparent 32%), var(--paper); color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }
    h1, h2, h3 { color: var(--ink); }
    .eyebrow { color: var(--leaf); font-size: .76rem; font-weight: 700; text-transform: uppercase; }
    .recommendation { padding: 1.2rem 1.4rem; border-left: 5px solid var(--coral); background: #fff; border-radius: 3px; }
    .stButton > button[kind="primary"] { background: var(--leaf); border-color: var(--leaf); }
    div[data-testid="stMetric"] { background: #fff; padding: .8rem; border-radius: 4px; border-bottom: 2px solid var(--lime); }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    initialize_database()
except Exception as error:
    st.error(f"Could not initialize the local catalog database: {error}")
    st.stop()

st.markdown('<div class="eyebrow">Local catalog · Simulated checkout</div>', unsafe_allow_html=True)
st.title("AI Shopping Assistant")
st.caption("Compare real catalog data against your needs. Listings and cart actions are illustrative only.")

with st.form("shopping_request"):
    requirement = st.text_area(
        "Shopping requirement",
        value="I need a laptop for Python programming, machine learning basics, and online classes. I prefer 16GB RAM and good battery life.",
        height=100,
    )
    budget_col, ram_col = st.columns(2)
    budget = budget_col.number_input("Budget (₹)", min_value=1, value=60000, step=1000)
    preferred_ram = ram_col.selectbox("Preferred RAM", ["16GB", "8GB", "32GB", "No preference"])
    submitted = st.form_submit_button("Search products", type="primary", use_container_width=True)

if submitted:
    if not requirement.strip():
        st.error("Enter a shopping requirement before searching.")
    else:
        with st.spinner("Searching, checking stock, and ranking suitable laptops..."):
            try:
                result = run_shopping_workflow(
                    requirement,
                    float(budget),
                    "" if preferred_ram == "No preference" else preferred_ram,
                    db_path=str(get_database_path()),
                )
                st.session_state["shopping_result"] = result
                st.session_state["shopping_inputs"] = {
                    "requirement": requirement,
                    "budget": float(budget),
                    "preferred_ram": "" if preferred_ram == "No preference" else preferred_ram,
                }
                st.session_state.pop("cart_result", None)
                st.session_state.pop("custom_comparison", None)
            except Exception as error:
                st.error(f"The shopping workflow could not finish: {error}")

result = st.session_state.get("shopping_result")
if result:
    st.divider()
    st.subheader("Matching products")
    st.caption(f"Budget ₹{budget:,.0f} · RAM preference: {preferred_ram}")
    products = result.get("products", [])
    if products:
        product_frame = pd.DataFrame(products).rename(
            columns={
                "product_name": "Product",
                "brand": "Brand",
                "price": "Price (₹)",
                "processor": "Processor",
                "ram": "RAM",
                "storage": "Storage",
                "battery_life": "Battery",
                "stock": "Catalog stock",
                "rating": "Rating / 5",
            }
        )
        st.dataframe(
            product_frame[["Product", "Brand", "Price (₹)", "Processor", "RAM", "Storage", "Battery", "Catalog stock", "Rating / 5"]],
            hide_index=True,
            use_container_width=True,
        )
        st.subheader("Comparison")
        comparison = result.get("comparison", [])
        if comparison:
            comparison_options = {
                f"{product['product_name']} · ₹{float(product['price']):,.0f}": product
                for product in products
            }
            default_selection = list(comparison_options)[:3]
            selected_products = st.multiselect(
                "Products to compare",
                list(comparison_options),
                default=default_selection,
                key="comparison_products",
            )
            if st.button("Compare products", disabled=len(selected_products) < 2):
                selected_ids = {
                    str(comparison_options[label]["product_id"])
                    for label in selected_products
                }
                st.session_state["custom_comparison"] = run_comparison_agent(
                    [product for product in products if str(product["product_id"]) in selected_ids]
                )
            displayed_comparison = st.session_state.get("custom_comparison", comparison)
            st.dataframe(
                pd.DataFrame(displayed_comparison), hide_index=True, use_container_width=True
            )
        st.subheader("Inventory and budget")
        status_rows = []
        for product in products:
            product_id = str(product["product_id"])
            stock = result.get("inventory", {}).get(product_id, {})
            budget_result = result.get("budget_validation", {}).get(product_id, {})
            status_rows.append(
                {
                    "Product": product["product_name"],
                    "Available": "In stock" if stock.get("available") else "Out of stock",
                    "Units available": stock.get("stock", 0),
                    "Within budget": "Yes" if budget_result.get("within_budget") else "No",
                }
            )
        st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)
    else:
        st.info("No products match those filters. Try increasing the budget or changing the RAM preference.")

    recommendation = result.get("recommendation")
    if recommendation:
        st.subheader("Recommended product")
        st.markdown(
            f"<div class='recommendation'><strong>{recommendation['product_name']}</strong> · "
            f"₹{float(recommendation['price']):,.0f}<br>{result.get('recommendation_reason', '')}</div>",
            unsafe_allow_html=True,
        )
        st.subheader("Product FAQs")
        faq = result.get("faq_answers", {}).get(str(recommendation["product_id"]))
        st.write(faq or "FAQ retrieval is not available for this product.")
        selectable = [
            product for product in products
            if result.get("inventory", {}).get(str(product["product_id"]), {}).get("available")
            and result.get("budget_validation", {}).get(str(product["product_id"]), {}).get("within_budget")
        ]
        if selectable:
            labels = {f"{item['product_name']} · ₹{float(item['price']):,.0f}": str(item["product_id"]) for item in selectable}
            selected_label = st.selectbox("Choose a product", list(labels), key="cart_product")
            st.warning("Adding to cart is simulated and does not place an order.")
            if st.button("Add to cart", type="primary"):
                try:
                    cart_result = run_shopping_workflow(
                        st.session_state["shopping_inputs"]["requirement"],
                        st.session_state["shopping_inputs"]["budget"],
                        st.session_state["shopping_inputs"]["preferred_ram"],
                        confirm_add_to_cart=True,
                        selected_product_id=labels[selected_label],
                        db_path=str(get_database_path()),
                    )
                    st.session_state["cart_result"] = cart_result.get("cart")
                    st.session_state["shopping_result"] = cart_result
                except Exception as error:
                    st.error(f"Could not update the simulated cart: {error}")
    else:
        st.info(result.get("recommendation_reason", "No suitable in-stock product was found."))
    for error in result.get("errors", []):
        st.error(error)

cart_result = st.session_state.get("cart_result")
if cart_result:
    st.success(f"{cart_result['product']} added to cart {cart_result['cart_id']}.")
    st.subheader("Cart summary")
    st.dataframe(pd.DataFrame(get_cart_items()), hide_index=True, use_container_width=True)