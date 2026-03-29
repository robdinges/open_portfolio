from datetime import date
from typing import Optional, Dict
from .products import Product


class ProductCollection:
    def __init__(self):
        self.products: Dict[int, Product] = {}

    def add_product(self, product: Product):
        self.products[product.instrument_id] = product

    def search_product_id(self, product_id: int) -> Optional[Product]:
        return self.products.get(product_id)

    def list_products(self, include_inactive: bool = False, on_date: date | None = None):
        all_products = list(self.products.values())
        if include_inactive:
            return all_products
        return [product for product in all_products if product.is_active(on_date=on_date)]
