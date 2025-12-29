from app.schema import TrendAnalysis
from app.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
from google.adk.agents.llm_agent import Agent
import json
import logging
from google import genai
from google.genai import types as genai_types

class TrendAgent:
    def __init__(self):
        # Load prompt for the agent
        try:
            with open("app/prompts/trend_analysis.md", "r") as f:
                self.prompt = f.read()
        except Exception as e:
            logging.error(f"Failed to load trend prompt: {e}")
            self.prompt = "Analyze the trends for this item."

        # Initialize the ADK Agent
        # Assuming Agent takes model, system_instruction or similar
        self.agent = Agent(
            name="trend_agent",
            model=GEMINI_MODEL_NAME,
            # system_instruction=self.prompt
        )

    def analyze_social_trends(self, product_context: str, image_path: str = None) -> TrendAnalysis:
        """
        Analyzes social media trends to find a match for the product using Gemini.
        If image_path is provided, it uses the image for analysis.
        """
        
        try:
            prompt_content = [
                f"Product Context: {product_context}\n",
                f"Product Context: {product_context}\n",
                "Analyze the current social media trends relevant to this product. Provide trend_name, executive_summary, trend_start_date, trend_scope, trend_lifecycle_stage, primary_sources, taxonomy_attributes, search_vectors, and visual_assets.\n"
            ]
            
            if image_path:
                image_part = genai_types.Part.from_uri(
                    file_uri=image_path, mime_type="image/png"  # Assumes png, strictly for demo
                )
                prompt_content.append(image_part)

            config = genai_types.GenerateContentConfig(
                **STANDARD_GENERATION_CONFIG,
                response_schema=TrendAnalysis,
            )
            
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt_content,
                config=config,
            )
            
            # response.parsed should be a valid object if using response_schema with Pydantic support in newer SDKs
            # Or response.text is valid JSON matching the schema
            
            if response.parsed:
                 # Check if response.parsed is already the object or dict
                 if isinstance(response.parsed, TrendAnalysis):
                     return response.parsed
                 return TrendAnalysis(**response.parsed)
            
            # Fallback to text parsing if parsed is not available/working as expected
            data = json.loads(response.text)
            return TrendAnalysis(**data)
            
        except Exception as e:
            logging.error(f"Trend Analysis Failed: {e}")
            from app.schema import TaxonomyAttributes
            # Fallback
            return TrendAnalysis(
                trend_name="Corporate Core",
                executive_summary="Fallback: Corporate style meeting modern comfort.",
                trend_start_date="01/2025",
                trend_scope="Macro",
                trend_lifecycle_stage="Current",
                primary_sources=["Fallback Source"],
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic="Minimalist",
                    secondary_aesthetic="Professional",
                    key_garments=["Blazer", "Trousers"],
                    materials_and_textures=["Wool", "Cotton"],
                    color_palette=["Navy", "Grey"],
                    mood_keywords=["Professional", "Sleek"],
                    target_occasion=["Work"],
                    seasonality="All Year"
                ),
                search_vectors=["corporate", "office", "workwear"],
                visual_assets=None
            )
