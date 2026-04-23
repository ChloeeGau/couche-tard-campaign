import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.davos')

from retail_ops.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from typing import List

from google.adk.agents import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import InMemorySessionService
from google.adk.tools import AgentTool, VertexAiSearchTool

from retail_ops.adk_common.utils.utils_agents import to_dict_recursive
from retail_ops.adk_common.utils.utils_gcs import generate_min_image
from retail_ops.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from retail_ops.config import GEMINI_MODEL_NAME, LOCATION, PROJECT_ID, AgentSettings
from retail_ops.data.products import retrieve_products
from retail_ops.schema import (
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
from retail_ops.sub_agents.art_director import ArtDirector
# from retail_ops.sub_agents.campaign_manager import CampaignManager
from retail_ops.sub_agents.creative_director import CreativeDirector
from retail_ops.sub_agents.fashion_photographer import FashionPhotographer
from retail_ops.sub_agents.product_trend_mapper import ProductTrendMapper
from retail_ops.sub_agents.trend_spotter import TrendSpotter
from retail_ops.sub_agents.social_media_director import SocialMediaDirector
from retail_ops.tools.inventory import InventoryTool
from retail_ops.tools.sales import SalesTool




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
def identify_inventory_opportunities(tool_context: InvocationContext) -> List[dict]:
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
def create_couche_tard_campaign_agent() -> Agent:
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
                trend_name='Morning Coffee Run',
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/moodboard_Morning_Fuel.png",
                executive_summary='Converting fuel customers into food/beverage buyers with fresh coffee and breakfast items.',
                trend_start_date='2026-01-01',
                trend_scope='Macro',
                trend_lifecycle_stage='Growth',
                primary_sources=['Sales Data', 'Customer Surveys'],
                key_designers=[],
                social_media_tags=['#CoffeeRun', '#BreakfastPizza'],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Convenient',
                    secondary_aesthetic='Fresh',
                    key_garments=['Coffee', 'Pizza'],
                    materials_and_textures=['Hot', 'Fresh'],
                    color_palette=['Warm'],
                    mood_keywords=['Energetic'],
                    target_occasion=['Morning Commute'],
                    seasonality='Winter'
                ),
                search_vectors=None,
                visual_assets=VisualAssets(
                    google_images_url=None,
                    pinterest_url=None,
                    tiktok_search_url=None,
                    ai_generation_prompt='A steaming cup of Circle K coffee next to a breakfast pizza slice.'
                ),
                marketing_attributes=None
            ),
            match_score=0.95,
            reasoning="Cold morning weather creates a perfect opportunity for hot coffee and breakfast pizza."
        ),
        TrendMatch(
            trend=Trend(
                trend_name='Afternoon Sloche Rush',
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/moodboard_Sloche.png",
                executive_summary='Driving afternoon traffic with icy, refreshing Sloche beverages.',
                trend_start_date='2026-05-01',
                trend_scope='Micro',
                trend_lifecycle_stage='Growth',
                primary_sources=['Weather Data', 'Sales Analytics'],
                key_designers=[],
                social_media_tags=['#Sloche', '#BeatTheHeat'],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Cool',
                    secondary_aesthetic='Refreshing',
                    key_garments=['Sloche'],
                    materials_and_textures=['Icy'],
                    color_palette=['Bright'],
                    mood_keywords=['Fun'],
                    target_occasion=['Afternoon Drive'],
                    seasonality='Summer'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.92,
            reasoning="Hot afternoon weather spikes demand for frozen beverages."
        ),
        TrendMatch(
            trend=Trend(
                trend_name='Late Night Snack',
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/moodboard_Late_Night.png",
                executive_summary='Targeting late-night drivers with quick snacks and energy drinks.',
                trend_start_date='2026-01-01',
                trend_scope='Macro',
                trend_lifecycle_stage='Mature',
                primary_sources=['Traffic Patterns'],
                key_designers=[],
                social_media_tags=['#LateNight', '#JokerEnergy'],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Fast',
                    secondary_aesthetic='Convenient',
                    key_garments=['Energy Drink', 'Chips'],
                    materials_and_textures=['Crunchy'],
                    color_palette=['Dark'],
                    mood_keywords=['Alert'],
                    target_occasion=['Late Night'],
                    seasonality='All-Year'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.85,
            reasoning="Late night drivers seek energy and convenience."
        )
    ]
    macro_trends_data = [
        TrendMatch(
            trend=Trend(
                trend_name='Fuel-to-Food Conversion',
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/moodboard_Conversion.png",
                executive_summary='Converting pay-at-the-pump customers into in-store basket builders.',
                trend_start_date='2026-01-01',
                trend_scope='Macro',
                trend_lifecycle_stage='Growth',
                primary_sources=['Loyalty Data', 'Point of Sale'],
                key_designers=[],
                social_media_tags=['#FuelToFood', '#InnerCircle'],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Convenient',
                    secondary_aesthetic='Rewarding',
                    key_garments=['Fuel', 'Food'],
                    materials_and_textures=['Fast'],
                    color_palette=['Red'],
                    mood_keywords=['Smart'],
                    target_occasion=['Fuel Stop'],
                    seasonality='All-Year'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.9,
            reasoning="Pay-at-the-pump users are a prime target for in-store food conversion."
        ),
        TrendMatch(
            trend=Trend(
                trend_name='EV Dwell Time',
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/moodboard_EVDwell.png",
                executive_summary='Capitalizing on extended dwell times of EV charging customers.',
                trend_start_date='2026-01-01',
                trend_scope='Macro',
                trend_lifecycle_stage='Emerging',
                primary_sources=['EV Station Usage'],
                key_designers=[],
                social_media_tags=['#EVCharging', '#DwellTime'],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Relaxed',
                    secondary_aesthetic='Premium',
                    key_garments=['Coffee', 'Seating'],
                    materials_and_textures=['Comfortable'],
                    color_palette=['Green'],
                    mood_keywords=['Relaxed'],
                    target_occasion=['EV Charging'],
                    seasonality='All-Year'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.88,
            reasoning="EV drivers have 20-30 minutes of dwell time available for premium food/beverage."
        ),
        TrendMatch(
            trend=Trend(
                trend_name='Private Label Growth',
                moodboard_url=f"https://storage.cloud.google.com/creative-content_{PROJECT_ID}/moodboard_PrivateLabel.png",
                executive_summary='Expanding high-margin private label sales (e.g., Joker Energy, Favorites snacks).',
                trend_start_date='2026-01-01',
                trend_scope='Macro',
                trend_lifecycle_stage='Growth',
                primary_sources=['Internal Strategy'],
                key_designers=[],
                social_media_tags=['#JokerEnergy', '#Favorites'],
                key_influencer_handles=[],
                essential_look_characteristics={},
                taxonomy_attributes=TaxonomyAttributes(
                    primary_aesthetic='Premium',
                    secondary_aesthetic='Affordable',
                    key_garments=['Energy Drink', 'Chips'],
                    materials_and_textures=['Quality'],
                    color_palette=['Gold'],
                    mood_keywords=['Smart'],
                    target_occasion=['Snack Time'],
                    seasonality='All-Year'
                ),
                search_vectors=None,
                visual_assets=None,
                marketing_attributes=None
            ),
            match_score=0.92,
            reasoning="Private labels offer high margins and build customer loyalty."
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
def create_couche_tard_campaign_agent_demo() -> Agent:
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
    agent = create_couche_tard_campaign_agent()
    log_message(f"{agent_settings.agent_name} initialized successfully", Severity.INFO)
except Exception as e:
    log_message(f"Failed to create agent: {e}", Severity.ERROR)
    raise RuntimeError(f"Failed to create agent: {str(e)}")

# Export with both names for ADK and AgentSpace compatibility
root_agent = agent
__all__ = ["agent", "root_agent", "create_couche_tard_campaign_agent"]