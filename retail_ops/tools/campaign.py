from retail_ops.config import GCS_BUCKET_NAME, VEO_MODEL_NAME
from retail_ops.schema import TrendAnalysis, CampaignDraft

from typing import List

class CampaignTool:
    def draft_campaign(self, product_name: str, trend: TrendAnalysis) -> CampaignDraft:
        """
        Drafts a campaign based on product and trend analysis.
        """
        return CampaignDraft(
            campaign_name=f"{product_name} x {trend.micro_trend}",
            trend=trend.micro_trend,
            target_audience=trend.target_audience,
            keyframes=[
                "Keyframe 1: Commuter grabbing a fresh cup of coffee.",
                "Keyframe 2: Close up of hot breakfast pizza slice.",
                "Keyframe 3: Happy customer swiping Inner Circle loyalty card."
            ],
            video_url=f"https://storage.googleapis.com/{GCS_BUCKET_NAME or 'demo-bucket'}/campaigns/{product_name}_final.mp4"
        )
    
    def generate_video(self, draft: CampaignDraft) -> str:
        """
        Simulates calling Veo to generate a video.
        """
        # Real implementation would use the Veo model from Vertex AI
        print(f"Generating video using {VEO_MODEL_NAME}...")
        return draft.video_url or "https://example.com/video.mp4"
