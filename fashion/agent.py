# import logging

# from fashion.config import PROJECT_ID, LOCATION, GEMINI_MODEL_NAME
# from fashion.tools.inventory import InventoryTool
# from fashion.tools.sales import SalesTool
# # from fashion.tools.asset import AssetTool
# # from fashion.sub_agents.trend import TrendAgent
# from fashion.sub_agents.trend_spotter import TrendSpotter
# from fashion.sub_agents.fashion_photographer import FashionPhotographer
# from fashion.sub_agents.art_director import ArtDirector
# from fashion.sub_agents.creative_director import CreativeDirector
# from fashion.sub_agents.product_trend_mapper import ProductTrendMapper
# # from fashion.tools.campaign import CampaignTool
# from google.adk.agents import Agent
# from google.adk.tools import AgentTool
# from fashion.tools.video_generation_prompt import generate_video_prompt
# from google.adk.sessions import InMemorySessionService
# from typing import List
# from fashion.schema import Product, ProductTrendMapping, TrendMatch, Trend, ProductList
# from google.adk.agents.callback_context import CallbackContext
# # from google.adk.caching import InvocationContext
# from google.adk.agents.invocation_context import InvocationContext

# import uuid

# session_service = InMemorySessionService()
# logger = logging.getLogger(__name__)



# def create_davos_fashion_agent() -> Agent:
#     agent = Agent(
#         name=agent_settings.agent_name,
#         model="gemini-2.5-flash", # Defaulting to a capable model
#         instruction="greet the user",
#         description="a fashion agent",
#     )

#     return agent

#     # except Exception as e:
#     #     logger.error(f"Failed to create {agent_settings.agent_name}: {e}")
#     #     raise RuntimeError(f"Failed to create agent: {str(e)}")


# from fashion.config import AgentSettings

# # try:
# # Try to load settings from environment
# agent_settings = AgentSettings()
# agent = create_davos_fashion_agent()
# logger.info(f"{agent_settings.agent_name} initialized successfully")
# # except Exception as e:
# #     logger.error(f"Failed to create agent: {e}")
# #     raise RuntimeError(f"Failed to create agent: {str(e)}")

# # Export with both names for ADK and AgentSpace compatibility
# root_agent = agent
# __all__ = ["agent", "root_agent", "create_davos_fashion_agent"]









import logging
from fashion.config import PROJECT_ID, LOCATION, GEMINI_MODEL_NAME
from fashion.tools.inventory import InventoryTool
from fashion.tools.sales import SalesTool
# from fashion.tools.asset import AssetTool
# from fashion.sub_agents.trend import TrendAgent
from fashion.sub_agents.trend_spotter import TrendSpotter
from fashion.sub_agents.fashion_photographer import FashionPhotographer
from fashion.sub_agents.art_director import ArtDirector
from fashion.sub_agents.creative_director import CreativeDirector
from fashion.sub_agents.product_trend_mapper import ProductTrendMapper
from fashion.sub_agents.campaign_manager import CampaignManager
# from fashion.tools.campaign import CampaignTool
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from fashion.tools.video_generation_prompt import generate_video_prompt
from google.adk.sessions import InMemorySessionService
from typing import List
from fashion.schema import *
from google.adk.agents.callback_context import CallbackContext
# from google.adk.caching import InvocationContext
from google.adk.agents.invocation_context import InvocationContext
from fashion.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from PIL import Image, ImageDraw, ImageFont
import uuid
import io
from google.adk.tools import VertexAiSearchTool
import json
import os
from typing import Tuple, Any, Dict 
from fashion.data.products import retrieve_products
from google.cloud import storage
from fashion.config import AgentSettings

session_service = InMemorySessionService()

logger = logging.getLogger(__name__)

# async def create_session_example():
#     print("hiya")
#     session = await session_service.create_session(
#         app_name="my_app", user_id="test_user", session_id="123"
#     )
#     print(f"new session is {session}")
#     print(session.id)
#     return session

