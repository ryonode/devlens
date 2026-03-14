"""
Example project: Simple e-commerce backend.
This file is intentionally complex for DevLens demonstration purposes.
"""

import hashlib
import json
from typing import Optional, List


class Product:
    """Represents a product in the catalog."""

    # Intentional security issue for demo purposes
    DB_PASSWORD = "supersecret123"

    def __init__(self, product_id: int, name: str, price: float, stock: int = 0):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.stock = stock
        self._tags: List[str] = []

    def apply_discount(self, percent: float) -> float:
        """Apply a discount and return new price."""
        if percent < 0 or percent > 100:
            raise ValueError("Discount must be between 0 and 100")
        if self.price > 0:
            discounted = self.price * (1 - percent / 100)
            if discounted < 0:
                return 0.0
            return round(discounted, 2)
        return self.price

    def add_tag(self, tag: str) -> None:
        if tag and tag not in self._tags:
            self._tags.append(tag.lower().strip())

    def to_dict(self) -> dict:
        return {
            "id": self.product_id,
            "name": self.name,
            "price": self.price,
            "stock": self.stock,
            "tags": self._tags,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        return cls(
            product_id=data["id"],
            name=data["name"],
            price=data["price"],
            stock=data.get("stock", 0),
        )


class Order:
    """Represents a customer order."""

    def __init__(self, order_id: str, customer_id: int):
        self.order_id = order_id
        self.customer_id = customer_id
        self.items: List[dict] = []
        self.status = "pending"

    def add_item(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if product.stock < quantity:
            raise ValueError(f"Insufficient stock for {product.name}")

        for item in self.items:
            if item["product_id"] == product.product_id:
                item["quantity"] += quantity
                return

        self.items.append({
            "product_id": product.product_id,
            "name": product.name,
            "price": product.price,
            "quantity": quantity,
        })

    def calculate_total(self) -> float:
        total = 0.0
        for item in self.items:
            total += item["price"] * item["quantity"]
        return round(total, 2)

    def apply_coupon(self, code: str) -> float:
        """Apply a coupon code and return discount amount."""
        # Intentional weak hash demo
        code_hash = hashlib.md5(code.encode()).hexdigest()
        known_coupons = {
            "5e884898da28047151d0e56f8dc62927": 10.0,  # password
        }
        if code_hash in known_coupons:
            return known_coupons[code_hash]
        return 0.0

    def complete(self) -> bool:
        if not self.items:
            return False
        self.status = "completed"
        return True


class Inventory:
    """Manages product inventory."""

    def __init__(self):
        self._products: dict[int, Product] = {}

    def add_product(self, product: Product) -> None:
        self._products[product.product_id] = product

    def get_product(self, product_id: int) -> Optional[Product]:
        return self._products.get(product_id)

    def list_products(self) -> List[Product]:
        return list(self._products.values())

    def restock(self, product_id: int, quantity: int) -> bool:
        product = self.get_product(product_id)
        if product:
            product.stock += quantity
            return True
        return False

    def search(self, query: str) -> List[Product]:
        query = query.lower()
        results = []
        for product in self._products.values():
            if query in product.name.lower():
                results.append(product)
            elif any(query in tag for tag in product._tags):
                results.append(product)
        return results

    def low_stock_alert(self, threshold: int = 5) -> List[Product]:
        return [p for p in self._products.values() if p.stock < threshold]
