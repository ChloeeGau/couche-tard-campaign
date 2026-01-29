from fashion.schema import Product, ProductTrendMapping, TrendMatch, Trend
from typing import Optional
from fashion.config import GEMINI_MODEL_NAME, PROJECT_ID, LOCATION, STANDARD_GENERATION_CONFIG
from google.adk.agents.llm_agent import Agent
import json
import logging
from google import genai
from google.genai import types as genai_types
from google.cloud import storage
import io
from PIL import Image
from urllib.parse import urlparse, unquote
from google.adk.tools import ToolContext
from google.adk.sessions import InMemorySessionService


async def _load_gcs_image(gcs_uri: str, storage_client: storage.Client) -> Optional[genai_types.Part]:
  """Loads an image from GCS and returns it as a Part object.

  Args:
      gcs_uri: The GCS URI of the image. Does not start with "gs://"
      storage_client: The GCS storage client.

  Returns:
      A Part object containing the image data, or None on failure.
  """
  # try:
  bucket_name =  gcs_uri.replace("gs://", "").split("/")[0]
  blob_name = gcs_uri.replace(f"gs://{bucket_name}/", "")
  blob = storage_client.bucket(bucket_name).blob(blob_name)
  image_bytes = blob.download_as_bytes()
  return genai_types.Part.from_bytes(data=image_bytes, mime_type="image/png")
  # except Exception as e:
  #     logging.error(f"Failed to load image from '{gcs_uri}': {e}")
  #     return None


async def normalize_bucket_uri(url: str) -> Optional[str]:
  """Normalizes GCS URLs to gs:// format."""
  print(f"received url: {url}")
  if not url:
      return None
  if url.startswith("gs://"):
      return url

  parsed = urlparse(url)
  path = unquote(parsed.path)

  # Handle virtual hosted style: bucket.storage.googleapis.com
  if parsed.netloc.endswith(".storage.googleapis.com") and parsed.netloc != "storage.googleapis.com":
      bucket = parsed.netloc.replace(".storage.googleapis.com", "")
      obj = path.lstrip("/")
      return f"gs://{bucket}/{obj}"

  # Handle path style: storage.googleapis.com or storage.cloud.google.com
  if parsed.netloc in ["storage.googleapis.com", "storage.cloud.google.com"]:
      # Path is /bucket/object...
      clean_path = path.lstrip("/")
      if "/" in clean_path:
          bucket, obj = clean_path.split("/", 1)
          return f"gs://{bucket}/{obj}"

  return None

from fashion.adk_common.utils import utils_gcs

# TODO move this to a shared utils file 
async def save_image_into_artifact(image_gcs_file_path: str, tool_context: ToolContext) -> Optional[str]:
  """Ensures the product photo artifact exists, creating it if necessary.

  If a `image_gcs_file_path` is provided, it will be used directly.
  Otherwise, it fetches the product's image URI from BigQuery, downloads it
  from GCS, and saves it as an artifact.

  Args:
      product (str): The product name to look up if no filename is provided.
      tool_context (ToolContext): The context for accessing and saving artifacts.
      image_gcs_file_path (Optional[str]): The filename of an existing product
      photo artifact. Defaults to None.

  Returns:
      The filename of the product photo artifact, or None on failure.
  """
  normalized_uri = await normalize_bucket_uri(image_gcs_file_path)
  print(f"normalized_uri: {normalized_uri}")
  artifact_filename = image_gcs_file_path.split("/")[-1].strip()

  if normalized_uri:
      # try:
        storage_client = storage.Client()
        product_photo_part = await _load_gcs_image(normalized_uri, storage_client)
        if product_photo_part:
            
            # artifact_filename="product_image.png"
            # await tool_context.save_artifact(artifact_filename, product_photo_part)
            file = utils_gcs.download_bytes_from_gcs(normalized_uri)

            await tool_context.save_artifact(
                filename=artifact_filename,
                artifact=genai_types.Part.from_bytes(
                    data=file,
                    mime_type="image/png",
                ),
            )

            logging.info(f"Saved product photo from GCS URI '{image_gcs_file_path}' as artifact '{artifact_filename}' of type {type(artifact_filename)}")
            return artifact_filename
        else:
            raise ValueError("Failed to load image from GCS.")
      # except Exception as e:
      #     logging.error(f"Failed to process GCS URI '{image_gcs_file_path}': {e}. Will attempt to fetch from BigQuery.", exc_info=True)
  else:
      logging.error(f"Invalid gcs image '{image_gcs_file_path}': Invalid path.")
      raise ValueError("Failed to load image from GCS.")
  
  try:
      # Verify the artifact exists by trying to load it.
      await tool_context.load_artifact(artifact_filename)
      logging.info(
          f"Using existing product photo artifact: {artifact_filename}"
      )
      return artifact_filename
  except Exception as e:
      logging.warning(
          f"Could not load provided artifact '{artifact_filename}': {e}."
          " Will attempt to fetch from BigQuery."
      )

