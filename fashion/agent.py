import json
from fashion.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
import os
from typing import List

from google.adk.agents import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import InMemorySessionService
from google.adk.tools import AgentTool, VertexAiSearchTool

from fashion.adk_common.utils.utils_agents import to_dict_recursive
from fashion.adk_common.utils.utils_gcs import generate_min_image
from fashion.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from fashion.config import GEMINI_MODEL_NAME, LOCATION, PROJECT_ID, AgentSettings
from fashion.data.products import retrieve_products
from fashion.schema import (
    Attributes,
    Brand,
    Categorization,
    CommercialStatus,
    CoreIdentifiers,
    Description,
    Media,
    Product,
    ProductTrendMapping,
    TaxonomyAttributes,
    Trend,
    TrendMatch,
    VisualAssets,
)
from fashion.sub_agents.art_director import ArtDirector
# from fashion.sub_agents.campaign_manager import CampaignManager
from fashion.sub_agents.creative_director import CreativeDirector
from fashion.sub_agents.fashion_photographer import FashionPhotographer
from fashion.sub_agents.product_trend_mapper import ProductTrendMapper
from fashion.sub_agents.trend_spotter import TrendSpotter
from fashion.sub_agents.social_media_director import SocialMediaDirector
from fashion.tools.inventory import InventoryTool
from fashion.tools.sales import SalesTool




# TODO: session
# Initialize the session immediately so it's ready
# session_service = InMemorySessionService()
# async def create_session():
#     """Creates a sample session for testing purposes.

#     Returns:
#         Session: A newly created in-memory session.
#     """
#     session = await session_service.create_session(
#         app_name="my_app", user_id="test_user", session_id="123"
#     )
#     log_message(f"new session is {session.id}", Severity.INFO)
#     return session

# Initialize Tools
# TODO: should the inventory and sales tools for BQ be brought in differently?
inventory_tool = InventoryTool()
sales_tool = SalesTool()
trend_spotter_agent = TrendSpotter()
fashion_photographer_agent = FashionPhotographer()
art_director_agent = ArtDirector()
creative_director_agent = CreativeDirector()
product_trend_mapper_agent = ProductTrendMapper()
social_media_director_agent = SocialMediaDirector()
# campaign_manager_agent = CampaignManager()
    
# TODO: enhance the logic around determining velocity
# TODO: include sales plan information
@log_function_call
def identify_inventory_opportunities(tool_context: InvocationContext) -> List[Product]:
    """Identifies high-stock, low-velocity inventory items by cross-referencing inventory and sales data.

    This function finds products that have high stock levels but low sales velocity.
    It enriches the product data with sales velocity reasoning if available.

    Args:
        tool_context (InvocationContext): The context for the tool execution.

    Returns:
        List[dict]: A list of dictionary representations of the identified opportunity products.
    """
    high_stock_products = inventory_tool.find_high_stock()
    low_velocity_products = sales_tool.find_low_velocity()
    # Map SKU to Product for low velocity items
    low_velocity_map = {p.core_identifiers.sku: p for p in low_velocity_products}
    opportunities = []
    opportunities_as_dict = []
    for product in high_stock_products:
        opportunities.append(product)
        opportunities_as_dict.append(to_dict_recursive(product))
        # # Access SKU via core_identifiers
        # sku = product.core_identifiers.sku
        # if sku in low_velocity_map:
        #     # Merge sales data into the high stock product
        #     sales_product = low_velocity_map[sku]
        #     # Assumes commercial_status exists on both
        #     if product.commercial_status and sales_product.commercial_status:
        #         product.commercial_status.sales_velocity = sales_product.commercial_status.sales_velocity
        #         product.commercial_status.sales_reasoning = sales_product.commercial_status.sales_reasoning
        #     opportunities.append(product)
        #     opportunities_as_dict.append(to_dict_recursive(product))
      
    # TODO look at putting this back, but serilization was an issue        
    tool_context.state["opportunities"] = opportunities_as_dict
    return opportunities_as_dict    


# TODO: read from BQ instead of JSON
@log_function_call
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
            log_message("Brand data loaded successfully into state.", Severity.INFO)
            log_message(f"Brand data: {tool_context.state['brand_data']}", Severity.INFO)
    except FileNotFoundError:
        log_message(f"brands.json not found at {file_path}", Severity.ERROR)
        tool_context.state["brand_data"] = {}
    except json.JSONDecodeError:
        log_message(f"Error decoding JSON from brands.json at {file_path}", Severity.ERROR)
        tool_context.state["brand_data"] = {}
    except Exception as e:
        log_message(f"An unexpected error occurred while loading brand data: {e}", Severity.ERROR)
        tool_context.state["brand_data"] = {}


