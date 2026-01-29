from typing import List
from fashion.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
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
from fashion.schema import Product, ProductTrendMapping, TrendMatch, Trend, Brand
from fashion.data.brands import retrieve_brands
from fashion.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from urllib.parse import urlparse, unquote

_genai_client = None
_genai_client_global = None  # For gemini-3 models that require global location
_storage_client = None
def get_genai_client(use_global: bool = False):
    """Get or create the GenAI client.
    
    Args:
        use_global: If True, use 'global' location for gemini-3 models
    """
    global _genai_client, _genai_client_global
    
    if use_global:
        if _genai_client_global is None:
            _genai_client_global = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location="global",  # gemini-3 models require global location
            )
        return _genai_client_global
    else:
        if _genai_client is None:
            _genai_client = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=LOCATION,
            )
        return _genai_client

class ArtDirector:
    selected_product:Product = None
    
    def __init__(self):
        # self.agent = Agent(
        #     name="product_trend_mapper",
        #     model=GEMINI_MODEL_NAME,
        # )
      
      self.prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/art_director.md")
      self.agent = Agent(
          name="art_director",
          model=GEMINI_MODEL_NAME,
          instruction=self.prompt_template,
          tools=[
            self.create_moodboards,
            # self.create_campaign_directive
          ],
          after_model_callback=self._after_model_callback,
          before_model_callback=self._before_model_callback
          
      )

    def _before_model_callback(
        self,
        callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        # matching_trends = callback_context.state.get("matching_trends")
        # print(f"matching_trends from state: {matching_trends}")
        selected_product = callback_context.state.get('product')
        # with open("./purchase_history.json", "r") as f:
        #     purchase_data = json.load(f)
        # TDO
        # purchase_data = json.loads(purchase_history_json)
        # callback_context.state["purchase_history"] = purchase_data
        # # current_agent = callback_context.agent
        # # current_agent.purchase_list = purchase_data
        # callback_context.purchase_list = purchase_data
        # print("_before_model_callback IS")
        # print(callback_context.state["purchase_history"])
        # agent_name = callback_context.agent_name
        # invocation_id = callback_context.invocation_id
        # # llm_prompt = _stringify_llm_request(llm_request)
        # callback_context.state["test"] = "hello world"

        # print(f"Before Model Callback")
        # print(f"Starting Mgent: {agent_name} (Inv: {invocation_id})")
        # print(f"LLM Prompt: {llm_prompt}")

        return None  # Allow the model call to proceed

    def _after_model_callback(
        self,
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        agent_name = callback_context.agent_name
        invocation_id = callback_context.invocation_id
        LOGGING_PREFIX = "AfTeR"
        print("PLLLEASE WORK")
        # print(callback_context.state["purchase_history"])
        print(f"{LOGGING_PREFIX} After Model Callback")
        print(f"{LOGGING_PREFIX} Exiting Agent: {agent_name} (Inv: {invocation_id})")
        print(llm_response)
        print("DONE PRINTING")
        # print("1")
        # print(llm_response.content.parts[0].text)
        # print("2")
        # print(llm_response.content.parts[0])
        # print("3")
        # # callback_context.state["purchase_history"] = llm_response.content.parts[0].text
        # # callback_context.state["purchase_history"] = llm_response.content.parts[0].text

        # if "purchase_history" in callback_context.state:
        #     print(callback_context.state["purchase_history"])
        # purchase_data = json.loads(purchase_history_full_json)
        # callback_context.state["purchase_history"] = purchase_data
        # if "purchase_history" in callback_context.state:
        #     print(callback_context.state["purchase_history"])
        # # current_agent = callback_context.agent
        # # current_agent.purchase_list = purchase_data
        # # callback_context.purchase_list = purchase_data
        # print("_after_model_callback IS")
        # print(callback_context.state["purchase_history"])

        return None  # Allow the model call to proceed

    async def download_blob_to_bytes(self, bucket_name, source_blob_name):
        """Downloads a blob from the bucket to bytes."""

        # Initialize the client
        # (Client looks for credentials in the GOOGLE_APPLICATION_CREDENTIALS env var)
        storage_client = storage.Client()

        # Get the bucket and the blob
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)

        # Download content as bytes
        blob_data = blob.download_as_bytes()

        print(f"Downloaded blob {source_blob_name} ({len(blob_data)} bytes).")

        return blob_data

    async def _generate_style_guide_prompt_old(self, trend_data: Trend, product_description: str = "") -> str:
        
        attrs = trend_data['taxonomy_attributes']
        
        # --- DYNAMIC INJECTION LOGIC ---
        
        # 1. Hallucinate Fonts based on Aesthetic (Simple logic for demo, can be expanded)
        aesthetic = attrs['primary_aesthetic'].lower()
        if "utility" in aesthetic:
            font_choice = "DIN Pro or Roboto Mono"
        elif "romantic" in aesthetic:
            font_choice = "Didot or Playfair Display"
        elif "futuristic" in aesthetic:
            font_choice = "Eurostile or Helvetia"
        else:
            font_choice = "Helvetica Neue"

        # 2. Hallucinate Hex Codes (The LLM usually does this, but we simulate it here for the prompt template)
        # In a real agent workflow, you'd ask the LLM to pick these.
        colors = attrs['color_palette']
        prompt_template = ""

        prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/graphic_designer.md")
            
        # Constructing the message to the LLM
        llm_instruction = f"""
            Please write an Image Generation Prompt for a Brand Board.
        
            Data to use:
            - Trend: {trend_data['trend_name']}
            - Aesthetic Keywords: {attrs['primary_aesthetic']}, {attrs['secondary_aesthetic']}
            - Moods: {', '.join(attrs['mood_keywords'])}
            - Suggested Font: {font_choice}
            - Color List: {', '.join(colors)} (Please convert these to Hex codes in the prompt)
            # - Product: {product_description}
        
            Style: 
            * A minimalist flat vector brand guideline sheet, presented in the International Typographic Style (Swiss Design)
            * Attempt to align the design with the aesthetic of the trend.
            * Use of modular grid layout for images is preferred
            * While the required sections are important, they should take up less visual space than the rest of the design
            * Logo: genereate a brand logo that is simple and modern, and that aligns with the aesthetic of the trend. Place logo at the top left of the page.
            * Brand Name: The brand name should be placed at the top right of the page.
            * Brand Tagline: The brand tagline should be placed smaller font directly below the brand name.
            * Trend Name: The trend name should be placed at top of the page, centered.

            Required Sections: In addition to other elements, the following two sections are required:
            1. **Palette Section (label:'Palette'):** Square color swatches labeled with large bold text: [Insert Generated Hex Codes].
            2. **Typography Section (label:'Typography'):** A type specimen poster displaying the alphabet in '{font_choice}' font. 
            3. **Mood Keywords:** Mood keywords should be incorporate into the design. It doesn't need to have a dedicated section, but should be reflected in the overall design.


            Imagery Requirements (multiple images should be used, but the following are required):
            1. **Product Image:** One image should be of the product
            2. **Textures:** Multiple textures should be used to represent the materials and textures, taking into consideration {', '.join(attrs['materials_and_textures'])}
            3. **Accessories Image:** One image should represent associated accessories that match the style of the trend. This single image should represent multiple accessories.
            4. **Scene:** One image should represent a scene (without people) based on the trend occasions: {', '.join(attrs['target_occasion'])}
        
            **Crucial**: 
            * None of the images should be labeled. 
            * Only label sections if designated in the prompt.
        
            Apply these to the 'Brand Style Guide' prompt structure defined in your system instructions.
        """
        # prompt_template = prompt_template.replace("{product_description}", product_description)
        # prompt_template = prompt_template.replace("{trend_name}", trend_data.trend_name)
        # prompt_template = prompt_template.replace("{primary_aesthetic}", attrs.primary_aesthetic)
        # prompt_template = prompt_template.replace("{secondary_aesthetic}", attrs.secondary_aesthetic)
        # prompt_template = prompt_template.replace("{mood_keywords}", ', '.join(attrs.mood_keywords))
        # prompt_template = prompt_template.replace("{font_choice}", font_choice)
        # prompt_template = prompt_template.replace("{colors}", ', '.join(colors))
        # print(f"Prompt template is {prompt_template}")
        print(f"llm_instruction is {llm_instruction}")
        
        config = genai_types.GenerateContentConfig(
            **STANDARD_GENERATION_CONFIG,
        )
        
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=llm_instruction,
            config=config,
        )
        print(response.text)
        return response.text
    #   return prompt_template
    #   return llm_instruction

    async def _generate_style_guide_prompt(self, brand_data: Brand, trend_data: Trend, product_image_path: str) -> str:
        
        attrs = trend_data['taxonomy_attributes']
        
        colors = attrs['color_palette']
        prompt_template = ""

        prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/graphic_designer.md")
        # TODO check for existince of these values to avoid errors
        aesthetic_keywords = attrs['primary_aesthetic']
        if 'secondary_aesthetic' in attrs:
            aesthetic_keywords += f", {attrs['secondary_aesthetic']}"



        # Constructing the message to the LLM
        example_moodboard_location = f"gs://creative-content/brands/{brand_data.brand_identifier}/moodboard_{brand_data.brand_identifier}.png"
        logo_location = f"gs://creative-content/brands/{brand_data.brand_identifier}/logo_{brand_data.brand_identifier}.png"
        llm_instruction = f"""
            Please write an Image Generation Prompt for a Brand Board, for the specified fashion trend, highlighting the product provided in the image.

            Brand Data:
            - Brand: {brand_data.name}
            - Brand Photography and Art Direction: {brand_data.photography_and_art_direction}
            - Brand Voice and Tone: {brand_data.voice_and_tone}
            - Brand Visual Identity: {brand_data.visual_identity}            

            Trend Data:
            - Trend: {trend_data['trend_name']}
            - Aesthetic Keywords: {aesthetic_keywords}
            - Moods: {', '.join(attrs['mood_keywords'])}
            - Color List: {', '.join(colors)} (Please convert these to Hex codes in the prompt)

            Product Data:
            - Product Image Path: {product_image_path}

            Style: 
            * Evaluate the moodboard stored at {example_moodboard_location} to create a similar style moodboard.

            Required Sections: In addition to other elements, the following two sections are required:
            1. **Palette Section (label:'Palette'):** Square color swatches labeled with large bold text: [Insert Generated Hex Codes].
            2. **Typography Section (label:'Typography'):** A type specimen poster displaying the alphabet in '{brand_data.visual_identity.typography}' font. 
            3. **Mood Keywords:** Mood keywords should be incorporate into the design. It doesn't need to have a dedicated section, but should be reflected in the overall design.


            Imagery Requirements (multiple images should be used, but the following are required):
            * **Product Image:** One image should be of the product
            * **Textures:** Multiple textures should be used to represent the materials and textures, taking into consideration {', '.join(attrs['materials_and_textures'])}
            * **Accessories Image:** One image should represent associated accessories that match the style of the trend. This single image should represent multiple accessories.
            """
        if "target_occasion" in attrs:
            llm_instruction += f"""
            * **Scene:** One image should represent a scene (without people) based on the trend occasions: {', '.join(attrs['target_occasion'])}
            """
        
        llm_instruction += f"""
            * **Logo:** Do not attempt to make a logo. Instead, include the brand logo found here: {logo_location}
            
            **Crucial**: 
            * None of the images should be labeled. 
            * Only label sections if designated in the prompt.
        
            Apply these to the 'Brand Style Guide' prompt structure defined in your system instructions.
        """
        print(f"llm_instruction is {llm_instruction}")
        
        config = genai_types.GenerateContentConfig(
            **STANDARD_GENERATION_CONFIG,
        )
        
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=llm_instruction,
            config=config,
        )
        print(response.text)
        return response.text
    #   return prompt_template
    #   return llm_instruction
        
    async def load_trend_data(self, tool_context: ToolContext) -> List[Trend]:
        artifact_trend_data = tool_context.load_artifact("matching_trends")
        raw_data_bytes = artifact_trend_data.inline_data.data
        trend_data = raw_data_bytes.decode("utf-8")
        print(f"artifact trend_data is {trend_data}")
        
        return trend_data


    async def _load_brand_data_from_json(self, selected_product) -> Brand:
        brand_name_str = selected_product['core_identifiers']['brand']
        
        # Assuming self.retrieve_brands() returns a list of dictionaries,
        # where each dictionary represents a brand and has a 'name' key.
        all_brands = retrieve_brands()
        print(f"all_brands is {all_brands}")
        for brand in all_brands:
            if brand.name == brand_name_str:
                return brand

    async def normalize_bucket_uri(self, url: str) -> Optional[str]:
        """Normalizes GCS URLs to gs:// format."""
        print(f"normalize_bucket_uri: {url}")
        if not url:
            return None
        if url.startswith("gs://"):
            print("ALREADY GS")
            return url

        parsed = urlparse(url)
        path = unquote(parsed.path)

        # Handle virtual hosted style: bucket.storage.googleapis.com
        if parsed.netloc.endswith(".storage.googleapis.com") and parsed.netloc != "storage.googleapis.com":
            bucket = parsed.netloc.replace(".storage.googleapis.com", "")
            obj = path.lstrip("/")
            return f"gs://{bucket}/{obj}"

        # Handle path style: storage.googleapis.com or storage.cloud.google.com
        if parsed.netloc in ["storage.googleapis.com", "storage.cloud.google.com"]:
            # Path is /bucket/object...
            clean_path = path.lstrip("/")
            if "/" in clean_path:
                bucket, obj = clean_path.split("/", 1)
                return f"gs://{bucket}/{obj}"

        return None

    async def create_moodboards(self, trend_data: List[Trend], tool_context: ToolContext) -> List[str]:
        """
        Generates moodboard options for a campaign based on trend data.
        """
        # trend_data = [trend]
        # trend_data = None
        # all_matching_trends = tool_context._invocation_context.session.state.get("matching_trends")
        # if all_matching_trends:
        #     for trend in all_matching_trends:
        #         if (hasattr(trend, 'name') and trend.name == trend_name) or \
        #            (isinstance(trend, dict) and trend.get('name') == trend_name):
        #             trend_data = [trend]
        #             break
        
        # if len(trend_data) == 0:
        #     trend_data = tool_context._invocation_context.session.state.get("matching_trends")

        # client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        IMAGE_MODEL = "gemini-3-pro-image-preview"
        use_global = "gemini-3" in IMAGE_MODEL
        location_used = "global" if use_global else LOCATION
        client = get_genai_client(use_global=use_global)
        print(f"session state: {tool_context._invocation_context.session.state}")
        print(f"trend_data is {trend_data}")    
        selected_product = tool_context._invocation_context.session.state.get('product')
        print(f"selected_product is {selected_product}")
        print(f"selected_product.media is {selected_product['media']}")
        product_image_path = selected_product['media']['main_image_url']
            
        brand_data: Brand = await self._load_brand_data_from_json(selected_product)
        print(f"brand_data is {brand_data}")
        # Download product image once if provided
        images = []
        if product_image_path:
            print(f"gcs_image is {product_image_path}")
            product_image_path = await self.normalize_bucket_uri(product_image_path)
            print(f"normalized gcs_image is {product_image_path}")
            try:
                bucket_name = (
                    product_image_path.replace("gs://", "").split("/")[0]
                )
                source_blob_name = (
                    product_image_path.replace(f"gs://{bucket_name}/", "")
                )
                print(f"bucket_name is {bucket_name}")
                print(f"source_blob_name is {source_blob_name}")
                image_bytes = await self.download_blob_to_bytes(bucket_name, source_blob_name)
                images.append(image_bytes)
            except Exception as e:
                logging.error(f"Failed to download product image: {e}")
        
        moodboard_urls = []

        for trend in trend_data:
            print(f"trend is {trend}")
            attrs = trend['taxonomy_attributes']
            colors = attrs['color_palette']
            
            # Use the loop variable 'trend' here
            prompt_contents = await self._generate_style_guide_prompt(brand_data, trend, product_image_path)
            logo_location = f"gs://creative-content/brands/{brand_data.brand_identifier}/logo_{brand_data.brand_identifier}.png"
            prompt_contents += (
                f"""

                **CRUCIAL**: 
                * None of the images should be labeled. 
                * Product Image: One image should be of the product {product_image_path}
                * Incorporate some of the following colors into the design: {', '.join(colors)}
                * Do not attempt to make a logo. Instead, include the brand logo below: 
                """
            )
            logging.info(f"Adding logo to prompt: {logo_location}")
            image_part = genai_types.Part.from_uri(
                file_uri=logo_location, mime_type="image/png"
            )            
            print(f"prompt_contents is {prompt_contents}")
            
            contents = [prompt_contents, image_part]
            if images:
                contents.append(Image.open(io.BytesIO(images[0])))
            
            safety_settings: list = [
                genai_types.SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.OFF,
                ),
            ]
            
            try:
                response = client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
                        safety_settings=safety_settings,
                    ),
                )
                print(response.text)
                
                storage_client = storage.Client()
                bucket_name = "creative-content"
                bucket = storage_client.bucket(bucket_name)
                # Unique name for each moodboard
                moodboard_file_name = f"moodboard_{trend['trend_name'].replace(' ', '_')}_{base64.urlsafe_b64encode(os.urandom(6)).decode()}.png"
                destination_blob_name = f"moodboards/{moodboard_file_name}"

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
                            print(f"Thumbnail '{min_blob_name}' successfully saved.")
                        except Exception as e:
                            logging.error(f"Failed to create/upload thumbnail: {e}")

                        
                        print(f"Image '{destination_blob_name}' successfully saved to GCS bucket '{bucket_name}'.")
                        
                        public_url = f"https://storage.cloud.google.com/{bucket_name}/{min_blob_name}"
                        moodboard_urls.append(public_url)
                        logging.info(f"Generated Moodboard: {public_url}")
            except Exception as e:
                logging.error(f"Moodboard generation failed for trend {trend['trend_name']}: {e}")
                continue

        return moodboard_urls

    async def create_campaign_directive(self, product_image_path: str, trend_data: Trend) -> str:
        """
        Generates a creative directive (image prompt) for a campaign based on product and trend.
        """
        try:
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

            # Step 1: Generate the Image Prompt using Gemini
            prompt_content = [
                self.prompt_template,
                f"\n\nTrend Data: {trend_data.model_dump_json()}",
                "Product Image:"
            ]
            
            # Load product image bytes for Gemini
            try:
                if product_image_path:
                    image_part = genai_types.Part.from_uri(
                        file_uri=product_image_path, mime_type="image/png"
                    )
                    prompt_content.append(image_part)

                config = genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7, # Slightly higher for creativity
                )
                
            except Exception as e:
                logging.error(f"Failed to load product image for prompt generation: {e}")
                return None
                
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt_content,
                config=config,
            )
            
            art_direction = response.text.strip()
            logging.info(f"Generated Art Direction: {art_direction}")
            return art_direction

        except Exception as e:
            logging.error(f"Art Director Failed: {e}")
            return None