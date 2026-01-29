from google.cloud import storage
from google import genai
from google.genai import types as genai_types
from google.cloud import storage
from PIL import Image
import io
import base64
import os
from google.genai.types import HarmBlockThreshold, HarmCategory
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json

class CoreIdentifiers(BaseModel):
    sku: str
    upc: Optional[str] = None
    brand: Optional[str] = None
    product_name: str
class Attributes(BaseModel):
    size: Optional[str] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    material: Optional[str] = None
    fit_type: Optional[str] = None
    care_instructions: Optional[str] = None
class Categorization(BaseModel):
    department: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    collection: Optional[str] = None
class CommercialStatus(BaseModel):
    currency: Optional[str] = "USD"
    msrp: Optional[float] = None
    current_price: Optional[float] = None
    cost_price: Optional[float] = None
    in_stock: bool = False
    stock_quantity: int = 0
    # Extended fields for internal app usage
    sales_velocity: Optional[str] = None
    sales_reasoning: Optional[str] = None
class Media(BaseModel):
    main_image_url: Optional[str] = None
    gallery_urls: List[str] = []
    alt_text: Optional[str] = None
class Description(BaseModel):
    short: Optional[str] = None
    long: Optional[str] = None
class Product(BaseModel):
    core_identifiers: CoreIdentifiers
    attributes: Attributes
    categorization: Categorization
    commercial_status: CommercialStatus
    media: Media
    description: Description

products=[]
def get_all_storage_uris(bucket_name, prefix=None, extensions=None):
    """
    Lists all files in a GCS bucket and returns them as 'gs://' URIs.
    Args:
        bucket_name: Name of your bucket (e.g. "my-fashion-bucket")
        prefix: Optional folder filter (e.g. "tops/")
        extensions: Optional tuple to filter file types (e.g. ('.jpg', '.png'))
    """
    # 1. Initialize Client
    storage_client = storage.Client()
    # 2. Get the blobs (files)
    # Note: list_blobs is lazy loading, so it handles large buckets well.
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
    uri_list = []
    for blob in blobs:
        # Optional: Filter by file extension (e.g. only images)
        if extensions and not blob.name.lower().endswith(tuple(extensions)) or 'catalog' not in blob.name:
            continue
        # Construct the gs:// URI
        # blob.name contains the full path (e.g. "tops/shirt.jpg")
        sku = blob.name.split("/")[-1].split(".")[0]
        print(sku)
        gcs_uri = f"gs://{bucket_name}/{blob.name}"
        uri_list.append(gcs_uri)
    return uri_list
uri_list=get_all_storage_uris('product-image-assets', extensions=['.jpg', '.png', '.jpeg']) 

for uri in uri_list:
    create_product(uri)


def create_product(product_image_path: str) -> Dict[str, Any]:
    """
    Generates a creative directive (image prompt) for a campaign based on product and trend.
    """
    try:
        client = genai.Client(vertexai=True, project='gemini-enterprise-banking-1446', location='us-central1')
        # Step 1: Generate the Image Prompt using Gemini
        sku = product_image_path.split("/")[-1].split(".")[0]
        prompt_content = [
            f"Generate catalog information as {Product} object based on the apparel item in the the image. Sku is {sku} and the main_image_url is {product_image_path}",
            "Product Image:"
        ]
        # Load product image bytes for Gemini
        try:
            if product_image_path:
                image_part = genai_types.Part.from_uri(
                    file_uri=product_image_path, mime_type="image/png"
                )
                prompt_content.append(image_part)
              
                prompt_content.append("""
                  Output as a JSON object and MUST conform to the following schema:
                  ``` json
                    {
                        "core_identifiers": {
                            "sku": sku,
                            "upc": "made up value", 
                            "brand": "made up brand",
                            "product_name": "made up product name based on product in the image"
                        },
                        "attributes": {
                            "size": "Medium", 
                            "color_name": "use a color name that is representative of the product in the image",
                            "color_hex": "use a color hex that is representative of the product in the image",
                            "material": "use a material that is representative of the product in the image",
                            "fit_type": "use a fit that is representative of the product in the image",
                            "care_instructions": "use care instructions that are representative of the product in the image"
                        },
                        "categorization": {
                            "department": "use a department that is representative of the product in the image (men, women or unisex)",
                            "category": "Apparel", 
                            "sub_category": "use a sub category that is representative of the product in the image (Top, Bottom, Footwear, Accessory, Dress, or Outerwear)",
                            "collection": "use a collection that is representative of the product in the image"
                        },
                        "commercial_status": {
                            "currency": "USD", #always USD
                            "msrp": "use a msrp that is representative of the product in the image", 
                            "current_price": "use a current price that is representative of the product in the image",
                            "cost_price": "use a cost price that is representative of the product in the image and lower than current_price",
                            "in_stock": true,
                            "stock_quantity": "use a random qty between 1 and 600"
                        },
                        "media": {
                            "main_image_url": product_image_path,
                            "gallery_urls": [],
                            "alt_text": "use a alt text that is representative of the product in the image"
                        },
                        "description": {
                            "short": "use a short description that is representative of the product in the image",
                            "long": "use a long description that is representative of the product in the image"
                        }
                    }
                    ```
              "**Critical** Escape double quotes in strings with a backslash"
              "**Critical** When setting boolean values, use lower case true or false"
              "**Critical** Don't set any value to None"
              "**Critical** Output MUST be a JSON object"
              "**Critical** Evaluate the image before providing descriptions"
              """)
            config = genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7, # Slightly higher for creativity
                response_schema=Product,
            )
        except Exception as e:
            print(f"Failed to load product image for prompt generation: {e}")
            return None
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt_content,
            config=config,
        )
        json_return = response.text
        products.append(json.loads(json_return))
        # print(f"Generated Art Direction: {art_direction}")
        return json_return
    except Exception as e:
        print(f"Art Director Failed: {e}")
        return None
# get_all_storage_uris('creative-content', extensions=['.jpg', '.png', '.jpeg'])


create_product('gs://product-image-assets/bottom/185932.png')
create_product('gs://product-image-assets/top/239944.png')
# print(f"type: {type(products[0])}")
# print(products[0])
# print(json.dumps(products[0], indent=4, sort_keys=True))