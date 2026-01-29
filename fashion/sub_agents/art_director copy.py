from fashion.schema import Trend
from typing import List
from fashion.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
import logging
from google import genai
from google.genai import types as genai_types
from google.cloud import storage
from PIL import Image
import io
import base64
import os
from google.genai.types import HarmBlockThreshold, HarmCategory


class ArtDirector:
    def __init__(self):
        try:
            with open("fashion/prompts/art_director.md", "r") as f:
                self.prompt_template = f.read()
        except Exception as e:
            logging.error(f"Failed to load art_director prompt: {e}")
            self.prompt_template = "Create a fashion image prompt for this product and trend."
    
    def download_blob_to_bytes(self, bucket_name, source_blob_name):
      """Downloads a blob from the bucket to bytes."""

      # Initialize the client
      # (Client looks for credentials in the GOOGLE_APPLICATION_CREDENTIALS env var)
      storage_client = storage.Client()

      # Get the bucket and the blob
      bucket = storage_client.bucket(bucket_name)
      blob = bucket.blob(source_blob_name)

      # Download content as bytes
      blob_data = blob.download_as_bytes()

      print(f"Downloaded blob {source_blob_name} ({len(blob_data)} bytes).")

      return blob_data

    def _generate_style_guide_prompt(self, trend_data: Trend, product_description: str = "") -> str:
      
        attrs = trend_data['taxonomy_attributes']
      
        # --- DYNAMIC INJECTION LOGIC ---
      
        # 1. Hallucinate Fonts based on Aesthetic (Simple logic for demo, can be expanded)
        aesthetic = attrs['primary_aesthetic'].lower()
        if "utility" in aesthetic:
            font_choice = "DIN Pro or Roboto Mono"
        elif "romantic" in aesthetic:
            font_choice = "Didot or Playfair Display"
        elif "futuristic" in aesthetic:
            font_choice = "Eurostile or Helvetia"
        else:
            font_choice = "Helvetica Neue"

        # 2. Hallucinate Hex Codes (The LLM usually does this, but we simulate it here for the prompt template)
        # In a real agent workflow, you'd ask the LLM to pick these.
        colors = attrs['color_palette']
        prompt_template = ""

        try:
          with open("fashion/prompts/graphic_designer.md", "r") as f:
              prompt_template = f.read()
        except Exception as e:
          logging.error(f"Failed to load graphic designer prompt: {e}")
          
        # Constructing the message to the LLM
        llm_instruction = f"""
            Please write an Image Generation Prompt for a Brand Board.
        
            Data to use:
            - Trend: {trend_data['trend_name']}
            - Aesthetic Keywords: {attrs['primary_aesthetic']}, {attrs['secondary_aesthetic']}
            - Moods: {', '.join(attrs['mood_keywords'])}
            - Suggested Font: {font_choice}
            - Color List: {', '.join(colors)} (Please convert these to Hex codes in the prompt)
            # - Product: {product_description}
        
            Style: 
            * A minimalist flat vector brand guideline sheet, presented in the International Typographic Style (Swiss Design)
            * Attempt to align the design with the aesthetic of the trend.
            * Use of modular grid layout for images is preferred
            * While the required sections are important, they should take up less visual space than the rest of the design
            * Logo: genereate a brand logo that is simple and modern, and that aligns with the aesthetic of the trend. Place logo at the top left of the page.
            * Brand Name: The brand name should be placed at the top right of the page.
            * Brand Tagline: The brand tagline should be placed smaller font directly below the brand name.
            * Trend Name: The trend name should be placed at top of the page, centered.

            Required Sections: In addition to other elements, the following two sections are required:
            1. **Palette Section (label:'Palette'):** Square color swatches labeled with large bold text: [Insert Generated Hex Codes].
            2. **Typography Section (label:'Typography'):** A type specimen poster displaying the alphabet in '{font_choice}' font. 
            3. **Mood Keywords:** Mood keywords should be incorporate into the design. It doesn't need to have a dedicated section, but should be reflected in the overall design.


            Imagery Requirements (multiple images should be used, but the following are required):
            1. **Product Image:** One image should be of the product
            2. **Textures:** Multiple textures should be used to represent the materials and textures, taking into consideration {', '.join(attrs['materials_and_textures'])}
            3. **Accessories Image:** One image should represent associated accessories that match the style of the trend. This single image should represent multiple accessories.
            4. **Scene:** One image should represent a scene (without people) based on the trend occasions: {', '.join(attrs['target_occasion'])}
        
            **Crucial**: 
            * None of the images should be labeled. 
            * Only label sections if designated in the prompt.
        
            Apply these to the 'Brand Style Guide' prompt structure defined in your system instructions.
        """
        # prompt_template = prompt_template.replace("{product_description}", product_description)
        # prompt_template = prompt_template.replace("{trend_name}", trend_data.trend_name)
        # prompt_template = prompt_template.replace("{primary_aesthetic}", attrs.primary_aesthetic)
        # prompt_template = prompt_template.replace("{secondary_aesthetic}", attrs.secondary_aesthetic)
        # prompt_template = prompt_template.replace("{mood_keywords}", ', '.join(attrs.mood_keywords))
        # prompt_template = prompt_template.replace("{font_choice}", font_choice)
        # prompt_template = prompt_template.replace("{colors}", ', '.join(colors))
        # print(f"Prompt template is {prompt_template}")
        print(f"llm_instruction is {llm_instruction}")
        
        config = genai_types.GenerateContentConfig(
            **STANDARD_GENERATION_CONFIG,
        )
        
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=llm_instruction,
            config=config,
        )
        print(response.text)
        return response.text
    #   return prompt_template
    #   return llm_instruction
      
    def create_moodboards(self, trend_data: List[Trend], product_image_path: str = "") -> List[str]:
        """
        Generates moodboard options for a campaign based on trend data.
        """
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        
        print(f"trend_data is {trend_data}")
        # Download product image once if provided
        images = []
        if product_image_path:
            print(f"gcs_image is {product_image_path}")
            try:
                bucket_name = (
                    product_image_path.replace("gs://", "").replace("https://", "").split("/")[0]
                )
                source_blob_name = (
                    product_image_path.replace("gs://", "")
                    .replace("https://", "")
                    .replace(f"{bucket_name}/", "")
                )
                image_bytes = self.download_blob_to_bytes(bucket_name, source_blob_name)
                images.append(image_bytes)
            except Exception as e:
                logging.error(f"Failed to download product image: {e}")
        
        moodboard_urls = []

        for trend in trend_data:
            print(f"trend is {trend}")
            attrs = trend['taxonomy_attributes']
            colors = attrs['color_palette']
            
            # Use the loop variable 'trend' here
            prompt_contents = self._generate_style_guide_prompt(trend)
            prompt_contents += (
                f"""

                **CRUCIAL**: 
                * None of the images should be labeled. 
                * Product Image: One image should be of the product {product_image_path}
                * Incorporate some of the following colors into the design: {', '.join(colors)}
                """
            )
            print(f"prompt_contents is {prompt_contents}")
            
            contents = [prompt_contents]
            if images:
                contents.append(Image.open(io.BytesIO(images[0])))
            
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
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
                        safety_settings=safety_settings,
                    ),
                )
                print(response.text)
                
                storage_client = storage.Client()
                bucket_name = "creative-content"
                bucket = storage_client.bucket(bucket_name)
                # Unique name for each moodboard
                moodboard_file_name = f"moodboard_{trend['trend_name'].replace(' ', '_')}_{base64.urlsafe_b64encode(os.urandom(6)).decode()}.png"
                destination_blob_name = f"moodboard/{moodboard_file_name}"

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
                        moodboard_urls.append(public_url)
                        logging.info(f"Generated Moodboard: {public_url}")
            except Exception as e:
                logging.error(f"Moodboard generation failed for trend {trend['trend_name']}: {e}")
                continue

        return moodboard_urls
    
    def create_campaign_directive(self, product_image_path: str, trend_data: Trend) -> str:
        """
        Generates a creative directive (image prompt) for a campaign based on product and trend.
        """
        try:
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

            # Step 1: Generate the Image Prompt using Gemini
            prompt_content = [
                self.prompt_template,
                f"\n\nTrend Data: {trend_data.model_dump_json()}",
                "Product Image:"
            ]
            
            # Load product image bytes for Gemini
            try:
                if product_image_path:
                  image_part = genai_types.Part.from_uri(
                      file_uri=product_image_path, mime_type="image/png"
                  )
                  prompt_content.append(image_part)

                config = genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7, # Slightly higher for creativity
                )
              
            except Exception as e:
                logging.error(f"Failed to load product image for prompt generation: {e}")
                return None
              
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt_content,
                config=config,
            )
            
            art_direction = response.text.strip()
            logging.info(f"Generated Art Direction: {art_direction}")
            return art_direction

        except Exception as e:
            logging.error(f"Art Director Failed: {e}")
            return None
