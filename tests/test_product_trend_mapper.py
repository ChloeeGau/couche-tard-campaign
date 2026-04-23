import sys
from unittest.mock import MagicMock
import json

# --- Mocks ---
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

# Mock google.genai
mock_genai = MagicMock()
sys.modules["google.genai"] = mock_genai
sys.modules["google.genai.types"] = MagicMock()

# Mock config
mock_config = MagicMock()
mock_config.PROJECT_ID = "mock-project-id"
mock_config.LOCATION = "us-central1"
mock_config.GEMINI_MODEL_NAME = "gemini-2.5-pro"
mock_config.STANDARD_GENERATION_CONFIG = {"response_mime_type": "application/json", "temperature": 0.2}
sys.modules["app.config"] = mock_config

# Mock schema
class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def model_dump_json(self):
        return json.dumps(self.__dict__, default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o))

mock_pydantic = MagicMock()
mock_pydantic.BaseModel = MockBaseModel
mock_pydantic.Field = MagicMock(return_value=None)
sys.modules["pydantic"] = mock_pydantic

try:
    from retail_ops.sub_agents.product_trend_mapper import ProductTrendMapper
    from retail_ops.schema import Product, ProductTrendMapping, TrendMatch, Trend
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Mock GenAI Client
mock_client_cls = sys.modules["google.genai"].Client
mock_client_instance = mock_client_cls.return_value
mock_response = MagicMock()

# Helper to create mock trend analysis
def create_mock_trend_match(name, score):
    mock_trend = MagicMock()
    mock_trend.trend_name = name
    mock_trend.match_score = score
    # We need to mock the TrendAnalysis object inside TrendMatch
    return TrendMatch(
        match_score=score,
        reasoning="Mock Reasoning",
        trend=Trend(
            trend_name=name,
            executive_summary="Summary",
            key_designers=[],
            social_media_tags=[],
            key_influencer_handles=[],
            essential_look_characteristics={},
            taxonomy_attributes=MagicMock(),
            search_vectors=[],
            marketing_attributes=None
        )
    )

class MockProductTrendMapping:
    micro_trends = [
        create_mock_trend_match("Micro 1", 0.9),
        create_mock_trend_match("Micro 2", 0.8),
        create_mock_trend_match("Micro 3", 0.7)
    ]
    macro_trends = [
        create_mock_trend_match("Macro 1", 0.9),
        create_mock_trend_match("Macro 2", 0.8),
        create_mock_trend_match("Macro 3", 0.7)
    ]

mock_response.parsed = MockProductTrendMapping()
mock_client_instance.models.generate_content.return_value = mock_response

print("\n--- Testing ProductTrendMapper ---")
try:
    mapper = ProductTrendMapper()
    print("ProductTrendMapper initialized.")
    
    product = Product(name="Neo-Trench", sku="123")
    
    result = mapper.map_product_to_trends(product, image_path="trench.png")
    
    print(f"Micro Trends Found: {len(result.micro_trends)}")
    print(f"Macro Trends Found: {len(result.macro_trends)}")
    print(f"First Micro Trend: {result.micro_trends[0].trend.trend_name} (Score: {result.micro_trends[0].match_score})")

    # Verify generate_content called with schema
    mock_client_instance.models.generate_content.assert_called()
    _, call_kwargs = mock_client_instance.models.generate_content.call_args
    if call_kwargs['config'].response_schema:
        print("Called with response_schema.")
    else:
        print("Did NOT call with response_schema.")

    # Test identify_product_from_image
    print("\nTesting identify_product_from_image...")
    
    # Mock response for product identification
    mock_product_response = MagicMock()
    mock_product_response.parsed = Product(sku="GEN-123", name="Generated Product", retail_price=100.0)
    mock_client_instance.models.generate_content.return_value = mock_product_response
    
    identified_product = mapper.identify_product_from_image("test_image.png")
    print(f"Identified Product: {identified_product.name}, SKU: {identified_product.sku}")
    
    if identified_product.image_uri == "test_image.png":
         print("Image URI safely defaulted/set.")
    else:
         print(f"Image URI mismatch: {identified_product.image_uri}")

except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
