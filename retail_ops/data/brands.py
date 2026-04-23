from retail_ops.schema import Brand
import json
from typing import List

def retrieve_brands() -> List[Brand]:
    with open('retail_ops/data/brands.json', 'r') as f:
        brand_data = f.read()
        x = json.loads(brand_data)
        brands = [Brand(**item) for item in x]
    return brands
