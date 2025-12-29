import sys
from unittest.mock import MagicMock

# 1. Mock google.adk chain
mock_google = MagicMock()
mock_adk = MagicMock()
mock_google.adk = mock_adk
sys.modules["google"] = mock_google
sys.modules["google.adk"] = mock_adk
mock_google.__path__ = []
mock_adk.__path__ = []

sys.modules["google.adk.model"] = MagicMock()
sys.modules["google.adk.agent"] = MagicMock()
sys.modules["google.adk.files"] = MagicMock()
sys.modules["google.adk.agents"] = MagicMock()
sys.modules["google.adk.agents.llm_agent"] = MagicMock()

# Mock google.genai (used in sub_agents/trend.py which is imported by agent.py)
sys.modules["google.genai"] = MagicMock()
sys.modules["google.genai.types"] = MagicMock()

# 2. Mock google.cloud.bigquery
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.bigquery"] = MagicMock()

# 3. Mock pydantic_settings
# We need a proper class for BaseSettings so subclassing works
class MockBaseSettings:
    def __init__(self, **kwargs):
        pass
    class Config:
        env_file = ".env"
        extra = "ignore"

mock_pydantic_settings = MagicMock()
mock_pydantic_settings.BaseSettings = MockBaseSettings
sys.modules["pydantic_settings"] = mock_pydantic_settings

# 4. Mock pydantic (used in schema)
# schema.py imports BaseModel, Field from pydantic
# We need actual classes for these or the schema definitions will fail
class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

mock_pydantic = MagicMock()
mock_pydantic.BaseModel = MockBaseModel
mock_pydantic.Field = MagicMock(return_value=None)
sys.modules["pydantic"] = mock_pydantic

# --- Now we can import app code ---
# We need to ensure app.config uses our mocked values
# app.config needs to be patched or mocked in sys.modules if we want to control it before import
# OR we can import it and then set attributes if it's a simple module now.

# Since app.config is likely just variables now, we should mock the module
mock_config = MagicMock()
mock_config.PROJECT_ID = "mock-project-id"
mock_config.BQ_DATASET = "mock-dataset"
mock_config.GEMINI_MODEL_NAME = "gemini-2.5-pro"
mock_config.WITH_MOCKED_DATA = False
sys.modules["app.config"] = mock_config

try:
    from app.tools.inventory import InventoryTool
    from app.tools.sales import SalesTool
    from app.config import PROJECT_ID, BQ_DATASET, WITH_MOCKED_DATA
except ImportError as e:
    print(f"ImportError despite mocks: {e}")
    sys.exit(1)

print(f"Project ID: {PROJECT_ID}")

# Instantiate Tools
inventory_tool = InventoryTool()
sales_tool = SalesTool()

# Force client to None to trigger fallback/mock paths in tools
inventory_tool.client = None
sales_tool.client = None

# Test InventoryTool
print("\n--- Testing InventoryTool (Fallback) ---")
high_stock = inventory_tool.find_high_stock()
print(f"High Stock Items Found: {len(high_stock)}")
for product in high_stock:
    # product is instance of Product now
    stock = product.inventory.stock_level if product.inventory else "Unknown"
    print(f"- {product.sku}: {product.name} - Stock: {stock}")

print("\n--- Testing SalesTool (Fallback) ---")
low_velocity = sales_tool.find_low_velocity()
print(f"Low Velocity Items Found: {len(low_velocity)}")
for product in low_velocity:
    velocity = product.sales.velocity if product.sales else "Unknown"
    reason = product.sales.reasoning if product.sales else "None"
    print(f"- {product.sku}: {product.name} - Velocity: {velocity} (Reason: {reason})")

# Test Intersection
print("\n--- Testing Intersection (Manual) ---")
# Manually simulate what agent does
low_velocity_map = {p.sku: p for p in low_velocity}
opportunities = []

for product in high_stock:
    if product.sku in low_velocity_map:
        sales_product = low_velocity_map[product.sku]
        product.sales = sales_product.sales
        opportunities.append(product)

print(f"Opportunities Found: {len(opportunities)}")
for op in opportunities:
    stock = op.inventory.stock_level if op.inventory else "Unknown"
    velocity = op.sales.velocity if op.sales else "Unknown"
    print(f"OPPORTUNITY: {op.name} ({op.sku}) - Stock: {stock}, Velocity: {velocity}")
