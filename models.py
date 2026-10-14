"""Shared typed models for catalog products and shopping carts."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Product:
    product_id: str
    product_name: str
    brand: str
    price: float
    processor: str
    ram: str
    storage: str
    battery_life: str
    category: str
    stock: int
    rating: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CartResult:
    cart_id: str
    product: str
    status: str
    quantity: int = 1