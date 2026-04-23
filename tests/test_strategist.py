import unittest
from unittest.mock import MagicMock
import sys
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
sys.modules["google.adk.agents"] = MagicMock()
sys.modules["google.adk.agents.llm_agent"] = MagicMock()

# Mock genai
sys.modules["google.genai"] = MagicMock()

# Mock config
mock_config = MagicMock()
mock_config.PROJECT_ID = "mock-project-id"
mock_config.LOCATION = "us-central1"
mock_config.GEMINI_MODEL_NAME = "gemini-2.5-pro"
mock_config.STANDARD_GENERATION_CONFIG = {}
sys.modules["app.config"] = mock_config

try:
    from retail_ops.sub_agents.strategist import Strategist
    from retail_ops.schema import Trend, TrendStrategy, TaxonomyAttributes, MarketingAttributes, TargetAudienceProfile
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

class TestStrategist(unittest.TestCase):
    def setUp(self):
        self.strategist = Strategist()
        self.strategist.agent = MagicMock()

    def test_generate_strategies_success(self):
        # Mock Input Trend
        trend = Trend(
            trend_name="Mock Trend",
            executive_summary="Summary",
            key_designers=[],
            social_media_tags=[],
            key_influencer_handles=[],
            essential_look_characteristics={},
            taxonomy_attributes=MagicMock(),
            search_vectors=[],
            marketing_attributes=MarketingAttributes(
                commercial_maturity="Mature",
                purchase_driver="Driver",
                ad_creative_direction="Direction",
                recommended_influencer_archetype="Archetype",
                ad_copy_hook="Hook",
                target_audience_profile=TargetAudienceProfile(
                    age_segments=["20s"],
                    gender_focus="All",
                    income_level="Mid",
                    psychographics=["Happy"],
                    geo_targeting="City",
                    shopping_behavior="Impulse"
                )
            )
        )

        # Mock Agent Response
        mock_strategies = [
            {
                "trend_name": "Mock Trend",
                "strategy_directive": "Buy this now.",
                "target_audience": "20s"
            }
        ]
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_strategies)
        self.strategist.agent.run.return_value = mock_response

        # Call
        strategies = self.strategist.generate_strategies([trend])

        # Assert
        self.assertEqual(len(strategies), 1)
        self.assertEqual(strategies[0].trend_name, "Mock Trend")
        self.assertEqual(strategies[0].strategy_directive, "Buy this now.")
        self.strategist.agent.run.assert_called_once()

    def test_generate_strategies_failure(self):
        self.strategist.agent.run.side_effect = Exception("API Error")
        strategies = self.strategist.generate_strategies([])
        self.assertEqual(strategies, [])

if __name__ == "__main__":
    unittest.main()
