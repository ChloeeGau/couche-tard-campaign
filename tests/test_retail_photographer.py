import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.davos')

from retail_ops.sub_agents.retail_photographer import RetailPhotographer
from retail_ops.schema import Trend, TaxonomyAttributes

print("\n--- Testing RetailPhotographer ---")
try:
    photographer = RetailPhotographer()
    print("RetailPhotographer initialized.")
    
    # Create dummy Trend Data
    trend_data = Trend(
        trend_name="Morning Coffee Run",
        executive_summary="Summary",
        taxonomy_attributes=TaxonomyAttributes(
            primary_aesthetic="Convenience",
            secondary_aesthetic="Warmth",
            key_garments=["Coffee"],
            materials_and_textures=["Hot"],
            color_palette=["Red"],
            mood_keywords=["Energizing"],
            target_occasion=["Morning"],
            seasonality="Winter"
        )
    )
    
    # Testing the Sloche
    product_path = "retail_ops/data/brand_assets/BEV-SLO-001.png"
    print("Calling generate_campaign_image for Sloche...")
    output_path = photographer.generate_campaign_image(product_path, "A vibrant red frozen Sloche drink in a branded cup with condensation on the outside, sitting on a clean counter inside a bright Circle K store. Fun, refreshing, high energy.")
    
    print(f"Generated Image Path: {output_path}")

    if output_path and "generated_campaigns" in output_path:
        print("Success: Real image path returned.")
    else:
        print("Failure: No image path returned.")

except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
