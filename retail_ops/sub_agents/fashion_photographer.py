from retail_ops.schema import Trend, TaxonomyAttributes, VisualAssets, MarketingAttributes, TargetAudienceProfile
from retail_ops.adk_common.utils.utils_logging import (Severity, log_function_call, log_message)
from retail_ops.config import GEMINI_MODEL_NAME, IMAGEN_MODEL_NAME, PROJECT_ID, LOCATION, NANO_BANANA_PRO_MODEL_NAME, STANDARD_GENERATION_CONFIG, PROTOTYPE_SAFETY_SETTINGS
import logging
from google import genai
from google.genai import types as genai_types
import base64
import os
from google.genai.types import HarmBlockThreshold, HarmCategory
from google.cloud import storage
from PIL import Image
import io
from retail_ops.adk_common.utils.utils_prompts import load_prompt_file_from_calling_agent
from retail_ops.adk_common.utils.utils_gcs import download_blob_to_bytes

image_path_example_1 = "gs://vto-demo/cropped_flatlay/outerwear/84511-flyweight-flex-blazer?utm_source=Standard%20-%20Order%20Confirmation&utm_medium=email&utm_campaign=orderconfirmation_noteligible3%20(XWFDTK)&utm_id=Ux6pzz&term=flow&uid=01J1P79F4DDCS83FFTXMY86NBR&_kx=qZnD_aogIJ_ircLHGjZEU9O4lo5bmBWBQdlyG10kghQ.bVvvBe.png"
trend_data_example_1 = Trend(
    trend_name="The Barn Blazer (Soft-Utility Tailoring)",
    executive_summary="Evolving from the massive 'Barn Jacket' viral moment of 2024, the 'Barn Blazer' represents the 2025 shift towards 'Soft-Utility.' As men return to semi-formal spaces but refuse to sacrifice the comfort of Gorpcore, the rugged field coat has been refined into a blazer silhouette. It features the functional DNA of workwear (patch pockets, throat latches, durable cotton) but with the cut of a soft, unstructured sport coat. It is the ultimate 'City-Ready' layer for the 'Eclectic Grandpa' or 'Refined Workwear' aesthetic.",
    trend_start_date="09/2024",
    trend_scope="Macro",
    trend_lifecycle_stage="Mass Adoption (Peak)",
    primary_sources=[
      "GQ Trend Report: The Evolution of Workwear (Winter 2025)",
      "TikTok Trend Watch: #UtilityBlazer",
      "WGSN Menswear Forecast F/W 25"
    ],
    key_designers=["Prada", "Loewe", "Margaret Howell"],
    social_media_tags=["#UtilityBlazer", "#SoftWorkwear", "#EclecticGrandpa"],
    key_influencer_handles=["@dieworkwear", "@ethanwong"],
    essential_look_characteristics={
        "Silhouette": "Relaxed but tailored",
        "Key Element": "Patch pockets on a blazer cut",
        "Fabric": "Natural fibers, textured"
    },
    taxonomy_attributes=TaxonomyAttributes(
      primary_aesthetic="Heritage Workwear",
      secondary_aesthetic="Quiet Luxury",
      key_garments=[
      "Unstructured Utility Blazer",
      "Refined Chore Coat",
      "Field Jacket Hybrid"
      ],
      materials_and_textures=[
      "Garment-dyed Cotton Canvas",
      "Moleskin",
      "Washed Twill",
      "Matte Finish"
      ],
      color_palette=[
      "Sage Green",
      "Slate Grey",
      "Driftwood",
      "Charcoal"
      ],
      mood_keywords=[
      "Functional",
      "Lived-in",
      "Versatile",
      "Rugged-Refined"
      ],
      target_occasion=[
      "Creative Office",
      "Smart Casual",
      "Weekend Travel"
      ],
      seasonality="Fall/Winter 2025"
      ),
      search_vectors=[
      "mens utility blazer trend 2025",
      "relwen flyweight blazer style",
      "refined barn jacket mens",
      "soft tailoring workwear aesthetic",
      "chore coat vs blazer trend"
      ],
      visual_assets=VisualAssets(
        google_images_url="https://www.google.com/search?tbm=isch&q=mens+utility+blazer+trend+2025+street+style",
        pinterest_url="https://www.pinterest.com/search/pins/?q=mens+soft+tailoring+workwear",
        tiktok_search_url="https://www.tiktok.com/search?q=barn+jacket+outfit+men+2025",
        ai_generation_prompt="A cinematic street style shot of a stylish man in his 30s walking in a modern city during autumn. He is wearing a grey unstructured 'Barn Blazer' with a popped collar and patch pockets, layered over a textured waffle-knit sweater. The vibe is 'Quiet Outdoors' meets 'Creative Director'. Soft lighting, shallow depth of field, 8k resolution."
      ),
      marketing_attributes=MarketingAttributes(
        commercial_maturity="Growth",
        purchase_driver="Versatility",
        ad_creative_direction="Lo-Fi Studio / Warm Lighting",
        recommended_influencer_archetype="Lifestyle Curator",
        ad_copy_hook="Workwear that works anywhere.",
        target_demographic_segments=["Millennials", "Gen Z"],
        target_audience_profile=TargetAudienceProfile(
            age_segments=["25-40"],
            gender_focus="Male",
            income_level="Mid-High",
            psychographics=["Creative", "Urban", "Comfort-Seeker"],
            geo_targeting="Urban Centers",
            shopping_behavior="Quality-Focused"
        )
      )
  )