# TODO: move products to a database instead of json file
@log_function_call
def get_product_by_sku(tool_context: InvocationContext, sku: str) -> dict:
    """Retrieves a product and its associated brand information by SKU.

    Args:
        tool_context (InvocationContext): The context for the tool execution.
        sku (str): The SKU of the product to retrieve.

    Returns:
        tuple[dict, dict]: A tuple containing the product dictionary and the brand info dictionary.
    """
    products = retrieve_products()
    for product in products:
        if product.core_identifiers.sku == sku:
            tool_context.state['product'] = to_dict_recursive(product)
            min_image = generate_min_image(product.media.main_image_url)
            brand_name = product.core_identifiers.brand
            brand_info = next((brand for brand in tool_context.state.get("brand_data", []) if brand.get("name") == brand_name), None)
            if brand_info:
                tool_context.state['brand_info'] = brand_info
                log_message(f"Brand info for {brand_name} loaded successfully into state.", Severity.INFO)
            else:
                log_message(f"Brand info for {brand_name} not found in loaded data.", Severity.WARNING)
            return to_dict_recursive(product), to_dict_recursive(tool_context.state['brand_info'])

    return to_dict_recursive(Product()),to_dict_recursive(Brand())
    

@log_function_call
def analyze_market_trends():
    """Analyzes current social media trends using the Trend Spotter agent.

    Returns:
        str: The analysis result from the Trend Spotter agent.
    """
    return trend_spotter_agent.spot_trends()


system_instruction = load_prompt_file_from_calling_agent(prompt_filename="prompts/instructions.md")
# system_instruction = load_prompt_file_from_calling_agent(prompt_filename="prompts/instructions_demo.md")

@log_function_call
def create_davos_fashion_agent() -> Agent:
    """Create and configure the primary Davos Fashion Agent.

    Returns:
        Agent: The configured Google ADK Agent instance.
    """

    # Create the main agent
    try:
        agent = Agent(
            name=agent_settings.agent_name,
            model=GEMINI_MODEL_NAME, # Defaulting to a capable model
            instruction=system_instruction,
            description=agent_settings.agent_description,
            tools=[
                # AgentTool(agent=sales_plan_agent),
                # create_session,
                load_brand_data,
                identify_inventory_opportunities,
                get_product_by_sku,
                # get_product_assets,
                analyze_market_trends,
                AgentTool(agent=product_trend_mapper_agent.agent),
                # product_trend_mapper_agent.retrieve_image_from_gcs,
                # product_trend_mapper_agent.identify_product_from_image,
                # product_trend_mapper_agent.map_product_to_trends,
                AgentTool(agent=trend_spotter_agent.agent),
                AgentTool(agent=art_director_agent.agent),
                # art_director_agent.create_moodboards,
                # art_director_agent.create_campaign_directive,
                fashion_photographer_agent.generate_campaign_image,
                AgentTool(agent=creative_director_agent.agent),
                # creative_director_agent.create_video_scenes,
                # creative_director_agent.generate_scene_image,
                # # generate_video_prompt,
                AgentTool(agent=social_media_director_agent.agent)
            ]
        )

        log_message(f"Successfully created {agent_settings.agent_name}", Severity.INFO)
        return agent
    except Exception as e:
        log_message(f"Failed to create {agent_settings.agent_name}: {e}", Severity.ERROR)
        return None


@log_function_call
def map_product_to_trends_demo() -> ProductTrendMapping:
    """Creates a ProductTrendMapping object from static data.

    Returns:
        ProductTrendMapping: A static mapping of products to trends for demo purposes.
    """

    micro_trends_data=[
        TrendMatch(
            trend=Trend(
                trend_name='The Lady Jacket',
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
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
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
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
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
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
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
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
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
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
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/20260110173415814531_2v7h/moodboard_Heritage_Revival.png",
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
            main_image_url=f'https://storage.cloud.google.com/creative-content_{PROJECT_ID}/catalog/top/292929.png',
            web_image_url=f'https://storage.cloud.google.com/creative-content_{PROJECT_ID}/catalog/top/292929_min.png',
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

@log_function_call
def create_davos_fashion_agent_demo() -> Agent:
    """Create and configure the primary Davos Fashion Agent for deterministic demo purposes.

    Returns:
        Agent: The configured Google ADK Agent instance for the demo.
    """
    log_message(f"model is {GEMINI_MODEL_NAME}", Severity.INFO)

    try:
        agent = Agent(
            name=agent_settings.agent_name,
            model=GEMINI_MODEL_NAME, # Defaulting to a capable model
            instruction=system_instruction,
            description=agent_settings.agent_description,
            tools=[
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

        log_message(f"Successfully created {agent_settings.agent_name}", Severity.INFO)
        return agent
    except Exception as e:
        log_message(f"Failed to create {agent_settings.agent_name}: {e}", Severity.ERROR)
        raise RuntimeError(f"Failed to create agent: {str(e)}")


try:
    # Try to load settings from environment
    agent_settings = AgentSettings()

    sales_plan_agent = Agent(
        name="sales_plan_agent",
        model=GEMINI_MODEL_NAME,
        tools=[VertexAiSearchTool(data_store_id=agent_settings.sharepoint_datastore_id)],
        instruction="Retrieve data from the sales plan document. Return it in a human readable format.",
    )

    # agent = create_davos_fashion_agent_demo()
    agent = create_davos_fashion_agent()
    log_message(f"{agent_settings.agent_name} initialized successfully", Severity.INFO)
except Exception as e:
    log_message(f"Failed to create agent: {e}", Severity.ERROR)
    raise RuntimeError(f"Failed to create agent: {str(e)}")

# Export with both names for ADK and AgentSpace compatibility
root_agent = agent
__all__ = ["agent", "root_agent", "create_davos_fashion_agent"]