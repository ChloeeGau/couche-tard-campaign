import sys
from unittest.mock import MagicMock

# --- Mocks ---
# Create a robust mock structure for google
mock_google = MagicMock()
sys.modules["google"] = mock_google
mock_google.__path__ = []

# Mock google.adk (still imported in file)
mock_adk = MagicMock()
sys.modules["google.adk"] = mock_adk
sys.modules["google.adk.agents"] = MagicMock()
sys.modules["google.adk.agents.llm_agent"] = MagicMock()

# Mock google.genai
mock_genai = MagicMock()
sys.modules["google.genai"] = mock_genai
sys.modules["google.genai.types"] = MagicMock()

# Mock google.cloud (needed because app/__init__ imports agent which imports tools which import bigquery)
mock_cloud = MagicMock()
mock_bq = MagicMock()
mock_cloud.bigquery = mock_bq
sys.modules["google.cloud"] = mock_cloud
sys.modules["google.cloud.bigquery"] = mock_bq

# Mock config
mock_config = MagicMock()
mock_config.PROJECT_ID = "mock-project-id"
mock_config.LOCATION = "us-central1"
mock_config.GEMINI_MODEL_NAME = "gemini-2.5-pro"
mock_config.STANDARD_GENERATION_CONFIG = {"response_mime_type": "application/json", "temperature": 0.2}
sys.modules["app.config"] = mock_config

# Mock schema models
class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
mock_pydantic = MagicMock()
mock_pydantic.BaseModel = MockBaseModel
mock_pydantic.Field = MagicMock(return_value=None)
sys.modules["pydantic"] = mock_pydantic

# --- Imports after mocks ---
try:
    from retail_ops.sub_agents.trend import TrendAgent
    from retail_ops.config import GEMINI_MODEL_NAME
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Setup Mocks Return Values
# Mock GenAI Client
mock_client_cls = sys.modules["google.genai"].Client
mock_client_instance = mock_client_cls.return_value
# Mock generate_content response
mock_response = MagicMock()
# Mock parsed object to match TrendAnalysis structure
class MockTrendAnalysis:
    trend_name = "Digital Nomad"
    executive_summary = "Remote Work Revolution"
    trend_scope = "Macro"
    primary_sources = ["Source A"]
    taxonomy_attributes = MagicMock()
    search_vectors = ["nomad"]
    visual_assets = MagicMock()

mock_response.parsed = MockTrendAnalysis()
mock_client_instance.models.generate_content.return_value = mock_response

print("\n--- Testing TrendAgent ---")
try:
    agent = TrendAgent()
    print("TrendAgent initialized.")
    
    # Test analyze_social_trends
    print("Calling analyze_social_trends...")
    result = agent.analyze_social_trends("A comfortable hoodie for coding", image_path="hoodie.jpg")

    print(f"Trend Name: {result.trend_name}")
    print(f"Executive Summary: {result.executive_summary}")

    # Verify Client Init
    mock_client_cls.assert_called_once()
    _, kwargs = mock_client_cls.call_args
    if kwargs.get('project') == "mock-project-id" and kwargs.get('location') == "us-central1":
         print("GenAI Client initialized with correct config.")
    else:
         print(f"GenAI Client config mismatch: {kwargs}")

    # Verify generate_content called
    mock_client_instance.models.generate_content.assert_called_once()
    _, call_kwargs = mock_client_instance.models.generate_content.call_args
    
    if call_kwargs['config'].response_schema:
        print("Called with response_schema.")
    else:
        print("Did NOT call with response_schema.")

except Exception as e:
    print(f"Test failed with exception: {e}")
    import traceback
    traceback.print_exc()
