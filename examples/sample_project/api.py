"""
Sample API layer for the example project.
Demonstrates inter-module function calls for call graph visualization.
"""

from __future__ import annotations

from typing import Optional
from models import Product, Order, Inventory
from utils import validate_email, sanitize_input, format_currency, paginate, Logger

logger = Logger("api", level="INFO")
_inventory = Inventory()


def get_products(page: int = 1, per_page: int = 10, search: Optional[str] = None) -> dict:
    """
    Retrieve paginated product list.

    Args:
        page:     Page number (1-indexed).
        per_page: Items per page.
        search:   Optional search query.

    Returns:
        Paginated product data.
    """
    logger.info("Fetching products", page=page)

    if search:
        query = sanitize_input(search)
        products = _inventory.search(query)
    else:
        products = _inventory.list_products()

    product_dicts = [p.to_dict() for p in products]
    return paginate(product_dicts, page, per_page)


def get_product(product_id: int) -> Optional[dict]:
    """Retrieve a single product by ID."""
    product = _inventory.get_product(product_id)
    if product is None:
        logger.warning("Product not found", product_id=product_id)
        return None
    return product.to_dict()


def create_order(customer_email: str, items: list[dict]) -> dict:
    """
    Create a new order.

    Args:
        customer_email: Customer's email address.
        items:          List of {product_id, quantity} dicts.

    Returns:
        Order summary dict.
    """
    if not validate_email(customer_email):
        return {"error": "Invalid email address", "success": False}

    email = sanitize_input(customer_email)
    order = Order(order_id=_generate_order_id(), customer_id=hash(email))

    errors = []
    for item in items:
        product = _inventory.get_product(item["product_id"])
        if product is None:
            errors.append(f"Product {item['product_id']} not found")
            continue
        try:
            order.add_item(product, item["quantity"])
        except ValueError as e:
            errors.append(str(e))

    if errors:
        return {"success": False, "errors": errors}

    total = order.calculate_total()
    order.complete()

    logger.info("Order created", order_id=order.order_id, total=total)

    return {
        "success": True,
        "order_id": order.order_id,
        "total": format_currency(total),
        "items": order.items,
    }


def apply_coupon_to_order(order: Order, coupon_code: str) -> dict:
    """Apply a coupon to an existing order."""
    code = sanitize_input(coupon_code)
    discount = order.apply_coupon(code)
    if discount > 0:
        logger.info("Coupon applied", code=code, discount=discount)
        return {"applied": True, "discount": format_currency(discount)}
    return {"applied": False, "discount": format_currency(0)}


def restock_product(product_id: int, quantity: int) -> dict:
    """Restock a product."""
    success = _inventory.restock(product_id, quantity)
    if success:
        product = _inventory.get_product(product_id)
        logger.info("Product restocked", product_id=product_id, quantity=quantity)
        return {"success": True, "new_stock": product.stock}
    return {"success": False, "error": "Product not found"}


def get_low_stock_report(threshold: int = 5) -> list[dict]:
    """Get products with low stock."""
    low_stock = _inventory.low_stock_alert(threshold)
    return [p.to_dict() for p in low_stock]


def _generate_order_id() -> str:
    """Generate a unique order ID."""
    import time
    import random
    return f"ORD-{int(time.time())}-{random.randint(1000, 9999)}"


def seed_inventory() -> None:
    """Populate inventory with sample data."""
    sample_products = [
        Product(1, "Laptop Pro 15", 1299.99, stock=10),
        Product(2, "Wireless Mouse", 29.99, stock=50),
        Product(3, "USB-C Hub", 49.99, stock=30),
        Product(4, "Mechanical Keyboard", 159.99, stock=15),
        Product(5, "Monitor 4K", 599.99, stock=8),
        Product(6, "Webcam HD", 79.99, stock=25),
        Product(7, "Standing Desk", 449.99, stock=3),
        Product(8, "Desk Chair", 299.99, stock=7),
    ]
    for product in sample_products:
        _inventory.add_product(product)
    logger.info("Inventory seeded", count=len(sample_products))
