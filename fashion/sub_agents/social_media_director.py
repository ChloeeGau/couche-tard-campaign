from typing import List
from fashion.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from fashion.config import GEMINI_MODEL_NAME, IMAGE_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG, PROTOTYPE_SAFETY_SETTINGS
import logging
from google import genai
from google.genai import types as genai_types
from google.cloud import storage
from PIL import Image
import io
import base64
import os
from google.genai.types import HarmBlockThreshold, HarmCategory
from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from typing import Optional
from fashion.schema import Product, Trend, Brand
from fashion.data.brands import retrieve_brands
from fashion.data.brands import retrieve_brands
from fashion.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from fashion.adk_common.utils.utils_agents import get_genai_client, get_or_create_unique_session_id
from fashion.adk_common.utils.utils_gcs import download_blob_to_bytes
from fashion.adk_common.utils.utils_gcs import normalize_bucket_uri
from fashion.tools.generate_video import generate_video
from fashion.tools.combine_video import combine_video

logger = logging.getLogger(__name__)
class SocialMediaDirector:
    selected_product:Product = None
    
    @log_function_call
    def __init__(self):
      self.prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/social_media_director.md")
      self.agent = Agent(
          name="social_media_director",
          model=GEMINI_MODEL_NAME,
          instruction=self.prompt_template,
          tools=[
            self.product_research,
            self.generate_keyframe_image_prompt,
            generate_video,
            combine_video,
          ],
          after_model_callback=self._after_model_callback,
          before_model_callback=self._before_model_callback          
      )

    @log_function_call
    def _before_model_callback(
        self,
        callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        selected_product = callback_context.state.get('product')
        return None  # Allow the model call to proceed

    @log_function_call
    def _after_model_callback(
        self,
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        agent_name = callback_context.agent_name
        invocation_id = callback_context.invocation_id
        logger.info(f"After Model Callback")
        logger.info(f"Exiting Agent: {agent_name} (Inv: {invocation_id})")
        if llm_response:
            logger.info(f"Response: {llm_response.content}")
        return None  # Allow the model call to proceed

    @log_function_call
    async def _load_brand_data_from_json(self, selected_product) -> Brand:
        brand_name_str = selected_product['core_identifiers']['brand']
        
        # Assuming self.retrieve_brands() returns a list of dictionaries,
        # where each dictionary represents a brand and has a 'name' key.
        all_brands = retrieve_brands()
        logger.info(f"all_brands is {all_brands}")
        for brand in all_brands:
            if brand.name == brand_name_str:
                return brand
    
    # TODO add intermediary step to generate the prompt, provide to the user before generating the image
    @log_function_call
    async def generate_keyframe_image_prompt(self, product_data: Product, trend_data: Trend, product_research: str, tool_context: ToolContext) -> List[str]:
        logger.info(f"generate_keyframe_image_prompt {product_data}")
        logger.info(f"trend_data {trend_data}")
        selected_product = tool_context._invocation_context.session.state.get('product')
        product_image_path = selected_product['media']['main_image_url']
        brand_data: Brand = await self._load_brand_data_from_json(selected_product)
        logger.info(f"brand_data is {brand_data}")        
        
        # Extract Social Media Model Data
        social_media_model = brand_data.social_media_model
        model_name = "N/A"
        model_influencer_type = "N/A"
        model_consistency_desciption = "N/A"
        model_images = "N/A"

        setting_name = "N/A"
        setting_image_url = "N/A"
            
        if social_media_model:
            if social_media_model.model_images:
                model_images = ", ".join(social_media_model.model_images)
            
            model_name = social_media_model.model_name
            model_influencer_type = social_media_model.model_influencer_type
            model_consistency_desciption = social_media_model.model_consistency_desciption
            if social_media_model.model_settings:
                setting_name = social_media_model.model_settings[0].setting_name
                setting_image_url = social_media_model.model_settings[0].setting_image_url
        
        
        style_name = "N/A"
        if brand_data.social_media_model.model_social_media_styles and len(brand_data.social_media_model.model_social_media_styles) > 0:
            style_name = brand_data.social_media_model.model_social_media_styles[0].style_name

        formatted_style_name = style_name.lower().replace(" ", "_").lower()
        prompt_template = load_prompt_file_from_calling_agent(prompt_filename=f"../prompts/social_{formatted_style_name}_image.md")
        video_prompt_template = load_prompt_file_from_calling_agent(prompt_filename=f"../prompts/social_{formatted_style_name}_video.md")
        
        # Helper to join lists safely
        def format_list(item_list):
            return ", ".join(item_list) if item_list else "N/A"

        # Helper to format dicts
        def format_dict(item_dict):
             return "\n".join([f"- {k}: {v}" for k, v in item_dict.items()]) if item_dict else "N/A"

        # Map Attributes
        prompt_mapping = {
            "product_name": product_data['core_identifiers']['product_name'],
            "model_name": model_name,
            "model_influencer_type": model_influencer_type,
            "model_consistency_desciption": model_consistency_desciption,
            "setting_name": setting_name,
            # "product_image_path": product_image_path,
            # "model_images": model_images,
            # "setting_image_url": setting_image_url,
            "product_research": product_research,
        }

        social_media_urls = []
        # Format the prompt
        formatted_image_prompt = prompt_template.format(**prompt_mapping)
        formatted_video_prompt = video_prompt_template.format(**prompt_mapping)
        logger.info(f"formatted_image_prompt is {formatted_image_prompt}")
        contents = [formatted_image_prompt]
        image_part = genai_types.Part.from_uri(
            file_uri=normalize_bucket_uri(setting_image_url), mime_type="image/png"
        )        
        contents.append("setting image:")
        contents.append(image_part)

        image_part = genai_types.Part.from_uri(
            file_uri=normalize_bucket_uri(model_images), mime_type="image/png"
        )        
        contents.append("model image:")
        contents.append(image_part)

        image_part = genai_types.Part.from_uri(
            file_uri=normalize_bucket_uri(product_image_path), mime_type="image/png"
        )        
        contents.append("product image:")
        contents.append(image_part)

        images = []
        if images:
            contents.append(Image.open(io.BytesIO(images[0])))
        
        safety_settings = PROTOTYPE_SAFETY_SETTINGS
        
        try:
          use_global = "gemini-3" in IMAGE_MODEL_NAME
          location_used = "global" if use_global else LOCATION
          client = get_genai_client(use_global=use_global)
          selected_product = tool_context._invocation_context.session.state.get('product')
          product_image_path = selected_product['media']['main_image_url']
      
          response = client.models.generate_content(
              model=IMAGE_MODEL_NAME,
              contents=contents,
              config=genai_types.GenerateContentConfig(
                  image_config=genai_types.ImageConfig(aspect_ratio="9:16"),
                  safety_settings=safety_settings,
              ),
          )
          logger.info(response.text)
          
          storage_client = storage.Client()
          bucket_name = f"creative-content_{PROJECT_ID}"
          gcs_folder=get_or_create_unique_session_id(tool_context)

          bucket = storage_client.bucket(bucket_name)
          # Unique name for each moodboard
          social_file_name = f"social_{model_name}_{base64.urlsafe_b64encode(os.urandom(6)).decode()}.png"
          destination_blob_name = f"{gcs_folder}/social_media/{social_file_name}"

          for part in response.parts:
              if part.inline_data and part.inline_data.data:
                  image_bytes_out = part.inline_data.data
                  blob = bucket.blob(destination_blob_name)
                  blob.upload_from_string(image_bytes_out, content_type="image/png")

                  # Generate and upload thumbnail
                  try:
                      thumb_img = Image.open(io.BytesIO(image_bytes_out))
                      # Target height of 500, allowing width to scale accordingly (assuming aspect ratio < 4:1)
                      thumb_img.thumbnail((2000, 500))
                      thumb_io = io.BytesIO()
                      thumb_img.save(thumb_io, format="PNG")
                      thumb_bytes = thumb_io.getvalue()
                      
                      min_blob_name = destination_blob_name.replace(".png", "_min.png")
                      min_blob = bucket.blob(min_blob_name)
                      min_blob.upload_from_string(thumb_bytes, content_type="image/png")
                      logger.info(f"Thumbnail '{min_blob_name}' successfully saved.")
                  except Exception as e:
                      logger.error(f"Failed to create/upload thumbnail: {e}")

                  
                  logger.info(f"Image '{destination_blob_name}' successfully saved to GCS bucket '{bucket_name}'.")
                  
                  public_url = f"https://storage.cloud.google.com/{bucket_name}/{min_blob_name}"
                  social_media_urls.append(public_url)
                  logger.info(f"Generated Social Media Image: {public_url}")
        except Exception as e:
            logger.error(f"Social Media Image generation failed for model {model_name}: {e}")
              
        return formatted_image_prompt, formatted_video_prompt, social_media_urls[0]

    @log_function_call
    async def product_research(self, product_data: Product, trend_data: Trend, tool_context: ToolContext) -> str:
        logger.info(f"product_research {product_data}")
        logger.info(f"trend_data {trend_data}")
        selected_product = tool_context._invocation_context.session.state.get('product')
        product_image_path = selected_product['media']['main_image_url']
            
        
        
        brand_data: Brand = await self._load_brand_data_from_json(selected_product)
        logger.info(f"brand_data is {brand_data}")        
        style_name = "N/A"
        if brand_data.social_media_model.model_social_media_styles and len(brand_data.social_media_model.model_social_media_styles) > 0:
            style_name = brand_data.social_media_model.model_social_media_styles[0].style_name
        formatted_style_name = style_name.lower().replace(" ", "_").lower()
        prompt_template = load_prompt_file_from_calling_agent(prompt_filename=f"../prompts/social_{formatted_style_name}_product_research.md")        
        
        # Helper to join lists safely
        def format_list(item_list):
            return ", ".join(item_list) if item_list else "N/A"

        # Helper to format dicts
        def format_dict(item_dict):
             return "\n".join([f"- {k}: {v}" for k, v in item_dict.items()]) if item_dict else "N/A"

        # Map Attributes
        prompt_mapping = {
            # PRODUCT
            "product_name": product_data['core_identifiers']['product_name'],
            "color_name": product_data['attributes']['color_name'] or "N/A",
            "material": product_data['attributes']['material'] or "N/A",
            "fit_type": product_data['attributes']['fit_type'] or "N/A",
            "short": product_data['description']['short'] or "N/A",
            "long": product_data['description']['long'] or "N/A",
            # TREND
            "trend_name": trend_data['trend_name'],
            # "trend_scope": trend_data['trend_scope'] if trend_data['trend_scope'] else "N/A",
            "social_media_tags": format_list(trend_data['social_media_tags']) if trend_data['social_media_tags'] else "N/A",
            "key_influencer_handles": format_list(trend_data['key_influencer_handles']) if trend_data['key_influencer_handles'] else "N/A",
            "essential_look_characteristics": format_dict(trend_data['essential_look_characteristics']) if trend_data['essential_look_characteristics'] else "N/A",
            "primary_aesthetic": trend_data['taxonomy_attributes']['primary_aesthetic'] if trend_data['taxonomy_attributes']['primary_aesthetic'] else "N/A",
            "secondary_aesthetic": trend_data['taxonomy_attributes']['secondary_aesthetic'] if trend_data['taxonomy_attributes']['secondary_aesthetic'] else "N/A",
            "key_garments": format_list(trend_data['taxonomy_attributes']['key_garments']) if trend_data['taxonomy_attributes']['key_garments'] else "N/A",
            "materials_and_textures": format_list(trend_data['taxonomy_attributes']['materials_and_textures']) if trend_data['taxonomy_attributes']['materials_and_textures'] else "N/A",
            "color_palette": format_list(trend_data['taxonomy_attributes']['color_palette']) if trend_data['taxonomy_attributes']['color_palette'] else "N/A",
            "target_occasion": format_list(trend_data['taxonomy_attributes']['target_occasion']) if trend_data['taxonomy_attributes']['target_occasion'] else "N/A",
            # "marketing_attributes": trend_data['marketing_attributes'].model_dump_json(indent=2) if trend_data['marketing_attributes'] else "N/A",
            # BRAND
            "brand": brand_data.name,
        }

        filled_prompt = prompt_template.format(**prompt_mapping)

        images = []
        if product_image_path:
             # Normalize URI if needed
             norm_uri = normalize_bucket_uri(product_image_path)
             if norm_uri:
                 try:
                     bucket_name = norm_uri.replace("gs://", "").split("/")[0]
                     source_blob_name = norm_uri.replace(f"gs://{bucket_name}/", "")
                     image_bytes = download_blob_to_bytes(bucket_name, source_blob_name)
                     images.append(Image.open(io.BytesIO(image_bytes)))
                 except Exception as e:
                     logger.error(f"Failed to download product image for research: {e}")
        
        config = genai_types.GenerateContentConfig(
            **STANDARD_GENERATION_CONFIG,
        )
        log_message(f"Filled prompt: {filled_prompt}", Severity.INFO)
        client = get_genai_client()
        
        contents = [filled_prompt]
        if images:
            contents.extend(images)

        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=contents,
            config=config,
        )
        return response.text