from google.adk.tools import ToolContext
from google.adk.tools.function_tool import FunctionTool

async def list_session_artifacts(tool_context: ToolContext) -> str:
    """Lists the names of all artifacts currently available in the session."""
    try:
        # The list_artifacts() method returns a list of artifact names (strings)
        artifact_names = await tool_context.list_artifacts()
        
        if not artifact_names:
            return "No artifacts found in the current session."
        
        # Format the list for the agent's response
        return "The following artifacts are available in the session:\n" + "\n".join(
            [f"* {name}" for name in artifact_names]
        )
    except Exception as e:
        return f"An error occurred while trying to list artifacts: {e}"

# To use this function, you would register it as a tool in your agent definition
# Example (part of a larger agent setup):
# agent.tools.append(FunctionTool(list_session_artifacts))


async def retrieve_image_from_gcs(image_path: str, tool_context: ToolContext ) -> str:
  # try:
  print("HERE")
  storage_client = storage.Client()
  image_path = image_path.strip()
  # Extract bucket and blob name from gs:// path
  bucket_name = image_path.replace("gs://", "").split("/")[0]
  source_blob_name = image_path.replace(f"gs://{bucket_name}/", "")
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
      target_height = 500
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
  
  # artifact_name = await save_image_into_artifact(f"https://storage.cloud.google.com/{bucket_name}/{min_blob_name}", tool_context)
  await tool_context.save_artifact(source_blob_name,f"https://storage.cloud.google.com/{bucket_name}/{min_blob_name}")
  artifacts = await list_session_artifacts(tool_context)
  print(f"artifacts: {artifacts}")
  return source_blob_name
  # return f"https://storage.cloud.google.com/{bucket_name}/{min_blob_name}"


  # except Exception as e:
  #     logging.error(f"Failed to retrieve/process image from GCS: {e}")
  #     # Fallback to original logic if something fails, or just return original URL
  #     source_blob_name = (
  #         image_path.replace("gs://", "")
  #         .replace("https://storage.cloud.google.com", "")
  #     )
  #     return "https://storage.cloud.google.com/" + source_blob_name

# async def identify_product_from_image(self, image_path: str) -> Product:
#   """
#   Analyzes an image to identify the product and maps it to the Product schema.
#   """
#   try:
#       prompt_content = [
#           "Analyze this image and extract product details to populate the Product schema. Estimate fields like price if unknown, or use reasonable defaults. Generate a SKU if not visible.\n"
#       ]
      
#       image_part = genai_types.Part.from_uri(
#           file_uri=image_path, mime_type="image/png"
#       )
#       prompt_content.ap
async def load_image_bytes_from_artifact(artifact_name: str, tool_context: ToolContext):
    """Loads image bytes from an existing artifact for analysis.
    
    Args:
        artifact_name: The name of the artifact to load.
        tool_context: The tool context.
        
    Returns:
        The image artifact object.
    """
    logging.info(f"Loading artifact: {artifact_name}")
    try:
        artifact = await tool_context.load_artifact(artifact_name)
        if artifact:
          print(f"returning artifact: {artifact} of type {type(artifact)}")
          return artifact
        return f"Artifact {artifact_name} not found."
    except Exception as e:
        logging.error(f"Error loading artifact {artifact_name}: {e}")
        return f"Error loading artifact: {e}"
        
# async def temp_load_image(artifact_path: str, tool_context: ToolContext):
#     images = []
#     file = utils_gcs.download_bytes_from_gcs("gs://creative-content/catalog/top/109244.png")

#     await tool_context.save_artifact(
#         filename=f"test_file.png",
#         artifact=genai_types.Part.from_bytes(
#             data=file,
#             mime_type="image/png",
#         ),
#     )
#     image_part = await tool_context.load_artifact(filename=f"test_file.png")
#     return image_part
        
class ProductTrendMapperAgent:
    def __init__(self):
      try:
          with open("fashion/prompts/product_trend_mapper.md", "r") as f:
              self.prompt_template = f.read()
      except Exception as e:
          logging.error(f"Failed to load product_trend_mapper prompt: {e}")
      self.agent = Agent(
          name="product_trend_mapper_agent",
          model=GEMINI_MODEL_NAME,
          instruction=self.prompt_template,
          tools=[
            retrieve_image_from_gcs,
            load_image_bytes_from_artifact
          ]
      )

  