import asyncio
import os
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment variables
load_dotenv('.env.davos')

from retail_ops.agent import agent

async def main():
    session_service = InMemorySessionService()
    await session_service.create_session(app_name="Couche_Tard_Marketing", user_id="user", session_id="storyboard_session")
    
    runner = Runner(agent=agent, app_name="Couche_Tard_Marketing", session_service=session_service)

    prompts = [
        "Identify stores with high fuel traffic but low conversion on 'Fresh Food Fast' items.",
        "Details for product SKU F-PIZZA-001.",
        "Focusing on Breakfast Pizza (SKU F-PIZZA-001), analyze the consumption gaps for hot weather weekends to create a 'Pizza & Sloche' bundle concept.",
        "Create a trend board for the 'Summer Refresh' bundle: SKU F-PIZZA-001 and Sloche.",
        "Create scene concepts for a social media ad featuring a 'Sloche' and Breakfast Pizza in an urban Montreal setting.",
        "Create a 6-second social video for the 'Sloche & Pizza' bundle for the Montreal market."
    ]

    for i, prompt in enumerate(prompts, 2):
        print(f"\n=== Scene {i}: {prompt[:50]}... ===")
        async for event in runner.run_async(
            user_id="user", session_id="storyboard_session",
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
        ):
            if event.is_final_response():
                print(f"\n--- Agent Response (Scene {i}) ---")
                print(event.content.parts[0].text)
                print("--------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
