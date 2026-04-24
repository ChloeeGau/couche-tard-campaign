import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv('.env.davos')

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
VIDEO_GENERATION_MODEL = os.getenv("VIDEO_GENERATION_MODEL", "veo-3.1-generate-preview")

async def main():
    print(f"Initializing GenAI Client for project: {PROJECT_ID}")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    
    # Load a local image as the source
    image_path = "retail_ops/data/brand_assets/BEV-SLO-001.png"
    print(f"Loading reference image: {image_path}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
        
    request = {
        "model": VIDEO_GENERATION_MODEL,
        "source": {
            "prompt": "A slow zoom in on a vibrant red Sloche cup sitting on a counter, ice cubes clinking inside. High energy.",
            "image": types.Image(
                image_bytes=image_bytes,
                mime_type="image/png"
            ),
        },
        "config": types.GenerateVideosConfig(
            aspect_ratio="9:16",
            generate_audio=False,
            number_of_videos=1,
            duration_seconds=6,
            fps=24,
            person_generation="allow_all",
            enhance_prompt=True,
        ),
    }
    
    print(f"Submitting video generation request using model {VIDEO_GENERATION_MODEL}...")
    try:
        operation = await client.aio.models.generate_videos(**request)
        print(f"Operation submitted: {operation.name}")
        print("Waiting for operation to complete (this may take a few minutes)...")
        
        while not operation.done:
            await asyncio.sleep(10)
            operation = await client.aio.operations.get(operation)
            print(f"Status: Done={operation.done}")
            
        if operation.error:
            print(f"Error: {operation.error}")
        else:
            print("Video generated successfully!")
            video = operation.result.generated_videos[0]
            output_path = "tests/output_veo.mp4"
            with open(output_path, "wb") as f:
                f.write(video.video.video_bytes)
            print(f"Saved video to: {output_path}")
            
    except Exception as e:
        print(f"Failed to generate video: {e}")

if __name__ == "__main__":
    asyncio.run(main())
