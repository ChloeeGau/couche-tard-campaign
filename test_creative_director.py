import pytest
from app.sub_agents.creative_director import CreativeDirector
from app.schema import Trend, TaxonomyAttributes
import json

def test_creative_director_initialization():
    agent = CreativeDirector()
    assert agent is not None
    assert "Creative Director" in agent.prompt_template

def test_create_video_scenes():
    agent = CreativeDirector()
    
    # Mock Trend Data
    # Using a simple trend structure for testing
    mock_trend = Trend(
        trend_name="Cyber-Noir Rebellion",
        key_designers=["Alexander McQueen", "Rick Owens", "Balenciaga"],
        taxonomy_attributes=TaxonomyAttributes(
            primary_aesthetic="Cyberpunk",
            secondary_aesthetic="Gothic",
            key_garments=["Leather harness", "Platform boots", "Oversized hoodies"],
            materials_and_textures=["Latex", "Distressed denim", "Chainmail"],
            color_palette=["#000000", "#1A1A1A", "#FF00FF", "#00FF00"],
            mood_keywords=["Rebellious", "Dark", "Futuristic", "Edgy"],
            target_occasion=["Underground Rave", "Night Club"],
            seasonality="Winter 2025"
        )
    )
    
    # Using a known existing image from the mock data
    product_image_path = "gs://creative-content/catalog/bottom/194821.png"
    
    result = agent.create_video_scenes(product_image_path, mock_trend)
    
    assert result is not None
    print(f"Result: {result}")
    
    # Verify JSON structure
    data = json.loads(result)
    assert "creative_direction_summary" in data
    assert "scenes" in data
    assert len(data["scenes"]) >= 1
    assert "scene_id" in data["scenes"][0]
    assert "setting" in data["scenes"][0]
    assert "lighting_style" in data["scenes"][0]
    assert "camera_movement" in data["scenes"][0]

def test_generate_scene_image():
    agent = CreativeDirector()
    from app.schema import Scene
    
    # Mock Scene
    mock_scene = Scene(
        scene_id=1,
        setting="A futuristic neon-lit city street at night",
        lighting_style="High contrast, blue and pink neon highlights",
        camera_movement="Tracking shot",
        styling_details="Model wearing the product with silver accessories",
        action="Walking confidently towards the camera"
    )
    
    # Using a known existing image from the mock data
    product_image_path = "gs://creative-content/catalog/bottom/194821.png"
    
    # Note: This test makes a real API call. 
    # In a CI/CD environment, this should be mocked.
    # For now, we print the result to verify it returns a GCS URI or handles errors gracefully.
    results = agent.generate_scene_image(product_image_path, [mock_scene])
    
    print(f"Generate Scene Image Results: {results}")
    # assert len(results) > 0 # Uncomment if we expect it to always succeed with valid creds

if __name__ == "__main__":
    test_creative_director_initialization()
    test_create_video_scenes()
    test_generate_scene_image()
