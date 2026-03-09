import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

from prompt_filter_engine.pii_detection.redactor import UniversalRedactor
from prompt_filter_engine.core.auth import verify_service_token

app = FastAPI(title="Prompt Filter Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize UniversalRedactor
# We can initialize it globally or lazily. 
# Global initialization ensures it's ready when the server starts.
try:
    redactor = UniversalRedactor()
    print("UniversalRedactor initialized successfully.")
except Exception as e:
    print(f"Failed to initialize UniversalRedactor: {e}")
    redactor = None

class FilterRequest(BaseModel):
    prompt: str

class FilterResponse(BaseModel):
    original: str
    redacted: str
    labeled: str
    enriched_analysis: list[Dict[str, Any]]

@app.get("/health")
def health_check():
    if redactor:
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=503, detail="Redactor not initialized")

@app.post("/filter", response_model=FilterResponse, dependencies=[Depends(verify_service_token)])
def filter_prompt(request: FilterRequest):
    if not redactor:
        raise HTTPException(status_code=503, detail="Redactor service unavailable")
    
    try:
        clean_text, labeled_text, _, enriched = redactor.redact(request.prompt, return_enriched=True)
        return FilterResponse(
            original=request.prompt,
            redacted=clean_text,
            labeled=labeled_text,
            enriched_analysis=enriched
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing prompt: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3003))
    uvicorn.run(app, host="0.0.0.0", port=port)
