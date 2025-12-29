import os
import uvicorn
from fastapi import FastAPI
from google.adk import get_fast_api_app

from app.agent import root_agent

# Initialize FastAPI app using ADK's helper
# This automatically sets up the agent endpoints
app: FastAPI = get_fast_api_app(
    agent=root_agent,
    allow_origins=["*"] # For demo purposes
)

@app.get("/")
async def root():
    return {"message": "Agentic Retail Demo API is Running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