# # Initialize the session immediately so it's ready
# Generate a UUID object (Version 4, random)

async def create_session_example():
    session = await session_service.create_session(
        app_name="my_app", user_id="test_user", session_id="123"
    )
    print(f"new session is {session}")
    print(session.id)
    return session

# from fashion.sub_agents.product_trend_mapper_agent import ProductTrendMapperAgent
# Initialize Tools
inventory_tool = InventoryTool()
sales_tool = SalesTool()
# asset_tool = AssetTool()
# trend_agent = TrendAgent()
trend_spotter_agent = TrendSpotter()
fashion_photographer_agent = FashionPhotographer()
art_director_agent = ArtDirector()
creative_director_agent = CreativeDirector()
product_trend_mapper_agent = ProductTrendMapper()
campaign_manager_agent = CampaignManager()

# async def _dynamic_instruction_provider(
#     context: ReadonlyContext,
# ) -> str:
#     """Dynamically provides instructions to the agent by loading and formatting a prompt."""

#     prompt = utils_prompts.load_prompt_file_from_calling_agent(
#         {
#             "DEMO_COMPANY_NAME": DEMO_COMPANY_NAME,
#             "STORYTELLING_INSTRUCTIONS": STORYTELLING_INSTRUCTIONS,
#             "GCS_AUTHENTICATED_DOMAIN": utils_gcs.GCS_AUTHENTICATED_DOMAIN,
#             "GCS_AUTHENTICATED_DOMAIN_SANS_PROTOCOL": utils_gcs.GCS_AUTHENTICATED_DOMAIN_SANS_PROTOCOL,
#             "SESSION_ARTIFACTS_STATE": json.dumps(context.state.get(SESSION_ARTIFACTS_STATE_KEY, "{}"))
#         }
#     )
#     return prompt
    
# Define Tool Functions for the Agent (wrapper for tools)

# TODO: enhance the logic around determining velocity
# TODO: include sales plan information
def identify_inventory_opportunities(tool_context: InvocationContext) -> List[Product]:
    """Identifies high-stock, low-velocity inventory items."""
    high_stock_products = inventory_tool.find_high_stock()
    low_velocity_products = sales_tool.find_low_velocity()
    # Map SKU to Product for low velocity items
    low_velocity_map = {p.core_identifiers.sku: p for p in low_velocity_products}
    opportunities = []
    opportunities_as_dict = []
    for product in high_stock_products:
        # Access SKU via core_identifiers
        sku = product.core_identifiers.sku
        if sku in low_velocity_map:
            # Merge sales data into the high stock product
            sales_product = low_velocity_map[sku]
            # Assumes commercial_status exists on both
            if product.commercial_status and sales_product.commercial_status:
                product.commercial_status.sales_velocity = sales_product.commercial_status.sales_velocity
                product.commercial_status.sales_reasoning = sales_product.commercial_status.sales_reasoning
            opportunities.append(product)
            opportunities_as_dict.append(to_dict_recursive(product))
      
    # TODO look at putting this back, but serilization was an issue        
    tool_context.state["opportunities"] = opportunities_as_dict
    return opportunities_as_dict    

def to_dict_recursive(obj):
    # If the object is not a custom object (e.g., int, str, None, etc.), return it directly
    if not hasattr(obj, "__dict__"):
        return obj
    
    # If the object is a custom object, create a new dictionary
    result = {}
    for key, value in obj.__dict__.items():
        # Skip private attributes starting with '_' (optional, but good practice)
        if key.startswith("_"):
            continue
        
        # Recursively convert the value
        element = to_dict_recursive(value)
        result[key] = element
        
    return result



def generate_min_image(source_blob_name:str):
    print(f"source_blob_name: {source_blob_name}")
    storage_client = storage.Client()
    image_path = source_blob_name.strip()
    # Extract bucket and blob name from gs:// path
    bucket_name = image_path.replace("gs://", "").replace("https://storage.cloud.google.com/", "").split("/")[0]
    source_blob_name = image_path.replace(f"gs://{bucket_name}/", "").replace(f"https://storage.cloud.google.com/{bucket_name}/", "")
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
        target_height = 200
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
    print(f"min_blob_name: {min_blob_name}")
    return min_blob_name


