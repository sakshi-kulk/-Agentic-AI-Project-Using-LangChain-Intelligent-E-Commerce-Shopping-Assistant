"""Unit tests for catalog search, comparison, inventory, budget, and cart tools."""

import pandas as pd
import pytest

from database import get_stock, initialize_database
from tools.budget_tool import validate_budget
from tools.cart_tool import add_to_cart
from tools.comparison_tool import compare_products
from tools.faq_tool import answer_product_faq
from tools.inventory_tool import check_inventory
from tools.product_search_tool import search_products


@pytest.fixture
def catalog_path(tmp_path):
    path = tmp_path / "products.csv"
    pd.DataFrame(
        [
            {
                "product_id": "T1", "product_name": "Test Laptop", "brand": "Test",
                "price": 50000, "processor": "Core i5", "ram": "16GB",
                "storage": "512GB SSD", "battery_life": "8 Hours",
                "category": "Laptop", "stock": 2, "rating": 4.5,
            },
            {
                "product_id": "T2", "product_name": "Over Budget", "brand": "Test",
                "price": 70000, "processor": "Core i7", "ram": "32GB",
                "storage": "1TB SSD", "battery_life": "9 Hours",
                "category": "Laptop", "stock": 1, "rating": 4.8,
            },
        ]
    ).to_csv(path, index=False)
    return path


@pytest.fixture
def db_path(tmp_path, monkeypatch, catalog_path):
    import database

    monkeypatch.setattr(database, "PRODUCTS_PATH", catalog_path)
    path = tmp_path / "test.db"
    initialize_database(path)
    return path


def test_search_filters_by_budget_and_ram(catalog_path):
    products = search_products(60000, "Python programming", "16GB", catalog_path)
    assert [product["product_id"] for product in products] == ["T1"]


def test_search_rejects_nonpositive_budget(catalog_path):
    with pytest.raises(ValueError, match="greater than zero"):
        search_products(0, catalog_path=catalog_path)


def test_comparison_includes_requested_specs(catalog_path):
    product = search_products(60000, catalog_path=catalog_path)[0]
    comparison = compare_products([product])
    assert comparison.loc[0, "ram"] == "16GB"
    assert comparison.loc[0, "storage"] == "512GB SSD"
    assert "battery_life" in comparison.columns


def test_comparison_handles_empty_input():
    assert compare_products([]).empty


def test_inventory_reports_stock(db_path):
    assert check_inventory("T1", db_path) == {"available": True, "stock": 2}
    assert check_inventory("missing", db_path) == {"available": False, "stock": 0}


def test_budget_validation_includes_boundary():
    assert validate_budget(60000, 60000)["within_budget"] is True
    assert validate_budget(60001, 60000)["within_budget"] is False


def test_cart_requires_confirmation(db_path, catalog_path):
    product = search_products(60000, catalog_path=catalog_path)[0]
    with pytest.raises(PermissionError, match="confirmation"):
        add_to_cart(product, confirmed=False, db_path=db_path)
    assert get_stock("T1", db_path) == 2


def test_confirmed_cart_decrements_stock(db_path, catalog_path):
    product = search_products(60000, catalog_path=catalog_path)[0]
    result = add_to_cart(product, confirmed=True, db_path=db_path)
    assert result["status"] == "Added"
    assert result["product"] == "Test Laptop"
    assert result["cart_id"].startswith("CART-")
    assert get_stock("T1", db_path) == 1


def test_cart_rejects_out_of_stock_product(db_path):
    initialize_database(db_path)
    product = {
        "product_id": "T1", "product_name": "Test Laptop", "price": 50000,
    }
    add_to_cart(product, confirmed=True, db_path=db_path)
    add_to_cart(product, confirmed=True, db_path=db_path)
    with pytest.raises(ValueError, match="out of stock"):
        add_to_cart(product, confirmed=True, db_path=db_path)


def test_faq_fallback_answers_from_local_knowledge_base():
    answer = answer_product_faq(
        "Summarize Python programming, machine learning, battery runtime, and warranty.",
        {"product_name": "Test Laptop"},
        use_llm=False,
    )
    assert "Test Laptop" in answer
    assert "machine-learning" in answer.lower()
    assert "battery" in answer.lower()
    assert "warranty" in answer.lower()