
import asyncio
import logging
from fashion.sub_agents.social_media_director import SocialMediaDirector
from fashion.schema import Product, Brand, Trend, CoreIdentifiers, Attributes, Categorization, TaxonomyAttributes, MarketingAttributes, Description

# Setup logging
logging.basicConfig(level=logging.INFO)

async def verify():
    agent = SocialMediaDirector()
    
    # Create Dummy Data
    product = Product(
        core_identifiers=CoreIdentifiers(
            sku="123",
            product_name="Test Product",
            brand="TestBrand"
        ),
        attributes=Attributes(
            color_name="Red",
            material="Cotton",
            fit_type="Regular"
        ),
        categorization=Categorization(
            department="Apparel",
            category="Tops"
        ),
        description=Description(
            short="A nice red shirt",
            long="A very nice red shirt made of cotton."
        )
    )
    
    brand = Brand(
        brand_identifier="test_brand",
        name="TestBrand",
        brand_core={}, # minimal
        visual_identity={},
        photography_and_art_direction={},
        voice_and_tone={}
    )
    
    trend = Trend(
        trend_name="Summer Vibes",
        trend_scope="Macro",
        social_media_tags=["#summer", "#vibes"],
        key_influencer_handles=["@summer_influencer"],
        essential_look_characteristics={"Vibe": "Chill", "Style": "Loose"},
        taxonomy_attributes=TaxonomyAttributes(
            primary_aesthetic="Boho",
            secondary_aesthetic="Casual",
            key_garments=["Dress", "Shirt"],
            materials_and_textures=["Linen", "Cotton"],
            color_palette=["Yellow", "Red"],
            mood_keywords=["Happy", "Sunny"],
            target_occasion=["Beach", "Park"],
            seasonality="Summer"
        ),
        marketing_attributes=MarketingAttributes(
            ad_creative_direction="Fun in the sun"
        )
    )
    
    print("Calling product_research...")
    # Passing None for image path to avoid GCS download in test, or provide a dummy if needed (will fail download but proceed?)
    # The code handles download exceptions, so it should be fine.
    try:
        response = await agent.product_research(product, brand, trend, product_image_path=None)
        print("Response received:")
        print(response)
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
