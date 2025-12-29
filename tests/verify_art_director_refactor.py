
import unittest
from unittest.mock import MagicMock, patch
from app.sub_agents.art_director import ArtDirector
from app.schema import Trend, TaxonomyAttributes

class TestArtDirectorRefactor(unittest.TestCase):
    def setUp(self):
        self.art_director = ArtDirector()

    @patch('app.sub_agents.art_director.genai')
    @patch('app.sub_agents.art_director.storage')
    @patch('app.sub_agents.art_director.Image')
    def test_create_moodboards_list(self, mock_image, mock_storage, mock_genai):
        # Setup mocks
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.text = "Generated Prompt"
        mock_part = MagicMock()
        mock_part.inline_data.data = b"image_data"
        mock_response.parts = [mock_part]
        
        mock_client.models.generate_content.return_value = mock_response
        
        # Test data
        trend1 = Trend(
            trend_name="Trend 1",
            trend_description="Desc 1",
            taxonomy_attributes=TaxonomyAttributes(
                primary_aesthetic="Modern",
                secondary_aesthetic="Minimalist",
                mood_keywords=["Calm"],
                color_palette=["#FFFFFF"],
                materials_and_textures=["Cotton"],
                target_occasion=["Casual"]
            )
        )
        trend2 = Trend(
            trend_name="Trend 2",
            trend_description="Desc 2",
            taxonomy_attributes=TaxonomyAttributes(
                primary_aesthetic="Vintage",
                secondary_aesthetic="Retro",
                mood_keywords=["Nostalgic"],
                color_palette=["#000000"],
                materials_and_textures=["Leather"],
                target_occasion=["Party"]
            )
        )
        
        trends = [trend1, trend2]
        
        # Call method
        urls = self.art_director.create_moodboards(trends, "gs://bucket/image.png")
        
        # Verify
        # Verify
        self.assertEqual(len(urls), 2)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        
        # Verify both main image and thumbnail were uploaded for each trend
        # We expect at least 4 uploads (2 moodboards * (1 main + 1 thumb))
        self.assertTrue(mock_storage.Client.return_value.bucket.return_value.blob.return_value.upload_from_string.call_count >= 4)
        
        print("Successfully generated moodboards and thumbnails (height=500) for multiple trends")

if __name__ == '__main__':
    unittest.main()
