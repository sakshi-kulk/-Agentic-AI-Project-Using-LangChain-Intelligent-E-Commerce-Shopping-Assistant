"""SQLite persistence for local inventory and simulated shopping carts."""

import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = ROOT_DIR / "data" / "products.csv"
load_dotenv(ROOT_DIR / ".env")


def get_database_path(db_path: str | Path | None = None) -> Path:
    configured_path = db_path or os.getenv("SHOPPING_DB_PATH", "data/shopping_assistant.db")
    path = Path(configured_path)
    if not path.is_absolute():
        path = ROOT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(get_database_path(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: str | Path | None = None) -> None:
    """Create tables and load the sample catalog once into SQLite inventory."""
    with get_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                product_id TEXT PRIMARY KEY,
                stock INTEGER NOT NULL CHECK (stock >= 0)
            );
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS cart_items (
                cart_id TEXT NOT NULL REFERENCES carts(cart_id),
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price REAL NOT NULL,
                PRIMARY KEY (cart_id, product_id)
            );
            """
        )
        product_count = connection.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if product_count == 0:
            products = pd.read_csv(PRODUCTS_PATH)
            connection.executemany(
                "INSERT INTO inventory(product_id, stock) VALUES (?, ?)",
                [(str(row.product_id), int(row.stock)) for row in products.itertuples()],
            )


def get_stock(product_id: str, db_path: str | Path | None = None) -> int:
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT stock FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()
    if row is None:
        return 0
    return int(row["stock"])


def add_product_to_cart(
    product: dict[str, Any], db_path: str | Path | None = None
) -> dict[str, Any]:
    """Atomically check stock, decrement inventory, and persist a simulated cart."""
    initialize_database(db_path)
    product_id = str(product["product_id"])
    cart_id = f"CART-{uuid.uuid4().hex[:10].upper()}"
    connection = get_connection(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT stock FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None or row["stock"] < 1:
            raise ValueError(f"{product.get('product_name', product_id)} is out of stock.")
        connection.execute(
            "UPDATE inventory SET stock = stock - 1 WHERE product_id = ?", (product_id,)
        )
        connection.execute("INSERT INTO carts(cart_id) VALUES (?)", (cart_id,))
        connection.execute(
            """INSERT INTO cart_items(cart_id, product_id, product_name, quantity, unit_price)
               VALUES (?, ?, ?, 1, ?)""",
            (cart_id, product_id, str(product["product_name"]), float(product["price"])),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"cart_id": cart_id, "product": str(product["product_name"]), "status": "Added"}


def get_cart_items(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """SELECT c.cart_id, i.product_id, i.product_name, i.quantity, i.unit_price
               FROM carts AS c JOIN cart_items AS i ON i.cart_id = c.cart_id
               ORDER BY c.created_at DESC, c.cart_id DESC"""
        ).fetchall()
    return [dict(row) for row in rows]