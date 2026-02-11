from fashion.schema import Trend, Scene, CreativeDirection, FinalAd
from fashion.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from fashion.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
import logging
from google import genai
from google.genai import types as genai_types
from google.genai.types import HarmBlockThreshold, HarmCategory
import os
from google.cloud import storage
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from typing import List
from fashion.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from fashion.schema import Product, ProductTrendMapping, TrendMatch, Trend
from typing import Optional
from fashion.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
from google.adk.agents.llm_agent import Agent
import json
import logging
from google import genai
from google.genai import types as genai_types
from google.cloud import storage
import io
from PIL import Image
from urllib.parse import urlparse, unquote
from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import InMemorySessionService
from google.adk.models import LlmResponse, LlmRequest
from typing import Optional
from typing import List
from fashion.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from google.adk.agents.invocation_context import InvocationContext
from fashion.data.products import retrieve_products
_genai_client = None
_genai_client_global = None  # For gemini-3 models that require global location
_storage_client = None
from google.genai.types import HarmBlockThreshold, HarmCategory
from fashion.tools.generate_video import generate_video
from fashion.tools.combine_video import combine_video

from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class CampaignDraft(BaseModel):
    campaign_name: str
    trend: str
    target_audience: str
    keyframes: List[str]
    video_url: Optional[str] = None

