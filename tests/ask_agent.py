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
    await session_service.create_session(app_name="Couche_Tard_Marketing", user_id="user", session_id="s1")
    
    runner = Runner(agent=agent, app_name="Couche_Tard_Marketing", session_service=session_service)

    print("Sending message to agent...")
    async for event in runner.run_async(
        user_id="user", session_id="s1",
        new_message=types.Content(role="user", parts=[types.Part.from_text(text="Analyze the visual requirements for a campaign featuring SKU F-PIZZA-001 for the Couche-Tard brand. Target the 'Morning Coffee Run' consumption gap.")]),
    ):
        if event.is_final_response():
            print("\n--- Agent Response ---")
            print(event.content.parts[0].text)
            print("----------------------")

if __name__ == "__main__":
    asyncio.run(main())