image_path_example_2 = "gs://vto-demo/cropped_flatlay/outerwear/80949-combat-2-in-1-jacket?srsltid=AfmBOorl129wKcSJsam64LExZ4EcVt_uwF-KJ6GSRhuwcE_zT36EEVdK.png"
trend_data_example_2 = Trend(
    trend_name="The Field Jacket Revival (M-65 Core)",
    executive_summary="As the 'Barn Jacket' craze of 2024 settles, late 2025 has ushered in the return of its tougher, more structured cousin: the Military Field Jacket (specifically the M-65 silhouette). Driven by a collective mood for 'protection' and 'heritage' in uncertain times, this trend prioritizes rugged, multi-pocket functionality that transitions seamlessly from the creative office to the outdoors. Unlike the loose workwear of last year, this look is sharper, featuring cinched waists, epaulets, and 'whip-smart tailoring' that treats the field coat as a blazer alternative.",
    trend_start_date="09/2025",
    trend_scope="Macro",
    trend_lifecycle_stage="Mass Adoption",
    primary_sources=[
    "ELLE Trend Report: 'The Military Jacket Is Back' (Nov 2025)",
    "GQ/Esquire: Best Field Jackets for 2025",
    "Runway Analysis: McQueen & Dior Homme SS26/FW25"
  ],
    key_designers=["Dior Homme", "Alexander McQueen", "Stone Island"],
    social_media_tags=["#FieldJacket", "#M65", "#MilitaryChic"],
    key_influencer_handles=["@warrenalfie", "@takashikumagai_official"],
    essential_look_characteristics={
        "Silhouette": "Structured, cinched waist",
        "Key Details": "Epaulets, multi-pocket functionality",
        "Vibe": "Protective, Heritage"
    },
    taxonomy_attributes=TaxonomyAttributes(
    primary_aesthetic="Heritage Utility",
    secondary_aesthetic="Quiet Outdoors",
    key_garments=[
      "M-65 Field Jacket",
      "Quilted 2-in-1 Liners",
      "Tailored Cargo Trousers"
    ],
    materials_and_textures=[
      "Peached Cotton-Nylon",
      "Waxed Canvas",
      "Matte Heavy-Duty Hardware"
    ],
    color_palette=[
      "Sage Green",
      "Driftwood",
      "Charcoal",
      "Burnt Rubber (Rust)"
    ],
    mood_keywords=[
      "Resilient",
      "Structured",
      "Timeless",
      "Protective"
    ],
    target_occasion=[
      "City Commute",
      "Weekend Travel",
      "Creative Workplace"
    ],
    seasonality="Winter 2025 / Spring 2026"
  ),
  search_vectors=[
    "men's m65 field jacket outfit 2025",
    "relwen combat jacket 2-in-1 styling",
    "military jacket vs barn jacket trend",
    "elevated utility menswear winter 2025"
  ],
    visual_assets=VisualAssets(
    google_images_url="https://www.google.com/search?tbm=isch&q=mens+m65+field+jacket+street+style+2025",
    pinterest_url="https://www.pinterest.com/search/pins/?q=mens+heritage+military+fashion+2025",
    tiktok_search_url="https://www.tiktok.com/search?q=how+to+style+field+jacket+men+2025",
    ai_generation_prompt="A street-style photograph of a creative professional in London wearing a sage green Relwen Combat Field Jacket over a charcoal turtleneck. He is checking his watch, standing near a brick coffee shop. The jacket has a 'lived-in' texture with a popped collar. He is wearing selvedge denim and leather boots. overcast lighting, high texture, 8k resolution."
  ),
  marketing_attributes=MarketingAttributes(
    commercial_maturity="Early Adoption",
    purchase_driver="Durability",
    ad_creative_direction="Outdoor / Street",
    recommended_influencer_archetype="Techwear Enthusiast",
    ad_copy_hook="Prepared for anything.",
    target_demographic_segments=["Gen Z", "Young Millennials"],
    target_audience_profile=TargetAudienceProfile(
        age_segments=["20-35"],
        gender_focus="Male",
        income_level="Mid",
        psychographics=["Practical", "Streetwear Fan", "Outdoorsy"],
        geo_targeting="Global",
        shopping_behavior="Trend-Driven"
    )
  )
)

