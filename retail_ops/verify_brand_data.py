
from retail_ops.data.brands import retrieve_brands

def verify_brand_data():
    brands = retrieve_brands()
    found = False
    for brand in brands:
        print(f"Checking brand: {brand.name}")
        if brand.social_media_model:
            print(f"  Found social_media_model for {brand.name}")
            print(f"  Model Name: {brand.social_media_model.model_name}")
            print(f"  Influencer Type: {brand.social_media_model.model_influencer_type}")
            found = True
        else:
            print(f"  No social_media_model for {brand.name}")
    
    if found:
        print("SUCCESS: At least one brand has social_media_model populated.")
    else:
        print("FAILURE: No brand has social_media_model populated.")

if __name__ == "__main__":
    verify_brand_data()
