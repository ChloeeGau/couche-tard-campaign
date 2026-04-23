import unittest
from unittest.mock import MagicMock, patch
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.davos')

from retail_ops.sub_agents.art_director import ArtDirector
from retail_ops.schema import Trend, TaxonomyAttributes

class TestArtDirectorRefactor(unittest.TestCase):
    def setUp(self):
        self.art_director = ArtDirector()

    @patch('retail_ops.sub_agents.art_director.genai.Client')
    @patch('retail_ops.sub_agents.art_director.storage')
    @patch('retail_ops.sub_agents.art_director.Image')
    def test_create_moodboards_list(self, mock_image, mock_storage, MockClient):
        # Setup mocks
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.text = "Generated Prompt"
        mock_part = MagicMock()
        mock_part.inline_data.data = b"image_data"
        mock_response.parts = [mock_part]
        
        mock_client.models.generate_content.return_value = mock_response
        
        # Test data
        trend1 = Trend(
            trend_name="Morning Coffee Run",
            executive_summary="Desc 1",
            taxonomy_attributes=TaxonomyAttributes(
                primary_aesthetic="Convenience",
                secondary_aesthetic="Warmth",
                key_garments=["Coffee"],
                materials_and_textures=["Hot"],
                color_palette=["#FFFFFF"],
                mood_keywords=["Energizing"],
                target_occasion=["Morning"],
                seasonality="Winter"
            )
        )
        
        trends = [trend1]
        
        # Mock tool_context
        mock_tool_context = MagicMock()
        mock_tool_context._invocation_context.session.state = {
            'product': {
                'media': {'main_image_url': 'retail_ops/data/brand_assets/F-PIZZA-001.png'},
                'core_identifiers': {'brand': 'Couche-Tard (Quebec)'}
            }
        }
        
        # Call method
        import asyncio
        urls = asyncio.run(self.art_director.create_moodboards(trends, mock_tool_context))
        
        # Verify
        self.assertEqual(len(urls), 1)
        print("Successfully generated visual layouts for multiple gaps.")

if __name__ == '__main__':
    unittest.main()