class FashionPhotographer:
    @log_function_call
    def __init__(self):
        self.prompt_template = load_prompt_file_from_calling_agent(prompt_filename="../prompts/fashion_photographer.md")


    
    @log_function_call
    def generate_campaign_image(self, product_image_path: str, art_direction: str) -> str:
        """
        Generates a fashion campaign image for a product based on a trend.
        Returns the path to the saved image.
        """

        try:
            # product_image_path = image_path_example_2
            # trend_data = trend_data_example_2


            # Step 2: Generate the Image using Imagen
            # correct method for imagen might differ slightly by SDK version, 
            # assuming client.models.generate_images or similar for Vertex AI Imagen 3
            # NANO BANANA PRO
            

            # _genai_client_global = genai.Client(
            #     vertexai=True,
            #     project='gemini-enterprise-banking-1446',
            #     location="global",  # gemini-3 models require global location
            # )

            
          #   client = genai.Client(vertexai=True, project='gemini-enterprise-banking-1446', location='global')

          #   safety_settings: list = [
          #     genai_types.SafetySetting(
          #         category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
          #         threshold=HarmBlockThreshold.OFF,
          #     ),
          #     genai_types.SafetySetting(
          #         category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
          #         threshold=HarmBlockThreshold.OFF,
          #     ),
          #     genai_types.SafetySetting(
          #         category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
          #         threshold=HarmBlockThreshold.OFF,
          #     ),
          #     genai_types.SafetySetting(
          #         category=HarmCategory.HARM_CATEGORY_HARASSMENT,
          #         threshold=HarmBlockThreshold.OFF,
          #     ),
          # ]
          
          #   generate_image_content_config: genai_types.GenerateContentConfig = (
          #       genai_types.GenerateContentConfig(
          #           temperature=1.0,
          #           top_p=0.95,
          #           max_output_tokens=8192,
          #           safety_settings=safety_settings,
          #       )
          #   )
            
          #   nano_response = client.models.generate_content(
          #       model="gemini-3-pro-image-preview",
          #       contents="Generate an infographic of the current weather in Tokyo.",
          #       config=genai_types.GenerateContentConfig(
          #           response_modalities=["TEXT", "IMAGE"],
          #           image_config=genai_types.ImageConfig(
          #               aspect_ratio="16:9",
          #           ),
          #       ),
          #   )

          #   if nano_response.candidates and len(nano_response.candidates) > 0:
          #     for part in nano_response.candidates[0].content.parts:
          #         if hasattr(part, "inline_data") and part.inline_data:
          #             image_bytes = part.inline_data.data
          #             mime_type = part.inline_data.mime_type or "image/png"
          #             output_dir = "generated_campaigns"
          #             if not os.path.exists(output_dir):
          #                 os.makedirs(output_dir)
          #             output_path = f"{output_dir}/campaign_{base64.urlsafe_b64encode(os.urandom(6)).decode()}.png"
          #             # generated_image.image is likely bytes or needs saving
          #             # Check SDK structure. Usually it has .image_bytes or .image
          #             if hasattr(part.inline_data, "data"):
          #                 image_bytes = part.inline_data.data
          #                 # If it's PIL or bytes
          #                 with open(output_path, "wb") as f:
          #                     f.write(image_bytes)
          #                 print(output_path)
          #             elif hasattr(part.inline_data, "image"):
          #                 # If it's PIL or bytes
          #                 with open(output_path, "wb") as f:
          #                     f.write(image_bytes)
          #                 print(output_path)
          #             elif hasattr(part.inline_data, "image_bytes"):
          #                 with open(output_path, "wb") as f:
          #                     f.write(image_bytes)
          #                 print(output_path)
          #             # else:
          #             #     # Fallback if SDK structure is different (e.g. just raw bytes in response?)
          #             #     # But checking typical Google GenAI SDK
          #             #     generated_image.save(output_path)

          #             return str(os.path.abspath(output_path))
                      # END NANO BANANA PRO

                      # # Save the image directly as an artifact using tool_context
                      # # This is the recommended ADK pattern for saving binary artifacts
                      # # Note: save_artifact is async, so we must await it
                      # try:
                      #     image_artifact = types.Part.from_bytes(
                      #         data=image_bytes,
                      #         mime_type=mime_type
                      #     )
                      #     artifact_filename = "infographic.png"
                      #     version = await tool_context.save_artifact(
                      #         filename=artifact_filename,
                      #         artifact=image_artifact
                      #     )
                      #     logger.info(f"Saved infographic artifact: {artifact_filename} (version {version})")

                      #     # Also store base64 in state for AG-UI frontend display
                      #     b64_image = base64.b64encode(image_bytes).decode('utf-8')
                      #     tool_context.state["infographic_base64"] = f"data:{mime_type};base64,{b64_image}"

                      #     return {
                      #         "status": "success",
                      #         "message": f"Infographic generated and saved as artifact '{artifact_filename}'",
                      #         "artifact_saved": True,
                      #         "artifact_filename": artifact_filename,
                      #         "artifact_version": version,
                      #         "mime_type": mime_type,
                      #     }
                      # except Exception as save_error:
                      #     logger.warning(f"Failed to save artifact: {save_error}")
                      #     # Still return success with base64 data as fallback
                      #     return {
                      #         "status": "success",
                      #         "message": "Infographic generated but artifact save failed",
                      #         "artifact_saved": False,
                      #         "image_data": base64.b64encode(image_bytes).decode("utf-8"),
                      #         "mime_type": mime_type,
                      #         "save_error": str(save_error),
                      #     }
