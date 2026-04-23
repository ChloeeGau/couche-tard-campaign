import os
import json
from retail_ops.data.products import retrieve_products

def verify():
    products = retrieve_products()
    skus = [p.core_identifiers.sku for p in products]
    print(f"Available SKUs: {skus}")
    assert "F-PIZZA-001" in skus, "F-PIZZA-001 missing!"
    print("Verification Passed: F-PIZZA-001 is present.")

if __name__ == "__main__":
    verify()
