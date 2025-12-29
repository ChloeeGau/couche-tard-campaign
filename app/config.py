import os
# GOOGLE_API_KEY: str
# PROJECT_ID: str | None = None
# LOCATION: str = "us-central1"
GCS_BUCKET_NAME: str | None = None
VEO_MODEL_NAME: str = "veo-001"
IMAGEN_MODEL_NAME: str = "imagen-3.0-generate-001"
# GEMINI_MODEL_NAME: str = "gemini-2.5-pro"
NANO_BANANA_PRO_MODEL_NAME: str = "gemini-3.0-pro-image"

# BigQuery Settings
BQ_DATASET: str = "retail_analytics" # Default dataset for observability/inventory if not specified
WITH_MOCKED_DATA: bool = True # Set to True to force use of mocked data

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
GEMINI_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-pro")

STANDARD_GENERATION_CONFIG = {
    "response_mime_type": "application/json",
    "temperature": 0.2,
}