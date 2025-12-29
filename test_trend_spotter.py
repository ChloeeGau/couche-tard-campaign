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
    from app.sub_agents.trend_spotter import TrendSpotter
    from app.schema import TaxonomyAttributes, TrendSpotterOutput, Trend, MarketingAttributes, TargetAudienceProfile
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Mock GenAI Client
mock_client_cls = sys.modules["google.genai"].Client
mock_client_instance = mock_client_cls.return_value
mock_response = MagicMock()
class MockTaxonomyAttributes:
    primary_aesthetic = "Cyberpunk"
    secondary_aesthetic = "Dystopian"
    key_garments = ["Leather Jacket", "Neon Boots"]
    materials_and_textures = ["Leather", "PVC"]
    color_palette = ["Black", "Neon Green"]
    mood_keywords = ["Edgy", "Futuristic"]
    target_occasion = ["Night Out"]
    seasonality = "FW2077"

class MockTargetAudienceProfile:
    def __init__(self, age_segments, gender_focus, income_level, psychographics, geo_targeting, shopping_behavior):
        self.age_segments = age_segments
        self.gender_focus = gender_focus
        self.income_level = income_level
        self.psychographics = psychographics
        self.geo_targeting = geo_targeting
        self.shopping_behavior = shopping_behavior

class MockTrendSpotterOutput:
    trends = [
        Trend(
            trend_name="Cyber Core",
            executive_summary="A glimpse into the future.",
            key_designers=["Designer X"],
            social_media_tags=["#cyber"],
            key_influencer_handles=["@cyber_influencer"],
            essential_look_characteristics={"Vibe": "Futuristic"},
            ad_copy_hook="Future is now.",
            target_demographic_segments=["Gen Z", "Alphas"],
            target_audience_profile=MockTargetAudienceProfile(
                age_segments=["18-24"],
                gender_focus="Unisex",
                income_level="High",
                psychographics=["Techy"],
                geo_targeting="Global",
                shopping_behavior="Online"
            ),
            taxonomy_attributes=MockTaxonomyAttributes(),
            search_vectors=["cyber", "future", "neon"]
        )
    ]

mock_response.parsed = MockTrendSpotterOutput()
mock_client_instance.models.generate_content.return_value = mock_response

# Mock the LLM Agent
mock_llm_agent = sys.modules["google.adk.agents.llm_agent"]

print("\n--- Testing TrendSpotter ---")
try:
    spotter = TrendSpotter()
    print("TrendSpotter initialized.")
    
    # Test spot_trends
    print("Calling spot_trends...")
    # Assuming spot_trends takes an article_text argument, providing a dummy one.
    article_text = "In the year 2077, fashion takes a dark turn..."
    agent_instance = spotter.spot_trends(article_text)
    
    print(f"Returned object type: {type(agent_instance)}")

    # Verify Agent Init
    mock_llm_agent.Agent.assert_called()
    _, call_kwargs = mock_llm_agent.Agent.call_args
    
    if call_kwargs['model'] == "gemini-2.5-pro":
        print("Agent initialized with correct model.")
    else:
        print(f"Agent model mismatch: {call_kwargs.get('model')}")
        
    if "Analyze the fashion trend" in call_kwargs['system_instruction']:
        print("Agent initialized with correct system instruction.")
    else:
         print("Agent system instruction mismatch.")

except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
