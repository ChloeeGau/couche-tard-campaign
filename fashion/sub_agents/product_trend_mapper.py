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

class ProductTrendMapper:
    trendlist = None

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



    def _get_product_by_sku(self, tool_context: ToolContext, sku: str) -> dict[str, any]:
        # def _get_product_by_sku(self, tool_context: InvocationContext, sku: str) -> Optional[Product]:
        print(f"calling _get_product_by_sku with sku: {sku}")
        opportunities = tool_context._invocation_context.session.state.get("opportunities")
        print(f"opportunities: {opportunities}")
        if not opportunities:
            print()
            return Product().__dict__
        for product_listing in opportunities:
            if product_listing['core_identifiers']['sku'] == sku:
                print(f"Found product listing with sku: {sku}")
                # tool_context._invocation_context.session.state['product'] = product_listing
                # tool_context._invocation_context.session.state['product'] = product_listing
                return product_listing
        return Product().__dict__

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

    def _after_model_callback(
        self,
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        print("AFTER MODEL CALLBACK")
        agent_name = callback_context.agent_name
        invocation_id = callback_context.invocation_id
        LOGGING_PREFIX = "AfTeR"
        print("PLLPLEASE WORK")
        print(f"trendlist: {self.trendlist}")
        i = 0
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
        # products = retrieve_products()
        # print(f"products: {products}")
        # callback_context.state['product'] = products[0]
        # callback_context.state['matching_trends'] = ['biker chic']
        # print(callback_context.state["purchase_history"])
        print("DONE PRINTING")
        return None
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

    # TODO move this to a shared utils file 
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

        normalized_uri = await self.normalize_bucket_uri(image_gcs_file_path)
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

    async def retrieve_image_from_gcs(self, product: Product, image_path: str, tool_context: ToolContext) -> str:
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
        await self.load_image_into_artifact(product, tool_context, image_path)
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
            from fashion.schema import CoreIdentifiers, Attributes, Categorization, CommercialStatus, Media, Description
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

    async def generate_trend_image(self, product: Product, tool_context: ToolContext) -> str:
        """
        Generates an image based on the matching trends stored in the tool_context's session state.
        """
        matching_trends = tool_context._invocation_context.session.state.get("matching_trends")
        if not matching_trends:
            logging.warning("No matching trends found in session state for image generation.")
            return ""

        # Assuming matching_trends is a list of strings (trend names/descriptions)
        prompt_description = f"""
            Prompt: Modular Trend Profile Series
        
            Role: Fashion Trend Analyst & UI Designer Objective: Create a clean, modular infographic titled "Trend Report." The design must visualize 6 distinct Trend Profiles (3 Micro, 3 Macro) derived from the provided dataset.

            Input Data: 
            {matching_trends}

            Constraint:

            NO Product Data: Ignore all specific product details (price, SKU, images).

            NO Connections: Do not draw arrows or lines between trends. Treat each trend as an independent data point.

            Design Layout Strategy: "The Grid System" (Card-based layout).

            Top Section: "Micro Trends" (3 Cards horizontally).

            Bottom Section: "Macro Trends" (3 Cards horizontally).

            Style: Clean, editorial, highly readable. Like a high-end fashion forecast PDF.
        """
        IMAGE_MODEL = "gemini-3-pro-image-preview"
        use_global = "gemini-3" in IMAGE_MODEL
        location_used = "global" if use_global else LOCATION
        client = get_genai_client(use_global=use_global)
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
        contents = [prompt_description]
        trend_board_url = ""
        print(f"sending prompt: {prompt_description}")
        try:
            # Assuming the client has an async method `generate_image` that takes a prompt
            # and returns a URL or path to the generated image.
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
                    safety_settings=safety_settings,
                ),
            )
            storage_client = storage.Client()
            bucket_name = "creative-content"
            bucket = storage_client.bucket(bucket_name)
            # Unique name for each moodboard
            product_trend_file_name = f"{product['core_identifiers']['sku']}_trends.png"
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
                    
            return trend_board_url
        except Exception as e:
            logging.error(f"Failed to generate image for trends '{matching_trends}': {e}")
            return ""

    async def map_product_to_trends_demo(self, static_mapping_data: dict) -> ProductTrendMapping:
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

        return ProductTrendMapping(**static_mapping_data)
    
    async def map_product_to_trends(self, product: Product, image_path: str, tool_context: ToolContext) -> ProductTrendMapping:
        """
        Maps a product to relevant micro and macro trends using Gemini.
        """
        # try:
        image_path = await self.normalize_bucket_uri(image_path)
        print(f"Mapping product to trends: {product} {image_path}")
        
        prompt_content = [
            f"Product: {product}\n",
            "Analyze this product and identify relevant trends. Provide 3 micro trends and 3 macro trends that this product fits into. For each match, provide a Match Score, Reasoning, and a full TrendAnalysis object (including trend_name, executive_summary, trend_start_date, trend_scope, trend_lifecycle_stage, primary_sources, taxonomy_attributes, search_vectors, and visual_assets).\n"
        ]
        
        if image_path:
            logging.info(f"Adding image to prompt: {image_path}")
            image_part = genai_types.Part.from_uri(
                file_uri=image_path, mime_type="image/png"
            )
            prompt_content.append(image_part)

        config = genai_types.GenerateContentConfig(
            **STANDARD_GENERATION_CONFIG,
            response_schema=ProductTrendMapping,
        )
        
        GEMINI_MODEL_NAME = "gemini-3-flash-preview"
        use_global = "gemini-3" in GEMINI_MODEL_NAME
        location_used = "global" if use_global else LOCATION
        client = get_genai_client(use_global=use_global)

        # client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt_content,
            config=config,
        )
        print(response.text)
        result = None
        if response.parsed:
                if isinstance(response.parsed, ProductTrendMapping):
                    result = response.parsed
                else:
                    result = ProductTrendMapping(**response.parsed)
        else:
            data = json.loads(response.text)
            result = ProductTrendMapping(**data)
        
        # Populate product in TrendMatch objects
        # if result:
        #     for match in result.micro_trends:
        #         match.product = product
        #     for match in result.macro_trends:
        #         match.product = product
        
        
        # await tool_context.save_artifact("matching_trends", result)
        # print(f"session state: {tool_context._invocation_context.session.state}")
        matching_trends = tool_context._invocation_context.session.state.get("matching_trends")
        # print(f"matching trends: {matching_trends}")
        tool_context._invocation_context.session.state['matching_trends'] = result
        matching_trends = tool_context._invocation_context.session.state.get("matching_trends")
        print(f"matching trends after save: {matching_trends}")
        # tool_context.session.state[current_question_index] = result
        # tool_context.session.save()
        print(f"result: {result}")
        self.trendlist = result
        return result
            
        # except Exception as e:
        #     logging.error(f"Product Trend Mapping Failed: {e}")
        #     from fashion.schema import TaxonomyAttributes
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