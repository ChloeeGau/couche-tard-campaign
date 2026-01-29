from pydantic import BaseModel, Field
from typing import List, Optional, Dict

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
    web_image_url: Optional[str] = None
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

class ProductList(BaseModel):
    products: List[Product]

class TaxonomyAttributes(BaseModel):
    primary_aesthetic: str
    secondary_aesthetic: str
    key_garments: List[str]
    materials_and_textures: List[str]
    color_palette: List[str]
    mood_keywords: List[str]
    target_occasion: List[str]
    seasonality: str

class TargetAudienceProfile(BaseModel):
    age_segments: List[str]
    gender_focus: str
    income_level: str
    psychographics: List[str]
    geo_targeting: str
    shopping_behavior: str

class MarketingAttributes(BaseModel):
    commercial_maturity: Optional[str] = None
    purchase_driver: Optional[str] = None
    ad_creative_direction: Optional[str] = None
    recommended_influencer_archetype: Optional[str] = None
    ad_copy_hook: Optional[str] = None
    target_demographic_segments: Optional[List[str]] = None
    target_audience_profile: Optional[TargetAudienceProfile] = None

class VisualAssets(BaseModel):
    google_images_url: Optional[str] = None
    pinterest_url: Optional[str] = None
    tiktok_search_url: Optional[str] = None
    ai_generation_prompt: Optional[str] = None


class Trend(BaseModel):
    trend_name: str
    executive_summary: str = None
    trend_start_date: str = None
    trend_scope: str = None
    trend_lifecycle_stage: str = None
    primary_sources: List[str] = []
    key_designers: List[str] = []
    social_media_tags: List[str] = []
    key_influencer_handles: List[str] = []
    essential_look_characteristics: Dict[str, str] = {}
    taxonomy_attributes: TaxonomyAttributes
    search_vectors: List[str] = []
    visual_assets: VisualAssets = None
    marketing_attributes: MarketingAttributes = None    

class TrendMatch(BaseModel):
    product: Product
    trend: Trend
    match_score: float
    reasoning: str

class ProductTrendMapping(BaseModel):
    micro_trends: List[TrendMatch]
    macro_trends: List[TrendMatch]

class TrendSpotterOutput(BaseModel):
    trends: List[Trend]

class Scene(BaseModel):
    scene_id: int
    scene_url: str
    setting: str
    lighting_style: str
    camera_movement: str
    styling_details: str
    action: str

class CreativeDirection(BaseModel):
    creative_direction_summary: str
    scenes: List[Scene]

class CampaignDraft(BaseModel):
    campaign_name: str
    trend: str
    target_audience: str
    keyframes: List[str]
    video_url: Optional[str] = None

class TrendStrategy(BaseModel):
    trend_name: str
    strategy_directive: str
    target_audience: str

