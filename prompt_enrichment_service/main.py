from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

app = FastAPI(title="Prompt Enrichment Service", version="1.0.0")

# Mock OpenAI client
# client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class EnrichRequest(BaseModel):
    prompt: str

class EnrichResponse(BaseModel):
    enriched_prompt: str
    llm_response: str

@app.get("/health")
async def health_check():
    """Health check endpoint to verify service is running."""
    return {"status": "healthy", "service": "Prompt Enrichment Service"}

# --- Mock Context APIs ---

async def get_user_behavior_extraction() -> str:
    """Mock API for user behavior extraction."""
    # TODO: Replace with actual API call
    await asyncio.sleep(0.5) # Simulate network delay
    return "User prefers clear, stepwise, and actionable instructions."

async def get_user_core_behavior_extraction() -> str:
    """Mock API for user core behavior extraction."""
    # TODO: Replace with actual API call
    await asyncio.sleep(0.5)
    return "User is a software engineer interested in AI and robust system architectures."

async def get_user_profile_information() -> str:
    """Mock API for user profile information."""
    # TODO: Replace with actual API call
    await asyncio.sleep(0.5)
    return "User context: Technical background, prefers Python and Node.js."

# --- Main Enrichment Endpoint ---

@app.post("/enrich", response_model=EnrichResponse)
async def enrich_prompt(request: EnrichRequest):
    """
    Receives a prompt (secured or raw), fetches context from 3 APIs,
    combines them, and queries the LLM (ChatGPT) to get a final response.
    """
    original_prompt = request.prompt
    
    # Fetch all 3 contexts concurrently
    try:
        behavior_ctx, core_behavior_ctx, profile_ctx = await asyncio.gather(
            get_user_behavior_extraction(),
            get_user_core_behavior_extraction(),
            get_user_profile_information()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching context: {str(e)}")

    # Merge context with the prompt
    merged_prompt = (
        f"Context Information:\n"
        f"- Profile: {profile_ctx}\n"
        f"- Behavior: {behavior_ctx}\n"
        f"- Core Behavior: {core_behavior_ctx}\n\n"
        f"User Prompt:\n"
        f"{original_prompt}\n\n"
        f"Based on the context information provided above, please respond to the user prompt."
    )

    # Query LLM (ChatGPT) - Mocked
    try:
        # Simulate network delay for LLM
        await asyncio.sleep(1.0)
        
        # Mock LLM Response
        llm_answer = (
            f"This is a mock response from the LLM based on the user's prompt: '{original_prompt}'. "
            f"I have considered your profile ({profile_ctx}), your behavior ({behavior_ctx}), and your core behavior ({core_behavior_ctx})."
        )
        
        return EnrichResponse(
            enriched_prompt=merged_prompt,
            llm_response=llm_answer
        )
        
    except Exception as e:
        print(f"LLM Error: {e}")
        # Return a fallback response or raise HTTP exception
        raise HTTPException(status_code=502, detail=f"Error communicating with LLM: {str(e)}")

# To run locally: uvicorn main:app --port 3004 --reload