# TODO: read from BQ instead of JSON
def load_brand_data(tool_context: InvocationContext):
    """Loads brand data from brands.json into the tool_context state."""
    try:
        file_path = os.path.join(os.path.dirname(__file__), "data", "brands.json")
        if not os.path.exists(file_path):
            # Fallback to current directory if not found in data
            file_path = os.path.join(os.path.dirname(__file__), "brands.json")
            
        with open(file_path, "r") as f:
            brand_data = json.load(f)
            tool_context.state["brand_data"] = brand_data
            logger.info("Brand data loaded successfully into state.")
            logger.info(f"Brand data: {tool_context.state['brand_data']}")
    except FileNotFoundError:
        logger.error(f"brands.json not found at {file_path}")
        tool_context.state["brand_data"] = {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from brands.json at {file_path}")
        tool_context.state["brand_data"] = {}
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading brand data: {e}")
        tool_context.state["brand_data"] = {}


# def get_product_by_sku(tool_context: InvocationContext, sku: str) -> dict[str, any]:
# def get_product_by_sku(tool_context: InvocationContext, sku: str) -> Tuple[dict[str, Any], dict[str, Any]]:
# TODO: move products to a database instead of json file
def get_product_by_sku(tool_context: InvocationContext, sku: str) -> dict:
    products = retrieve_products()
    for product in products:
        if product.core_identifiers.sku == sku:
            tool_context.state['product'] = to_dict_recursive(product)
            min_image = generate_min_image(product.media.main_image_url)
            brand_name = product.core_identifiers.brand
            brand_info = next((brand for brand in tool_context.state.get("brand_data", []) if brand.get("name") == brand_name), None)
            if brand_info:
                tool_context.state['brand_info'] = brand_info
                logger.info(f"Brand info for {brand_name} loaded successfully into state.")
            else:
                logger.warning(f"Brand info for {brand_name} not found in loaded data.")
            return to_dict_recursive(product), to_dict_recursive(tool_context.state['brand_info'])

    return to_dict_recursive(Product()),to_dict_recursive(Brand())
    
# def get_product_assets(sku: str):
#     """Retrieves catalog specs and imagery for a generic product."""
#     return asset_tool.get_catalog_specs(sku)

# def analyze_market_trends(product_context: str, image_path: str):
#     """
#     Analyzes current social media trends for the given product.
#     
#     Args:
#         product_context: Description or context of the product.
#         image_path: Optional path to an image of the product.
#     """
#     return trend_agent.analyze_social_trends(product_context, image_path)

def analyze_market_trends():
    """
    Analyzes current social media trends for the given product.
    
    """
    return trend_spotter_agent.spot_trends()


# def create_campaign_draft(product_name: str, trend_micro: str, trend_macro: str, audience: str):
#     """
#     Drafts a campaign based on the product and trend data.
#     """
#     # reconstruct trend object for internal tool use
#     from fashion.schema import TrendAnalysis
#     trend_obj = TrendAnalysis(
#         micro_trend=trend_micro,
#         macro_trend=trend_macro,
#         target_audience=audience,
#         keywords=[]
#     )
#     return campaign_tool.draft_campaign(product_name, trend_obj)

# def generate_campaign_video(campaign_name: str):
#     """Generates a video for the campaign."""
#     # This is a simplification; in reality we'd pass the full draft object or ID
#     return f"Video generation started for {campaign_name}..."

# Load Prompts
def load_prompt(filename: str) -> str:
    try:
        with open(f"fashion/prompts/{filename}", "r") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load prompt {filename}: {e}")
        return ""

system_instruction = load_prompt("instructions.md")
# system_instruction = load_prompt_file_from_calling_agent(prompt_filename="prompts/instructions_demo.md")
# Create Agent
# Note: In a real ADK app, you'd likely use a specific Model implementation (e.g., VertexAIModel)
# For this demo, we assume the environment is set up for the default model provider or use a placeholder.
# If ADK requires a specific model instance, we would instantiate it here.

# def retrieve_campaign():
    

# campaign_agent = Agent(
#     name='campaign_agent',
#     model="gemini-2.5-flash", # Defaulting to a capable model
#     instruction="greet the user",
#     description="Campaign Agent"
# )

#     return agent
# def create_davos_fashion_agent() -> Agent:
#     agent = Agent(
#         name=agent_settings.agent_name,
#         model="gemini-2.5-flash", # Defaulting to a capable model
#         instruction="greet the user",
#         description=agent_settings.agent_description
#     )
#     return agent

# def create_davos_fashion_agent_demo() -> Agent:
#     """Create and configure the primary cap compliance agent."""

#     # Create the main compliance agent
#     # try:
#     agent = Agent(
#         name=agent_settings.agent_name,
#         model=GEMINI_MODEL_NAME, # Defaulting to a capable model
#         instruction=system_instruction,
#         description=agent_settings.agent_description,
#         tools=[
#             # create_session_example,
#             identify_inventory_opportunities,
#             load_brand_data,
#             get_product_by_sku,
#             product_lifestyle_image_generator
#             # get_product_assets,
#             # analyze_market_trends,
#             AgentTool(agent=product_trend_mapper_agent.agent),
#             # product_trend_mapper_agent.retrieve_image_from_gcs,
#             # product_trend_mapper_agent.identify_product_from_image,
#             # product_trend_mapper_agent.map_product_to_trends,
#             # AgentTool(agent=ProductTrendMapperAgent().agent),

#             AgentTool(agent=trend_spotter_agent.agent),
#             AgentTool(agent=ArtDirector().agent),
#             # art_director_agent.create_moodboards,
#             # art_director_agent.create_campaign_directive,
#             fashion_photographer_agent.generate_campaign_image,
#             # creative_director_agent.create_video_scenes_demo,
#             creative_director_agent.create_video_scenes,
#             creative_director_agent.generate_scene_image,
#             # generate_video_prompt,
#             AgentTool(agent=campaign_manager_agent.agent),
#             # create_campaign_draft,
#             # generate_campaign_video
#         ]
#     )

#     logger.info(f"Successfully created {agent_settings.agent_name}")
#     return agent


def map_product_to_trends_demo() -> ProductTrendMapping:
    """
    Creates a ProductTrendMapping object from static data.
    """

    micro_trends_data=[
        TrendMatch(
            trend=Trend(
                trend_name='The Lady Jacket',
                moodboard_url="https://storage.cloud.google.com/creative-content/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
                executive_summary='A specific outerwear trend focusing on collarless, structured, often cropped jackets with decorative buttons and trim, bridging the gap between a cardigan and a blazer.',
                trend_start_date='2023-09-01',
                trend_scope='Global Fashion',
                trend_lifecycle_stage='Growth',
                primary_sources=['Vogue', 'Who What Wear', "Harper's Bazaar"],
                key_designers=[],
                social_media_tags=[],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Preppy',
                    secondary_aesthetic='Classic',
                    key_garments=['Tweed jackets', 'Cardigan-jackets', 'Collarless blazers'],
                    materials_and_textures=['Tweed', 'Boucle', 'Knit'],
                    color_palette=['Pastels', 'Cream', 'Navy'],
                    mood_keywords=['Polished', 'Sophisticated', 'Ladylike'],
                    target_occasion=['Work', 'Social Events', 'Brunch'],
                    seasonality='Transitional'
                ),
                search_vectors=None,
                visual_assets=VisualAssets(
                    google_images_url=None,
                    pinterest_url=None,
                    tiktok_search_url=None,
                    ai_generation_prompt='A high-fashion studio shot of a woman wearing a structured pink tweed lady jacket with gold buttons and braided trim, styled with high-waisted denim.'
                ),
                marketing_attributes=None
            ),
            match_score=0.98,
            reasoning="This product is the quintessential 'Lady Jacket' with its collarless design, patch pockets, and braided trim, which are the defining characteristics of this micro-trend."
        ),
        TrendMatch(
            trend=Trend(
                trend_name='Barbiecore',
                moodboard_url="https://storage.cloud.google.com/creative-content/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
                executive_summary='A vibrant, pink-centric aesthetic celebrating hyper-femininity and nostalgia, popularized by the Barbie movie and high-fashion runway collections.',
                trend_start_date='2022-06-01',
                trend_scope='Pop Culture & Fashion',
                trend_lifecycle_stage='Maturity',
                primary_sources=['TikTok', 'Instagram', 'Valentino Pink PP Collection'],
                key_designers=[],
                social_media_tags=[],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Barbiecore',
                    secondary_aesthetic='Girly',
                    key_garments=['Mini skirts', 'Platform heels', 'Tweed sets'],
                    materials_and_textures=['Satin', 'Tweed', 'Latex'],
                    color_palette=['Hot Pink', 'Bubblegum Pink', 'Pastel Pink'],
                    mood_keywords=['Playful', 'Bold', 'Feminine'],
                    target_occasion=['Parties', 'Social Media Content', 'Outing'],
                    seasonality='Spring/Summer'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.92,
            reasoning="The specific light pink hue and hyper-feminine silhouette align perfectly with the Barbiecore movement's focus on iconic feminine staples."
        ),
        TrendMatch(
            trend=Trend(
                trend_name='Modern Preppy',
                moodboard_url="https://storage.cloud.google.com/creative-content/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
                executive_summary='A contemporary update to traditional collegiate and country club styles, blending classic silhouettes with modern colors and relaxed styling.',
                trend_start_date='2023-01-01',
                trend_scope='Youth & Professional Fashion',
                trend_lifecycle_stage='Growth',
                primary_sources=['Pinterest', 'Street Style Blogs'],
                key_designers=[],
                social_media_tags=[],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Preppy',
                    secondary_aesthetic='Academic',
                    key_garments=['Blazers', 'Pleated skirts', 'Loafers'],
                    materials_and_textures=['Wool', 'Tweed', 'Cotton'],
                    color_palette=['Navy', 'Pink', 'Forest Green'],
                    mood_keywords=['Smart', 'Clean', 'Traditional'],
                    target_occasion=['Campus', 'Office', 'Weekend'],
                    seasonality='Fall/Spring'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.85,
            reasoning="The tweed material and structured fit are core to the preppy aesthetic, while the pink color provides the 'modern' twist required for this trend."
        )
    ]
    macro_trends_data = [
        TrendMatch(
            trend=Trend(
                trend_name='Quiet Luxury / Old Money',
                moodboard_url="https://storage.cloud.google.com/creative-content/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
                executive_summary='A shift towards understated elegance, high-quality craftsmanship, and timeless pieces that signal wealth through texture and fit rather than overt logos.',
                trend_start_date='2023-03-01',
                trend_scope='Global Luxury Market',
                trend_lifecycle_stage='Maturity',
                primary_sources=['Succession (TV Series)', 'Loro Piana', 'Brunello Cucinelli'],
                key_designers=[],
                social_media_tags=[],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Minimalist',
                    secondary_aesthetic='Classic',
                    key_garments=['Cashmere sweaters', 'Tailored trousers', 'Tweed jackets'],
                    materials_and_textures=['Cashmere', 'Silk', 'Tweed'],
                    color_palette=['Beige', 'Navy', 'Pastels'],
                    mood_keywords=['Refined', 'Expensive', 'Timeless'],
                    target_occasion=['Professional', 'Formal', 'Travel'],
                    seasonality='All-season'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.9,
            reasoning="The 'Chanel-esque' design of this jacket is a pillar of the 'Old Money' aesthetic, emphasizing heritage construction and a polished appearance."
        ),
        TrendMatch(
            trend=Trend(
                trend_name='Heritage Revival',
                moodboard_url="https://storage.cloud.google.com/creative-content/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
                executive_summary="A broad movement where consumers seek out items with historical significance, traditional craftsmanship, and 'investment piece' status.",
                trend_start_date='2022-10-01',
                trend_scope='Consumer Behavior',
                trend_lifecycle_stage='Growth',
                primary_sources=['WGSN', 'Business of Fashion'],
                key_designers=[],
                social_media_tags=[],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Vintage-Inspired',
                    secondary_aesthetic='Classic',
                    key_garments=['Trench coats', 'Tweed jackets', 'Quilted vests'],
                    materials_and_textures=['Tweed', 'Leather', 'Wool'],
                    color_palette=['Earth tones', 'Primary colors', 'Pastels'],
                    mood_keywords=['Nostalgic', 'Durable', 'Authentic'],
                    target_occasion=['Daily wear', 'Outdoor'],
                    seasonality='Fall/Winter'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.88,
            reasoning='Tweed is a heritage fabric, and this jacket references a design language established decades ago that remains a staple investment piece.'
        ),
        TrendMatch(
            trend=Trend(
                trend_name='Hyper-Femininity',
                moodboard_url="https://storage.cloud.google.com/creative-content/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
                executive_summary='A cultural shift reclaiming traditionally feminine symbols, colors, and silhouettes as a form of empowerment and self-expression.',
                trend_start_date='2023-05-01',
                trend_scope='Social & Fashion',
                trend_lifecycle_stage='Growth',
                primary_sources=['TikTok (Coquette aesthetic)', 'Runway Trends'],
                key_designers=[],
                social_media_tags=[],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Romantic',
                    secondary_aesthetic='Coquette',
                    key_garments=['Dresses', 'Tailored jackets', 'Bow-detailed tops'],
                    materials_and_textures=['Lace', 'Tweed', 'Silk'],
                    color_palette=['Pink', 'Lavender', 'White'],
                    mood_keywords=['Empowered', 'Soft', 'Decorative'],
                    target_occasion=['Social', 'Work', 'Dates'],
                    seasonality='Spring'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.92,
            reasoning="The jacket combines a 'power' silhouette (the structured jacket) with a soft, traditionally feminine color and texture, embodying the modern hyper-feminine movement."
        )
    ]
    product_data = Product(
        core_identifiers=CoreIdentifiers(
            sku='292929',
            upc='195551292929',
            brand='Modern Muse',
            product_name='Pink Tweed Jacket'
        ),
        attributes=Attributes(
            size='Medium',
            color_name='Light Pink',
            color_hex='#F7C4C8',
            material='Tweed',
            fit_type='Classic Fit',
            care_instructions='Dry clean only'
        ),
        categorization=Categorization(
            department='Women',
            category='Apparel',
            sub_category='Outerwear',
            collection='Ready-to-Wear'
        ),
        commercial_status=CommercialStatus(
            currency='USD',
            msrp=495.0,
            current_price=450.0,
            cost_price=180.0,
            in_stock=True,
            stock_quantity=85,
            sales_velocity='low',
            sales_reasoning='High price point and niche aesthetic may lead to slower turnover compared to basics.'
        ),
        media=Media(
            main_image_url='https://storage.cloud.google.com/creative-content/catalog/top/292929.png',
            web_image_url='https://storage.cloud.google.com/creative-content/catalog/top/292929_min.png',
            gallery_urls=[],
            alt_text='Front view of a light pink tweed jacket with a collarless design, braided trim, and four patch pockets with gold logo buttons.'
        ),
        description=Description(
            short='An iconic tweed jacket in a soft light pink hue.',
            long='Crafted with the legendary savoir-faire of the House of , this jacket is a masterpiece of textile and tailoring. Made from a luxurious light pink tweed, it offers a structured yet comfortable fit. The design is distinguished by its clean, collarless neckline, button-front closure, and four practical patch pockets. Delicate braided trim elegantly outlines the collar, placket, cuffs, and pockets, adding texture and refinement. Each gold-tone button is adorned with the iconic interlocking CC logo, making this jacket an unmistakable symbol of Parisian elegance.'
        )
    )
    static_mapping_data = {
        "product": product_data,
        "micro_trends": micro_trends_data,
        "macro_trends": macro_trends_data
    }
    
    return ProductTrendMapping(**static_mapping_data)

def create_davos_fashion_agent() -> Agent:
    """Create and configure the primary cap compliance agent."""

    # Create the main compliance agent
    # try:
    agent = Agent(
        name=agent_settings.agent_name,
        model=GEMINI_MODEL_NAME, # Defaulting to a capable model
        instruction=system_instruction,
        description=agent_settings.agent_description,
        tools=[
            # AgentTool(agent=sales_plan_agent),
            # create_session_example,
            load_brand_data,
            identify_inventory_opportunities,
            get_product_by_sku,
            # get_product_assets,
            # analyze_market_trends,
            
            # USED FOR DEMO
            AgentTool(agent=product_trend_mapper_agent.agent),
            # product_trend_mapper_agent.retrieve_image_from_gcs,
            # product_trend_mapper_agent.identify_product_from_image,
            # product_trend_mapper_agent.map_product_to_trends,
            
            # AgentTool(agent=ProductTrendMapperAgent().agent),

            AgentTool(agent=trend_spotter_agent.agent),
            # USED FOR DEMO
            AgentTool(agent=art_director_agent.agent),
            # art_director_agent.create_moodboards,
            # art_director_agent.create_campaign_directive,

            fashion_photographer_agent.generate_campaign_image,
            # creative_director_agent.create_video_scenes_demo,
            creative_director_agent.create_video_scenes,
            creative_director_agent.generate_scene_image,
            # generate_video_prompt,
            # AgentTool(agent=campaign_manager_agent.agent),
            # create_campaign_draft,
            # generate_campaign_video
        ]
    )

    logger.info(f"Successfully created {agent_settings.agent_name}")
    return agent

def create_davos_fashion_agent_demo() -> Agent:
    """Create and configure the primary cap compliance agent."""
    print(f"model is {GEMINI_MODEL_NAME}")
    # Create the main compliance agent
    # try:
    agent = Agent(
        name=agent_settings.agent_name,
        model=GEMINI_MODEL_NAME, # Defaulting to a capable model
        instruction=system_instruction,
        description=agent_settings.agent_description,
        tools=[
            # AgentTool(agent=sales_plan_agent),
            identify_inventory_opportunities,
            load_brand_data,
            get_product_by_sku,
            map_product_to_trends_demo,
            AgentTool(agent=ArtDirector().agent),
            fashion_photographer_agent.generate_campaign_image,
            creative_director_agent.create_video_scenes,
            creative_director_agent.generate_scene_image,
            AgentTool(agent=campaign_manager_agent.agent),
        ]
    )

    logger.info(f"Successfully created {agent_settings.agent_name}")
    return agent

    # except Exception as e:
    #     logger.error(f"Failed to create {agent_settings.agent_name}: {e}")
    #     raise RuntimeError(f"Failed to create agent: {str(e)}")




# try:
# Try to load settings from environment
agent_settings = AgentSettings()


sales_plan_agent = Agent(
    name="sales_plan_agent",
    model='gemini-2.5-flash',
    tools=[VertexAiSearchTool(data_store_id=agent_settings.sharepoint_datastore_id)],
    instruction="Retrieve data from the sales plan document. Return it in a human readable format.",
)

# agent = create_davos_fashion_agent_demo()
agent = create_davos_fashion_agent()
logger.info(f"{agent_settings.agent_name} initialized successfully")
# except Exception as e:
#     logger.error(f"Failed to create agent: {e}")
#     raise RuntimeError(f"Failed to create agent: {str(e)}")

# Export with both names for ADK and AgentSpace compatibility
root_agent = agent
__all__ = ["agent", "root_agent", "create_davos_fashion_agent"]