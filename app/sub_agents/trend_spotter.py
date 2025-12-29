from app.schema import TrendSpotterOutput, Trend, TaxonomyAttributes
from app.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
from google.adk.agents.llm_agent import Agent
import json
import logging
from google import genai
from google.genai import types as genai_types

class TrendSpotter:
    def __init__(self):
        try:
            with open("app/prompts/trend_spotter.md", "r") as f:
                self.prompt_template = f.read()
        except Exception as e:
            logging.error(f"Failed to load trend_spotter prompt: {e}")
            self.prompt_template = "Analyze the latest fashion trends."
            
        self.agent = Agent(
            name="trend_spotter",
            model=GEMINI_MODEL_NAME,
            instruction=self.prompt_template,
            output_schema=TrendSpotterOutput
        )


    # def spot_trends(self) -> TrendSpotterOutput:
    #     """
    #     Returns the configured ADK Agent for trend spotting.
    #     The Agent is pre-loaded with the trend spotter prompt/system instruction.
    #     """
    #     try:
    #         return self.agent.run()
    #     except Exception as e:
    #         logging.error(f"Failed to spot trends: {e}")
    #         # Fallback
    #         return TrendSpotterOutput(
    #             trends=[
    #                 Trend(
    #                     executive_summary=f"Analysis failed: {e}",
    #                     trend_name="Unknown",
    #                     taxonomy_attributes=TaxonomyAttributes(
    #                         primary_aesthetic="Unknown",
    #                         secondary_aesthetic="Unknown",
    #                         key_garments=[],
    #                         materials_and_textures=[],
    #                         color_palette=[],
    #                         mood_keywords=[],
    #                         target_occasion=[],
    #                         seasonality="Unknown"
    #                     ),
    #                     search_vectors=[],
    #                     marketing_attributes=None
    #                 )
    #             ]
    #         )