# NANO BANANA

            client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
            print(f"art_direction is {art_direction}")
            images = []
            gcs_images = [product_image_path]
            for gcs_image in gcs_images:
              print(f"gcs_image is {gcs_image}")
              # bucket_name = gcs_image["bucket"]
              # source_blob_name = gcs_image["path"]
              bucket_name = (
                  gcs_image.replace("gs://", "").replace("https://", "").split("/")[0]
              )
              source_blob_name = (
                  gcs_image.replace("gs://", "")
                  .replace("https://", "")
                  .replace(f"{bucket_name}/", "")
              )
              print(f"bucket_name is {bucket_name}, source_blob_name is {source_blob_name}")
              image_bytes = download_blob_to_bytes(bucket_name, source_blob_name)
              print(f"image_bytes length is {len(image_bytes)}")
              # contents.append(Image.open(io.BytesIO(image_bytes)))
              images.append(image_bytes)
              # combo_name.append(source_blob_name.split("/")[-1].replace(".png", ""))

            contents = [
                art_direction,
                Image.open(io.BytesIO(images[0])),
                # Image.open(io.BytesIO(images[1])),
            ]
            safety_settings = PROTOTYPE_SAFETY_SETTINGS
            
              
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                # contents="Generate an infographic of the current weather in Tokyo.",
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
                    safety_settings=safety_settings,
                ),
            )

            for part in response.parts:
                print("valid repsonse checkpoint 1")
                if part.inline_data and part.inline_data.data:
                    print("valid repsonse checkpoint 2")
                    image_bytes = part.inline_data.data

                    # Save the image
                    output_dir = "generated_campaigns"
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    
                    output_path = f"{output_dir}/campaign_{base64.urlsafe_b64encode(os.urandom(6)).decode()}.png"
                    
                    
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                      
# END NANO BANANA
# IMAGEN
            imagen_response = client.models.generate_images(
                model=IMAGEN_MODEL_NAME,
                prompt=art_direction,
                config=genai_types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="3:4", # Portrait for fashion
                    safety_filter_level="block_medium_and_above", 
                    person_generation="allow_adult",
                )
            )

            if imagen_response.generated_images:
                generated_image = imagen_response.generated_images[0]
                
                # Save the image
                output_dir = "generated_campaigns"
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                output_path = f"{output_dir}/campaign_{base64.urlsafe_b64encode(os.urandom(6)).decode()}.png"
                
                # generated_image.image is likely bytes or needs saving
                # Check SDK structure. Usually it has .image_bytes or .image
                if hasattr(generated_image, "image"):
                     # If it's PIL or bytes
                     with open(output_path, "wb") as f:
                         f.write(generated_image.image.image_bytes)
                elif hasattr(generated_image, "image_bytes"):
                     with open(output_path, "wb") as f:
                         f.write(generated_image.image_bytes)
                else:
                    # Fallback if SDK structure is different (e.g. just raw bytes in response?)
                    # But checking typical Google GenAI SDK
                    generated_image.save(output_path)

                return str(os.path.abspath(output_path))
            
            return None

        except Exception as e:
            logging.error(f"Fashion Photography Failed: {e}")
            return None
