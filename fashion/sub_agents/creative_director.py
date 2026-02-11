from fashion.schema import Trend, Scene, CreativeDirection
from fashion.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from fashion.config import GEMINI_MODEL_NAME, IMAGE_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG, PROTOTYPE_SAFETY_SETTINGS
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
from fashion.adk_common.utils.utils_agents import get_genai_client
from fashion.adk_common.utils.utils_gcs import download_blob_to_bytes
from typing import Optional
from fashion.adk_common.utils.utils_gcs import normalize_bucket_uri 
from google.adk.agents.llm_agent import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest





class CreativeDirector:
    creative_direction = None

    @log_function_call
    def __init__(self):
        self.prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/creative_director.md")
        print(self.prompt_template)
        #   except Exception as e:
        #       logging.error(f"Failed to load product_trend_mapper prompt: {e}")
        self.agent = Agent(
          name="creative_director",
          model=GEMINI_MODEL_NAME,
          instruction=self.prompt_template,
          tools=[
            self.create_video_scenes,
            self.generate_scene_image,
          ],
          after_model_callback=self._after_model_callback,
          before_model_callback=self._before_model_callback
      )





    @log_function_call
    def create_video_scenes(self, product_image_path: str, trend_data: dict) -> CreativeDirection:
        """
        Generates video scene concepts based on product and trend.
        Returns a JSON string containing the creative direction and scenes.
        """
        try:
            print(f"Creative Director: Creating video scenes for product: {product_image_path}, trend data: {trend_data}")
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

            scene_prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/creative_director_scenes.md")

            # Step 1: Generate the Scene Concepts using Gemini
            prompt_content = [
                scene_prompt_template,
                f"\n\nTrend Data: {trend_data}",
                "Product Image:"
            ]
            
            # Load product image bytes for Gemini
            try:
                product_image_path = normalize_bucket_uri(product_image_path)
                if product_image_path:
                    image_part = genai_types.Part.from_uri(
                        file_uri=product_image_path, mime_type="image/png"
                    )
                    prompt_content.append(image_part)

                config = genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7, # Balanced creativity,
                    response_schema=CreativeDirection,
                )
              
            except Exception as e:
                logging.error(f"Failed to load product image for prompt generation: {e}")
                return None
              
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt_content,
                config=config,
            )
            
            creative_direction = response.text.strip()
            logging.info(f"Generated Creative Direction: {creative_direction}")
            self.creative_direction = creative_direction
            return creative_direction

        except Exception as e:
            logging.error(f"Creative Director Failed: {e}")
            return None

    @log_function_call
    def _before_model_callback(
        self,
        callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        print("BEFORE MODEL CALLBACK")  
        return None

    @log_function_call
    def _after_model_callback(
        self,
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        print("AFTER MODEL CALLBACK")
        agent_name = callback_context.agent_name
        invocation_id = callback_context.invocation_id
        print(f"creative_direction: {self.creative_direction}")
        i = 0
        if llm_response.content:
            for part in llm_response.content.parts:
                if part.text:
                    print(f"Response Part {i}: {part.text}")
                    # if "Product Attributes" in part.text:
                    #     callback_context.state['matching_trends'] = part.text
                #     print("Product Attributes found")
                # elif "core_identifiers" in part.text:
                #     cleaned_json_string = part.text.replace("```json\n", "").replace("\n```", "")
                #     print(f"cleaned_json_string: {cleaned_json_string}")
                #     # callback_context.state['product'] = json.loads(cleaned_json_string)
                #     print("Product found")
                i += 1
        if i > 0:
            callback_context.state['creative_direction'] = self.creative_direction

        return None  # Allow the model call to proceed
    @log_function_call
    def generate_scene_image(self, product_image_path: str, scenes: List[Scene]) -> List[str]:
        """
        Generates visualizations for scenes based on the product and scene descriptions.
        """
        print(f"generate_scene_image: {product_image_path}")
        print(f"scenes: {scenes}")
        generated_paths = []
        # try:
        
        # Download product image (once)
        images = []
        product_image_path = normalize_bucket_uri(product_image_path)
        print(f"product_image_path: {product_image_path}")
        if product_image_path.startswith("gs://"):
            bucket_name = product_image_path.replace("gs://", "").split("/")[0]
            source_blob_name = product_image_path.replace(f"gs://{bucket_name}/", "")
            image_bytes = download_blob_to_bytes(bucket_name, source_blob_name)
            images.append(image_bytes)
        else:
              logging.warning("Product image path is not likely a GCS URI (gs://), attempting to use as is provided it is local or generic.")
        
        if not images:
            return []

        product_image = Image.open(io.BytesIO(images[0]))
        
        for scene in scenes:
            # try:
              print(f"scene: {scene}")

              prompt = f"""
              Generate a high-fidelity fashion image based on the following scene description:
              
              **Setting:** {scene['setting']}
              **Lighting:** {scene['lighting_style']}
              **Camera:** {scene['camera_movement']} (Translate this to a visual angle/composition)
              **Styling:** {scene['styling_details']}
              **Action:** {scene['action']}
              
              **Important:** The image must prominently feature the product shown in the input image.
              """
              
              contents = [
                  prompt,
                  product_image,
              ]
              
              safety_settings = PROTOTYPE_SAFETY_SETTINGS
              use_global = "gemini-3" in IMAGE_MODEL_NAME
              location_used = "global" if use_global else LOCATION
              client = get_genai_client(use_global=use_global)

              response = client.models.generate_content(
                  model=IMAGE_MODEL_NAME,
                  contents=contents,
                  config=genai_types.GenerateContentConfig(
                      safety_settings=safety_settings,
                      image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
                  ),
              )
              
              if response.parts:
                  for part in response.parts:
                      if part.inline_data and part.inline_data.data:
                          image_bytes = part.inline_data.data

                          # Process image to add header
                          original_img = Image.open(io.BytesIO(image_bytes))
                          
                          # Define header properties
                          header_height = 220
                          width, height = original_img.size
                          new_height = height + header_height
                          
                          # Create new image with white background
                          new_img = Image.new('RGB', (width, new_height), 'white')
                          
                          # Draw header text
                          draw = ImageDraw.Draw(new_img)
                          
                          # Try to load a nicer font, fallback to default
                          try:
                              font = ImageFont.truetype("Arial.ttf", 20)
                              title_font = ImageFont.truetype("Arial.ttf", 30)
                          except IOError:
                              font = ImageFont.load_default()
                              title_font = ImageFont.load_default()

                          # Paste original image
                          new_img.paste(original_img, (0, header_height))

                          # Draw Text
                          padding = 20
                          current_y = padding
                          
                          # Title
                          draw.text((padding, current_y), f"SCENE {scene['scene_id']}", font=title_font, fill='black')
                          current_y += 40
                          
                          # Details
                          details = [
                              f"Setting: {scene['setting']}",
                              f"Action: {scene['action']}",
                              f"Lighting: {scene['lighting_style']}",
                              f"Camera: {scene['camera_movement']}",
                              f"Styling: {scene['styling_details'][:100]}..." if len(scene['styling_details']) > 100 else f"Styling: {scene['styling_details']}"
                          ]
                          
                          for line in details:
                              draw.text((padding, current_y), line, font=font, fill='black')
                              current_y += 25

                          # Save the image
                          output_dir = "generated_campaigns"
                          if not os.path.exists(output_dir):
                              os.makedirs(output_dir)
                          
                          # Use scene_id in filename for tracking
                          file_name = f"scene_{scene['scene_id']}_{base64.urlsafe_b64encode(os.urandom(6)).decode()}.png"
                          output_path = f"{output_dir}/{file_name}"
                          
                          new_img.save(output_path)
                          
                          logging.info(f"Generated Scene {scene['scene_id']} Image: {output_path}")
                          

                          print("valid repsonse checkpoint 2")
                          storage_client = storage.Client()
                          bucket_name = f"creative-content_{PROJECT_ID}"
                          bucket = storage_client.bucket(bucket_name)
                          destination_blob_name = f"scenes/{file_name}"

                          blob = bucket.blob(destination_blob_name)
                          img_byte_arr = io.BytesIO()
                          new_img.save(img_byte_arr, format='PNG')
                          img_bytes = img_byte_arr.getvalue()
                          blob.upload_from_string(img_bytes, content_type="image/png")
                          
                          

                          # Generate and save thumbnail
                          thumbnail_height = 500
                          aspect_ratio = new_img.width / new_img.height
                          thumbnail_width = int(thumbnail_height * aspect_ratio)
                          thumbnail_img = new_img.resize((thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS)
                          
                          min_file_name = file_name.replace(".png", "_min.png")
                          min_output_path = f"{output_dir}/{min_file_name}"
                          thumbnail_img.save(min_output_path)
                          
                          # Upload thumbnail
                          min_destination_blob_name = f"scene/{min_file_name}"
                          min_blob = bucket.blob(min_destination_blob_name)
                          
                          min_img_byte_arr = io.BytesIO()
                          thumbnail_img.save(min_img_byte_arr, format='PNG')
                          min_img_bytes = min_img_byte_arr.getvalue()
                          
                          min_blob.upload_from_string(min_img_bytes, content_type="image/png")
                          print(f"Thumbnail '{min_destination_blob_name}' saved.")
                          gs_path = f"gs://{bucket_name}/{min_destination_blob_name}"
                          cloud_path = f"https://storage.cloud.google.com/{bucket_name}/{min_destination_blob_name}"
                          generated_paths.append(cloud_path)
                          print(f"displaying image: {cloud_path}")
                          print(
                              f"Thumbnail '{gs_path}' successfully saved to GCS bucket '{cloud_path}'."
                          )
                            
            # except Exception as e:
            #     logging.error(f"Failed to generate image for scene {scene['scene_id']}: {e}")
            #     continue

        return generated_paths

        # except Exception as e:
        #     logging.error(f"Scene Image Generation Failed: {e}")
        #     return generated_paths
