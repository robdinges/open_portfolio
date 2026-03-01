from typing import Optional, Dict
from .products import Product


class ProductCollection:
    def __init__(self):
        self.products: Dict[int, Product] = {}

    def add_product(self, product: Product):
        self.products[product.instrument_id] = product

    def search_product_id(self, product_id: int) -> Optional[Product]:
        return self.products.get(product_id)

    def list_products(self):
        # minimal implementation
        return list(self.products.values())
