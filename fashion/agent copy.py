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
# from fashion.tools.campaign import CampaignTool
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from fashion.tools.video_generation_prompt import generate_video_prompt
from google.adk.sessions import InMemorySessionService
from typing import List
from fashion.schema import Product, ProductTrendMapping, TrendMatch, Trend, ProductList
from google.adk.agents.callback_context import CallbackContext
# from google.adk.caching import InvocationContext
from google.adk.agents.invocation_context import InvocationContext

import uuid


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
# art_director_agent = ArtDirector()
creative_director_agent = CreativeDirector()
# product_trend_mapper_agent = ProductTrendMapper()
# campaign_tool = CampaignTool()

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

def identify_inventory_opportunities(tool_context: InvocationContext) -> List[Product]:
    print('here1')
    """Identifies high-stock, low-velocity inventory items."""
    high_stock_products = inventory_tool.find_high_stock()
    print('here2')
    low_velocity_products = sales_tool.find_low_velocity()
    print('here3')
    # Map SKU to Product for low velocity items
    low_velocity_map = {p.core_identifiers.sku: p for p in low_velocity_products}
    print('here4')
    opportunities = []
    opportunities_as_dict = []
    print('here5')
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
            opportunities_as_dict.append(product.__dict__)
      
    # TODO look at putting this back, but serilization was an issue        
    tool_context.state["opportunities"] = opportunities
    print('here6')
    return opportunities

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

# Create Agent
# Note: In a real ADK app, you'd likely use a specific Model implementation (e.g., VertexAIModel)
# For this demo, we assume the environment is set up for the default model provider or use a placeholder.
# If ADK requires a specific model instance, we would instantiate it here.



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
            identify_inventory_opportunities,
            # get_product_assets,
            # analyze_market_trends,
            AgentTool(agent=ProductTrendMapper().agent),
            # product_trend_mapper_agent.retrieve_image_from_gcs,
            # product_trend_mapper_agent.identify_product_from_image,
            # product_trend_mapper_agent.map_product_to_trends,
            # AgentTool(agent=ProductTrendMapperAgent().agent),

            AgentTool(agent=trend_spotter_agent.agent),
            AgentTool(agent=ArtDirector().agent),
            # art_director_agent.create_moodboards,
            # art_director_agent.create_campaign_directive,
            fashion_photographer_agent.generate_campaign_image,
            creative_director_agent.create_video_scenes,
            creative_director_agent.generate_scene_image,
            generate_video_prompt
            # create_campaign_draft,
            # generate_campaign_video
        ]
    )

    logger.info(f"Successfully created {agent_settings.agent_name}")
    return agent

    # except Exception as e:
    #     logger.error(f"Failed to create {agent_settings.agent_name}: {e}")
    #     raise RuntimeError(f"Failed to create agent: {str(e)}")


from fashion.config import AgentSettings

# try:
# Try to load settings from environment
agent_settings = AgentSettings()
agent = create_davos_fashion_agent()
logger.info(f"{agent_settings.agent_name} initialized successfully")
# except Exception as e:
#     logger.error(f"Failed to create agent: {e}")
#     raise RuntimeError(f"Failed to create agent: {str(e)}")

# Export with both names for ADK and AgentSpace compatibility
root_agent = agent
__all__ = ["agent", "root_agent", "create_davos_fashion_agent"]