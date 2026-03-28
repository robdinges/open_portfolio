"""Production WSGI entrypoint for OpenPortfolio."""

from __future__ import annotations

from .product_collection import ProductCollection
from .sample_data import create_realistic_dataset
from .web_app import make_app


def create_wsgi_app():
    dataset = create_realistic_dataset()
    clients = dataset["clients"]
    products_list = dataset["products"]
    currency_prices = dataset["prices"]

    product_collection = ProductCollection()
    for product in products_list:
        product_collection.add_product(product)

    return make_app(clients, product_collection, currency_prices)


app = create_wsgi_app()
