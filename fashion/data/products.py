from fashion.schema import Product
import json
from typing import List


def retrieve_products() -> List[Product]:
    with open('fashion/data/products.json', 'r') as f:
      product_data = f.read()

      # x = json.loads(product_data, object_hook=lambda d: Product(**d))
      x = json.loads(product_data)
      products = [Product(**item) for item in x]
      # products = [p for p in products if p.commercial_status.sales_velocity == "low"]

    return products 