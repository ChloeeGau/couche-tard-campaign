from retail_ops.schema import TrendSpotterOutput, Trend, TaxonomyAttributes
from retail_ops.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from retail_ops.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
from google.adk.agents.llm_agent import Agent
import json
import logging
from google import genai
from google.genai import types as genai_types
import inspect
import pathlib
import sys
from retail_ops.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent

class TrendSpotter:
    @log_function_call
    def __init__(self):
        self.prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/trend_spotter.md")
        
        self.agent = Agent(
            name="trend_spotter",
            model=GEMINI_MODEL_NAME,
            instruction=self.prompt_template,
            output_schema=TrendSpotterOutput,
            tools=[self.google_search]
        )

    def google_search(self, query: str) -> str:
        """Searches the web for real-time trends.
        
        Args:
            query (str): The search query.
            
        Returns:
            str: Search results.
        """
        print(f"MOCK SEARCH: {query}")
        if "food trends" in query or "hot weather" in query:
            return "Found 2 major trends in Quebec: 1. Extreme heatwave forecasted for the weekend (30°C+), leading to a surge in cold beverage searches. 2. Viral TikTok trend 'Dirty Sloche' (mixing Sloche with creamer or energy drinks) is trending among Gen Z."
        return "No significant trends found for this query."


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
