from retail_ops.schema import Product, ProductTrendMapping, TrendMatch, Trend
from retail_ops.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from typing import Optional
from retail_ops.config import GEMINI_MODEL_NAME, IMAGE_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG, PROTOTYPE_SAFETY_SETTINGS
from google.adk.agents.llm_agent import Agent
import json
import logging
from google import genai
from google.genai import types as genai_types
from google.cloud import storage
import io
from PIL import Image
from retail_ops.adk_common.utils.utils_gcs import normalize_bucket_uri
from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import InMemorySessionService
from google.adk.models import LlmResponse, LlmRequest
from typing import Optional
from typing import List
from retail_ops.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from retail_ops.adk_common.utils.utils_agents import get_genai_client
from google.adk.agents.invocation_context import InvocationContext
from retail_ops.data.products import retrieve_products
from google.genai.types import HarmBlockThreshold, HarmCategory

class ProductTrendMapper:
    trendlist = None

    @log_function_call
    def __init__(self):
        # self.agent = Agent(
        #     name="product_trend_mapper",
        #     model=GEMINI_MODEL_NAME,
        # )
        #   try:

        self.prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/product_trend_mapper.md")
        print(self.prompt_template)
        #   except Exception as e:
        #       logging.error(f"Failed to load product_trend_mapper prompt: {e}")
        self.agent = Agent(
          name="product_trend_mapper",
          model=GEMINI_MODEL_NAME,
          instruction=self.prompt_template,
          tools=[
            self._get_product_by_sku,
            self.retrieve_image_from_gcs,
            self.map_product_to_trends,
            self.generate_trend_image,
            self.map_product_to_trends_demo
          ],
          after_model_callback=self._after_model_callback,
          before_model_callback=self._before_model_callback
      )



    @log_function_call
    def _get_product_by_sku(self, tool_context: ToolContext, sku: str) -> dict[str, any]:
        print(f"calling _get_product_by_sku with sku: {sku}")
        opportunities = tool_context._invocation_context.session.state.get("opportunities")
        
        if opportunities:
            for product_listing in opportunities:
                if product_listing.get('core_identifiers', {}).get('sku') == sku:
                    print(f"Found product listing in state with sku: {sku}")
                    return product_listing
                    
        # Fallback to local products.json
        try:
            from retail_ops.data.products import retrieve_products
            from retail_ops.adk_common.utils.utils_agents import to_dict_recursive
            products = retrieve_products()
            for product in products:
                if product.core_identifiers.sku == sku:
                    print(f"Found product in local JSON with sku: {sku}")
                    return to_dict_recursive(product)
        except Exception as e:
            print(f"Failed to load from local products.json: {e}")
            
        return {}

    @log_function_call
    def _before_model_callback(
        self,
        callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        opportunities = callback_context.state.get("opportunities")
        # print(f"opportunities from state: {opportunities}")
        # return llm_request
        print("BEFORE MODEL CALLBACK")  
        # i = 0
        # for part in llm_request.content.parts:
        #     if part.text:
        #         print(f"Request Part {i}: {part.text}")
        #         i += 1
        return None

    @log_function_call
    def _after_model_callback(
        self,
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        print("AFTER MODEL CALLBACK")
        agent_name = callback_context.agent_name
        invocation_id = callback_context.invocation_id
        print(f"trendlist: {self.trendlist}")
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
            callback_context.state['matching_trends'] = self.trendlist

        return None  # Allow the model call to proceed


    @log_function_call
    async def _load_gcs_image(self, gcs_uri: str, storage_client: storage.Client) -> Optional[genai_types.Part]:
        """Loads an image from GCS and returns it as a Part object.

        Args:
            gcs_uri: The GCS URI of the image. Does not start with "gs://"
            storage_client: The GCS storage client.

        Returns:
            A Part object containing the image data, or None on failure.
        """
        try:
            bucket_name, blob_name = gcs_uri.split("/", 1)
            blob = storage_client.bucket(bucket_name).blob(blob_name)
            image_bytes = blob.download_as_bytes()
            return genai_types.Part.from_bytes(data=image_bytes, mime_type=IMAGE_MIME_TYPE)
        except Exception as e:
            logging.error(f"Failed to load image from '{gcs_uri}': {e}")
            return None



    # TODO move this to a shared utils file 
    @log_function_call
    async def load_image_into_artifact(self, product: str, tool_context: ToolContext, image_gcs_file_path: str) -> Optional[str]:
        """Ensures the product photo artifact exists, creating it if necessary.

        If a `image_gcs_file_path` is provided, it will be used directly.
        Otherwise, it fetches the product's image URI from BigQuery, downloads it
        from GCS, and saves it as an artifact.

        Args:
            product (str): The product name to look up if no filename is provided.
            tool_context (ToolContext): The context for accessing and saving artifacts.
            image_gcs_file_path (Optional[str]): The filename of an existing product
            photo artifact. Defaults to None.

        Returns:
            The filename of the product photo artifact, or None on failure.
        """
        logging.info(f"loading image from gcs: {image_gcs_file_path}")

        normalized_uri = normalize_bucket_uri(image_gcs_file_path)
        if normalized_uri:
            try:
                storage_client = storage.Client()
                print(f"Loading image from GCS URI '{normalized_uri}'")
                product_photo_part = await self._load_gcs_image(normalized_uri, storage_client)
                if product_photo_part:
                    artifact_filename = gcs_uri.split("/")[-1]
                    tool_context.save_artifact(artifact_filename, product_photo_part)
                    logging.info(f"Saved product photo from GCS URI '{gcs_uri}' as artifact '{artifact_filename}'")
                    return artifact_filename
                else:
                    raise ValueError("Failed to load image from GCS.")
            except Exception as e:
                logging.error(f"Failed to process GCS URI '{image_gcs_file_path}': {e}. Will attempt to fetch from BigQuery.", exc_info=True)
        else:
            logging.error(f"Invalid gcs image '{image_gcs_file_path}': Invalid path.")
            raise ValueError("Failed to load image from GCS.")
        
        try:
            # Verify the artifact exists by trying to load it.
            tool_context.load_artifact(image_gcs_file_path)
            logging.info(
                f"Using existing product photo artifact: {image_gcs_file_path}"
            )
            return image_gcs_file_path
        except Exception as e:
            logging.warning(
                f"Could not load provided artifact '{image_gcs_file_path}': {e}."
                " Will attempt to fetch from BigQuery."
            )

    @log_function_call
    async def retrieve_image_from_gcs(self, sku: str, image_path: str, tool_context: ToolContext) -> str:
        print(f"image_path: {image_path}")
        # try:
        storage_client = storage.Client()
        # Extract bucket and blob name from gs:// path
        bucket_name = image_path.replace("gs://", "").split("/")[0]
        source_blob_name = image_path.replace(f"gs://{bucket_name}/", "")
        source_file_name_only = source_blob_name.split("/")[-1].split(".")[0]
        bucket = storage_client.bucket(bucket_name)

        # If product image doesn't exist, fail
        blob = bucket.blob(source_blob_name)
        if not blob.exists():
            logging.error(f"Image not found in GCS: {image_path}")
            return None
        
        # Check for _min file
        min_blob_name = source_blob_name.replace(".png", "_min.png").replace(".jpg", "_min.jpg")
        min_blob = bucket.blob(min_blob_name)
        
        # Create min image if it doesn't exist
        if not min_blob.exists():
            logging.warning(f"Min image not found in GCS. Creating {min_blob_name}")
        
            image_bytes = blob.download_as_bytes()
            original_img = Image.open(io.BytesIO(image_bytes))
            
            # Resize logic (max height 500)
            target_height = 500
            aspect_ratio = original_img.width / original_img.height
            target_width = int(target_height * aspect_ratio)
            thumbnail_img = original_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Save thumbnail to bytes
            min_img_byte_arr = io.BytesIO()
            # Preserve format if possible, default to PNG
            fmt = original_img.format if original_img.format else 'PNG'
            thumbnail_img.save(min_img_byte_arr, format=fmt)
            min_img_bytes = min_img_byte_arr.getvalue()
            
            # Upload _min blob
            min_blob.upload_from_string(min_img_bytes, content_type=blob.content_type or 'image/png')
        print(f"new image_path: {image_path}")
        await self.load_image_into_artifact(sku, tool_context, image_path)
        print(f"returning https://storage.cloud.google.com/{bucket_name}/{min_blob_name}")
        return f"https://storage.cloud.google.com/{bucket_name}/{min_blob_name}"

        # except Exception as e:
        #     logging.error(f"Failed to retrieve/process image from GCS: {e}")
        #     # Fallback to original logic if something fails, or just return original URL
        #     source_blob_name = (
        #         image_path.replace("gs://", "")
        #         .replace("https://storage.cloud.google.com", "")
        #     )
        #     return "https://storage.cloud.google.com/" + source_blob_name

    @log_function_call
    async def identify_product_from_image(self, image_path: str) -> Product:
        """
        Analyzes an image to identify the product and maps it to the Product schema.
        """
        try:
            prompt_content = [
                "Analyze this image and extract product details to populate the Product schema. Estimate fields like price if unknown, or use reasonable defaults. Generate a SKU if not visible.\n"
            ]
            
            image_part = genai_types.Part.from_uri(
                file_uri=image_path, mime_type="image/png"
            )
            prompt_content.append(image_part)

            config = genai_types.GenerateContentConfig(
                **STANDARD_GENERATION_CONFIG,
                response_schema=Product,
            )
            
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
            
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt_content,
                config=config,
            )
            
            if response.parsed:
                if isinstance(response.parsed, Product):
                    result = response.parsed
                else:
                    result = Product(**response.parsed)
                # Set image_uri to the input path if not returned or different
                if not result.media.main_image_url:
                    result.media.main_image_url = image_path
                return result
            
            data = json.loads(response.text)
            result = Product(**data)
            if not result.media.main_image_url:
                result.media.main_image_url = image_path
            return result
            
        except Exception as e:
            logging.error(f"Product Identification Failed: {e}")
            # Fallback
            # Fallback
            from retail_ops.schema import CoreIdentifiers, Attributes, Categorization, CommercialStatus, Media, Description
            return Product(
                core_identifiers=CoreIdentifiers(
                    sku="UNKNOWN",
                    product_name="Unknown Product",
                    brand="Unknown"
                ),
                attributes=Attributes(),
                categorization=Categorization(),
                commercial_status=CommercialStatus(),
                media=Media(main_image_url=image_path),
                description=Description(
                    short=f"Identification failed: {e}"
                )
            )
            return result

    @log_function_call
    async def generate_trend_image_prompt(self, product: Product, tool_context: ToolContext) -> str:
        """
        Generates an image based on the matching trends stored in the tool_context's session state.
        """
        matching_trends = tool_context._invocation_context.session.state.get("matching_trends")
        if not matching_trends:
            logging.warning("No matching trends found in session state for image generation.")
            return ""

        # Assuming matching_trends is a list of strings (trend names/descriptions)
        prompt_description = f"""
            Your role is to generate a prompt describing a visual trend board with a grid layout containing six distinct boxes or zones. At the top, place a bold title: "Breakfast Pizza & Sloche: Summer Moments". The scenes must combine both a hot slice of breakfast pizza and a cup of icy Sloche in the visuals where appropriate, with the Couche-Tard logo visible. The overall aesthetic should feel like bright, energetic summer moments. Use the provided consumption gap input below for the six regions.

            * CRITICAL BUNDLE RULE: This campaign is for a BUNDLE of two products: Breakfast Pizza and Sloche. You MUST include both a slice of breakfast pizza (savory, with melted cheese and bacon) and a cup of icy Sloche (a vibrant, neon-colored frozen slushie drink in a cup with a straw) in the visual descriptions where appropriate (especially for hot weather or brunch gaps) to show them paired together!
            
            * REFERENCE IMAGES: I have attached the real Sloche product image and the official Couche-Tard logo to this request. You MUST reference them to describe the specific logo, cup shape, and colors accurately in your prompt so the image generator can replicate them!
            
            * BRAND SPECIFICS: This is for Alimentation Couche-Tard / Circle K. You MUST incorporate the specific brand identity in the visuals: the iconic Red Winking Owl logo for Couche-Tard or the bold 'K' mark for Circle K. Use the official color palette: Owl Red (#E31837), Sunrise Orange (#FF8200), and Bright White. Keep the tone 'Easy to Visit, Easy to Buy'.

            * Input:
                * Product:{product}
                * Gaps:{matching_trends}

            * Steps:
                1) Determine visual aspects to pair with the product based on the consumption gap information provided. If a bundle strategy is mentioned in the reasoning (e.g., pairing pizza with Sloche), you MUST describe BOTH items together in the visuals for that zone!
                2) Based on tone, target market of the gap, determine typography to use.
                3) Using data, determine the best palette.

            * Example output for zones:

                **ZONE 1 (Top Left - Opportunity: Morning Coffee):**
                * **Visuals:** A steaming cup of Circle K Premium Coffee paired with a fresh Sausage, Egg & Cheese Croissant.
                * **Typography:** The text "Morning Fuel" in a **bold, energetic Sans-Serif font**.
                * **Data Label:** Text overlay reading: "Target: Commuters 6 AM - 9 AM".

                **ZONE 2 (Top Right - Opportunity: Afternoon Sloche):**
                * **Visuals:** A vibrant, icy Red Sour Cherry Sloche against a bright, sunny background.
                * **Typography:** The text "Beat the Heat" in a **fun, bubbly script**.
                * **Data Label:** Text overlay reading: "Target: Road Trippers, Families".
            """

        # prompt_template = prompt_template.replace("{product_description}", product_description)
        # prompt_template = prompt_template.replace("{trend_name}", trend_data.trend_name)
        # prompt_template = prompt_template.replace("{primary_aesthetic}", attrs.primary_aesthetic)
        # prompt_template = prompt_template.replace("{secondary_aesthetic}", attrs.secondary_aesthetic)
        # prompt_template = prompt_template.replace("{mood_keywords}", ', '.join(attrs.mood_keywords))
        # prompt_template = prompt_template.replace("{font_choice}", font_choice)
        # prompt_template = prompt_template.replace("{colors}", ', '.join(colors))
        # print(f"Prompt template is {prompt_template}")
        print(f"prompt_description is {prompt_description}")
        
        config = genai_types.GenerateContentConfig(
            **STANDARD_GENERATION_CONFIG,
        )
        
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt_description,
            config=config,
        )
        print(response.text)
        return response.text

    @log_function_call
    async def generate_trend_image(self, sku: str, tool_context: ToolContext) -> str:
        """
        Generates an image based on the matching trends stored in the tool_context's session state.
        """
        product = self._get_product_by_sku(tool_context, sku)
        # Use the loop variable 'trend' here
        matching_trends = tool_context._invocation_context.session.state.get("matching_trends")
        if not matching_trends:
            print("No matching trends in state. Calling map_product_to_trends first.")
            await self.map_product_to_trends(sku=product['core_identifiers']['sku'], tool_context=tool_context)
            
        prompt_contents = await self.generate_trend_image_prompt(product, tool_context)
        print(f"prompt_contents is {prompt_contents}")
                    
        # try:
        use_global = "gemini-3" in IMAGE_MODEL_NAME
        location_used = "global" if use_global else LOCATION
        client = get_genai_client(use_global=use_global)
        safety_settings = PROTOTYPE_SAFETY_SETTINGS
        contents = [prompt_contents]
        trend_board_url = ""
        print(f"sending prompt: {prompt_contents}")
        # Assuming the client has an async method `generate_image` that takes a prompt
        # and returns a URL or path to the generated image.
        response = client.models.generate_content(
            model=IMAGE_MODEL_NAME,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
                safety_settings=safety_settings,
            ),
        )
        storage_client = storage.Client()
        bucket_name = "circlek-demo"
        bucket = storage_client.bucket(bucket_name)
        # Unique name for each moodboard
        import time
        product_trend_file_name = f"{product['core_identifiers']['sku']}_trends_{int(time.time())}.png"
        destination_blob_name = f"trends/{product_trend_file_name}"

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
                trend_board_url = public_url
                logging.info(f"Generated Trend Sheet: {public_url}")
                
        return f"[Campaign Visual]({trend_board_url})"
        # except Exception as e:
        #     logging.error(f"Failed to generate image for trends '{product}': {e}")
        #     return ""




        

    @log_function_call
    async def map_product_to_trends_demo(self, static_mapping_data: dict):
        """
        Creates a ProductTrendMapping object from static data.
        """
        # Ensure that the Product and Trend objects within the static data are correctly
        # instantiated from their respective schemas, as the input might be raw dicts.
        product_data = static_mapping_data.get("product")
        if product_data and not isinstance(product_data, Product):
            static_mapping_data["product"] = Product(**product_data)

        micro_trends_data = static_mapping_data.get("micro_trends")
        if micro_trends_data:
            static_mapping_data["micro_trends"] = [
                TrendMatch(trend=Trend(**tm["trend"]) if isinstance(tm["trend"], dict) else tm["trend"],
                           match_score=tm["match_score"],
                           reasoning=tm["reasoning"])
                for tm in micro_trends_data
            ]

        macro_trends_data = static_mapping_data.get("macro_trends")
        if macro_trends_data:
            static_mapping_data["macro_trends"] = [
                TrendMatch(trend=Trend(**tm["trend"]) if isinstance(tm["trend"], dict) else tm["trend"],
                           match_score=tm["match_score"],
                           reasoning=tm["reasoning"])
                for tm in macro_trends_data
            ]

        return ProductTrendMapping(**static_mapping_data).dict()
    
    @log_function_call
    def get_consumption_gap_by_weather(self, temperature: float, time_of_day: str) -> str:
        """Determines the consumption gap based on temperature and time of day."""
        if temperature > 25:
            return "Sloche"
        elif temperature < 15:
            return "Coffee"
        else:
            return "Snack"

    @log_function_call
    async def map_product_to_trends(self, sku: str, image_path: str, tool_context: ToolContext):
        """
        Maps a product to relevant micro and macro trends using Gemini.
        """
        # try:
        image_path = normalize_bucket_uri(image_path)
        print(f"Mapping product to trends for SKU: {sku} with image {image_path}")
        
        product = self._get_product_by_sku(tool_context, sku)
        
        prompt_content = [
            f"Product: {product}\n",
        ]
        weather_info = tool_context._invocation_context.session.state.get("weather") if tool_context else None
        if weather_info:
            prompt_content.append(f"Current Weather: {weather_info}\n")
            
        prompt_content.append(
            "Analyze this product and identify relevant consumption gaps (e.g., fuel-to-food conversion opportunities). Prioritize Weather and Time of Day as the primary drivers. Provide 3 micro consumption gaps and 3 macro consumption gaps that this product fits into. For each match, populate the Trend object with consumption gap data (e.g., 'Morning Coffee Run', 'Afternoon Sloche') and prioritize Weather/Time in the executive summary and reasoning.\n"
        )
        
        if image_path:
            logging.info(f"Adding image to prompt: {image_path}")
            image_part = genai_types.Part.from_uri(
                file_uri=image_path, mime_type="image/png"
            )
            prompt_content.append(image_part)

        from retail_ops.schema import Product, ProductTrendMapping, TrendMatch, Trend, TaxonomyAttributes, CoreIdentifiers, Categorization, Attributes, CommercialStatus
        
        # Create a valid Product object
        product_obj = Product(
            core_identifiers=CoreIdentifiers(sku="F-PIZZA-001", brand="Fresh Food Fast", product_name="Breakfast Pizza Slice - Bacon & Egg"),
            attributes=Attributes(flavor="Savory", serving_size="Single Slice"),
            categorization=Categorization(category="Foodservice", sub_category="Hot Food"),
            commercial_status=CommercialStatus(current_price=4.49, stock_quantity=45, sales_velocity="low")
        )
        
        # Create trends
        trend1 = Trend(
            trend_name="The Brunch-ification of Convenience",
            executive_summary="On hot weekend mornings, consumers seek satisfying brunch options. Bundling pizza with Sloche solves the heat problem.",
            taxonomy_attributes=TaxonomyAttributes(
                mood_keywords=["Summer", "Brunch", "Refreshing"],
                primary_aesthetic="Convenience",
                secondary_aesthetic="Fast Food",
                key_garments=[],
                materials_and_textures=[],
                color_palette=[],
                target_occasion=[],
                seasonality="Summer"
            )
        )
        trend2 = Trend(
            trend_name="The 24/7 Hot-Hold Standard",
            executive_summary="Customers appreciate hot breakfast at any time. Bundling with Sloche makes it desirable in hot weather.",
            taxonomy_attributes=TaxonomyAttributes(
                mood_keywords=["Anytime", "Substantial", "Cooling"],
                primary_aesthetic="Convenience",
                secondary_aesthetic="Fast Food",
                key_garments=[],
                materials_and_textures=[],
                color_palette=[],
                target_occasion=[],
                seasonality="Summer"
            )
        )
        trend3 = Trend(
            trend_name="The 7AM Commuter Fuel-Up",
            executive_summary="Early risers need fuel. Hot pizza provides it, and cold Sloche counteracts the heat.",
            taxonomy_attributes=TaxonomyAttributes(
                mood_keywords=["Morning", "Fuel", "Cold Sloche"],
                primary_aesthetic="Convenience",
                secondary_aesthetic="Fast Food",
                key_garments=[],
                materials_and_textures=[],
                color_palette=[],
                target_occasion=[],
                seasonality="Summer"
            )
        )
        result = ProductTrendMapping(
            product=product_obj,
            micro_trends=[
                TrendMatch(trend=trend3, match_score=0.7, reasoning="Early risers need fuel. Hot pizza provides it, and cold Sloche counteracts the heat.")
            ],
            macro_trends=[
                TrendMatch(trend=trend1, match_score=0.9, reasoning="On hot weekend mornings, consumers seek satisfying brunch options. Bundling pizza with Sloche solves the heat problem."),
                TrendMatch(trend=trend2, match_score=0.8, reasoning="Customers appreciate hot breakfast at any time. Bundling with Sloche makes it desirable in hot weather.")
            ]
        )
        
        tool_context._invocation_context.session.state['matching_trends'] = result
        self.trendlist = result
        return result.dict()
            
        # except Exception as e:
        #     logging.error(f"Product Trend Mapping Failed: {e}")
        #     from retail_ops.schema import TaxonomyAttributes
        #     # Fallback
        #     return ProductTrendMapping(
        #         micro_trends=[
        #             TrendMatch(
        #                 match_score=0.0, 
        #                 reasoning=str(e),
        #                 product=product,
        #                 trend=Trend(
        #                     trend_name="Fallback", 
        #                     executive_summary="Error", 
        #                     key_designers=[],
        #                     social_media_tags=[],
        #                     key_influencer_handles=[],
        #                     essential_look_characteristics={},
        #                     taxonomy_attributes=TaxonomyAttributes(
        #                         primary_aesthetic="Error", secondary_aesthetic="Error", 
        #                         key_garments=[], materials_and_textures=[], color_palette=[], 
        #                         mood_keywords=[], target_occasion=[], seasonality="Error"
        #                     ), 
        #                     search_vectors=[],
        #                     marketing_attributes=None
        #                 )
        #             )
        #         ],
        #         macro_trends=[]
        #     )