import os
from google.genai import types as genai_types
from google.genai.types import HarmBlockThreshold, HarmCategory
from pydantic import Field
from pydantic_settings import BaseSettings


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
GEMINI_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
# LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "global")
# GEMINI_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3-flash-preview")
IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL_NAME", "gemini-3-pro-image-preview")
# GEMINI_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3-flash-preview")

STANDARD_GENERATION_CONFIG = {
    "response_mime_type": "application/json",
    "temperature": 0.2,
}

PROTOTYPE_SAFETY_SETTINGS: list = [
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

class AgentSettings(BaseSettings):
    """Agent configuration settings."""

    agent_name: str = Field(
        default="davos_fashion_campaign",
        description="Display name for the agent (must be a valid identifier)",
    )
    agent_description: str = Field(
        default="Build campaign for fashion product",
        description="Agent description",
    )

    model: str = Field(default="gemini-2.5-flash", description="Google AI model to use")

    # sharepoint_datastore_id: str = Field(
    #     # default="projects/gemini-enterprise-banking-1446/locations/global/collections/default_collection/dataStores/davos-sharepoint_1768436733774",
    #     default="projects/gemini-enterprise-banking-1446/locations/global/collections/default_collection/dataStores/davos-sharepoint_1768436733774",
    #     description="Datastore URI to use for sharepoint grounding",
    # )

    sharepoint_datastore_id: str = Field(
        default="projects/gemini-enterprise-banking-1446/locations/global/collections/default_collection/dataStores/davos-sharepoint_1768436733774_file",
        description="Datastore URI to use as grounding",
    )

    # datastore_id: str = Field(
    #     default="projects/gemini-enterprise-banking-1446/locations/global/collections/default_collection/dataStores/cymbal-docs_1761668997157_gcs_store",
    #     description="Datastore URI to use as grounding",
    # )

    class Config:
        env_prefix = "AGENT_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
