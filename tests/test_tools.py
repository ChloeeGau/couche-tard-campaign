import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.davos')

from retail_ops.tools.inventory import InventoryTool
from retail_ops.tools.sales import SalesTool

inventory_tool = InventoryTool()
sales_tool = SalesTool()

print("\n--- Testing InventoryTool (Fallback) ---")
high_stock = inventory_tool.find_high_stock()
print(f"High Stock Items Found: {len(high_stock)}")
for product in high_stock:
    sku = product.core_identifiers.sku
    name = product.core_identifiers.product_name
    stock = product.commercial_status.stock_quantity if product.commercial_status else "Unknown"
    print(f"- {sku}: {name} - Stock: {stock}")
    
    if sku == "F-PIZZA-001":
        print("Verified Couche-Tard SKU F-PIZZA-001 presence.")