class CampaignManager:
    # scenelist = []
    scene_dict = {
        "creative_direction_summary": "This campaign, 'Le Tweed Rose: A Modern Legacy,' celebrates the timeless elegance of the pink tweed jacket by placing it in contemporary contexts. We juxtapose the heritage-inspired design with modern cityscapes and intimate moments, showcasing its versatility from sophisticated daywear to chic evening attire. The visual language is polished and elegant, using lighting and camera work inspired by Chanel's iconic aesthetic to highlight the exquisite craftsmanship of the jacket.",
        "scenes": [
            {
                "scene_id": 1,
                "scene_url": "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_image_1_1768084528.png",
                "scene_video_url": "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_video_1_1768084736.mp4",
                "setting": "A bright, airy Parisian apartment with high ceilings, large windows, and minimalist decor. The 'Heritage Revival' trend is reflected in the classic herringbone wood floors and ornate crown molding, set against modern furniture.",
                "lighting_style": "Soft, diffused morning light inspired by classic Chanel campaigns. The light pours through the windows, creating an ethereal glow that beautifully illuminates the soft pink texture of the tweed jacket.",
                "camera_movement": "Reflecting an 'Elegant' mood, the camera uses slow, graceful tracking shots. A gentle push-in focuses on the intricate braided trim and the texture of the tweed as the model moves her arm.",
                "styling_details": "The pink tweed jacket is the hero piece, worn over a simple cream silk camisole and paired with high-waisted white linen trousers. Styling is minimal, with delicate pearl stud earrings to complement the jacket without overpowering it.",
                "action": "A model is standing by the window, arranging a bouquet of peonies..."
            },
            {
                "scene_id": 2,
                "scene_url": "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_image_2_1768084530.png",
                "scene_video_url": "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_video_2_1768084729.mp4",
                "setting": "A chic, bustling city street in a gallery district for a 'Day-to-Night' occasion. The backdrop features modern architecture and stylish pedestrians, contrasting the jacket's classic design with a contemporary urban environment.",
                "lighting_style": "Crisp, natural daylight with dynamic shadows, reminiscent of Karl Lagerfeld's high-energy street-style shoots for Chanel. The bright sun makes the pink of the jacket pop and creates sharp, fashionable shadows.",
                "camera_movement": "A confident, 'Polished' Steadicam shot follows the model as she walks. The movement is fluid and energetic, capturing the life and swing of the jacket as she navigates the city sidewalk.",
                "styling_details": "Showcasing versatility, the pink tweed jacket is styled open over a classic white t-shirt and paired with vintage-wash straight-leg denim. The look is accessorized with modern cat-eye sunglasses and classic leather slingback heels.",
                "action": "The model walks with purpose and a slight smile, weaving through the sidewalk crowd..."
            },
            {
                "scene_id": 3,
                "scene_url": "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_image_3_1768084907.png",
                "scene_video_url": "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_video_3_1768084986.mp4",
                "setting": "A charming European street cafe at golden hour. The setting is romantic and picturesque, with cobblestone streets, and tables adorned with fresh flowers, embodying the \"Heritage Revival\" trend in a real-world context.",
                "lighting_style": "Warm, golden hour sunlight filtering through the leaves of nearby trees, creating a soft, dappled light effect. This natural lighting enhances the jacket's pink hue and gives the scene a dreamy, cinematic quality.",
                "camera_movement": "A gentle, handheld camera movement that feels intimate and observational, as if capturing a candid moment. A slow pan follows the model as she brings a cup of coffee to her lips.",
                "styling_details": "The pink tweed jacket is worn draped over the shoulders of a simple white linen dress. This styling is relaxed yet chic, perfect for a cafe setting. The look is completed with espadrille wedges and a classic leather handbag.",
                "action": "The model is seated at a small, round cafe table, smiling as she sips her coffee..."
            }
        ]
    }

    @log_function_call
    def __init__(self):
        # self.agent = Agent(
        #     name="product_trend_mapper",
        #     model=GEMINI_MODEL_NAME,
        # )
        #   try:

        self.prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/campaign_manager.md")
        print(self.prompt_template)
        #   except Exception as e:
        #       logging.error(f"Failed to load product_trend_mapper prompt: {e}")
        self.agent = Agent(
          name="campaign_manager",
          model=GEMINI_MODEL_NAME,
          instruction=self.prompt_template,
          tools=[
            # self.generate_video_scenes,
            # self.generate_combined_video,
            # self.generate_social_post,
            generate_video,
            combine_video,
          ],
          # after_model_callback=self._after_model_callback,
      )

    @log_function_call
    async def map_scenes(self, static_mapping_data: dict) -> CreativeDirection:    
        """
        Creates a CreativeDirection object from static data.
        """
        creative_direction_summary = static_mapping_data.get("creative_direction_summary", "")
        scenes_data = static_mapping_data.get("scenes", [])

        scenes = []
        for scene_dict in scenes_data:
            scene = Scene(
                scene_id=scene_dict.get("scene_id"),
                scene_video_url=scene_dict.get("scene_video_url"),
                scene_url=scene_dict.get("scene_url"),
                setting=scene_dict.get("setting"),
                lighting_style=scene_dict.get("lighting_style"),
                camera_movement=scene_dict.get("camera_movement"),
                styling_details=scene_dict.get("styling_details"),
                action=scene_dict.get("action"),
            )
            scenes.append(scene)

        return CreativeDirection(
            creative_direction_summary=creative_direction_summary,
            scenes=scenes
        )

    @log_function_call
    async def generate_video_scenes(self) -> FinalAd:
        print(f"calling generate_video_scenes")
        # return ["https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_video_1_1768084736.mp4", "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_video_2_1768084729.mp4", "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/scene_video_3_1768084986.mp4"]
        mapped_scenes = await self.map_scenes(self.scene_dict)
        final_ad = FinalAd()
        final_ad.creative_direction = mapped_scenes
        return final_ad
      

    @log_function_call
    async def generate_combined_video(self) -> FinalAd:
        print(f"calling generate_combined_video")
        mapped_scenes = await self.map_scenes(self.scene_dict)
        final_ad = FinalAd()
        final_ad.creative_direction = mapped_scenes
        final_ad.final_ad_url = "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/combined_video_1768085105.mp4"
        return final_ad

    @log_function_call
    async def generate_social_post(self) -> FinalAd:
        print(f"calling generate_social_post")
        mapped_scenes = await self.map_scenes(self.scene_dict)
        final_ad = FinalAd()
        final_ad.creative_direction = mapped_scenes
        final_ad.final_ad_url = "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/combined_video_1768085105.mp4"
        final_ad.final_social_ad_url = "https://storage.cloud.google.com/creative-content_orionfire-launch-1511/20260110173415814531_2v7h/jenna_styles_live.mp4"
        return final_ad
  