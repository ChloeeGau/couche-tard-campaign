from retail_ops.schema import Trend, TrendStrategy
from retail_ops.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from retail_ops.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
from google.adk.agents.llm_agent import Agent
import logging
import json
from typing import List

class Strategist:
    @log_function_call
    def __init__(self):
        try:
            with open("retail_ops/prompts/strategist.md", "r") as f:
                self.prompt_template = f.read()
        except Exception as e:
            logging.error(f"Failed to load strategist prompt: {e}")
            self.prompt_template = "Generate sales strategies for these trends."

        self.agent = Agent(
            name="strategist",
            model=GEMINI_MODEL_NAME,
            instruction=self.prompt_template,
        )

    @log_function_call
    def generate_strategies(self, trends: List[Trend]) -> List[TrendStrategy]:
        """
        Generates strategy directives for a list of trends.
        """
        try:
            # Prepare input
            trends_json = json.dumps([t.model_dump() for t in trends], default=str)
            
            response = self.agent.run(trends_json)
            
            # Parse response
            # The agent might return a list of dictionaries, rely on ADK or manual parsing if needed
            # Assuming ADK returns the raw text or parsed object if strict output/output_schema was set
            # Since output_schema isn't set in Agent init (it's List[TrendStrategy] which might be tricky for ADK if not wrapped),
            # we'll try to parse the text directly if needed.
            
            # Ideally we should use output_schema in Agent, but List[Model] can be complex.
            # Let's see if we can just parse the text.
            
            text = response.text.strip()
            # Clean generic markdown if present
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text)
            strategies = [TrendStrategy(**item) for item in data]
            return strategies

        except Exception as e:
            logging.error(f"Strategist Failed: {e}")
            # Fallback
            return []
