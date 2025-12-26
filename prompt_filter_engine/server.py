import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from prompt_filter_engine.pii_detection.redactor import UniversalRedactor

app = FastAPI(title="Prompt Filter Engine API")

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
    enriched_analysis: list[Dict[str, Any]]

@app.get("/health")
def health_check():
    if redactor:
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=503, detail="Redactor not initialized")

@app.post("/filter", response_model=FilterResponse)
def filter_prompt(request: FilterRequest):
    if not redactor:
        raise HTTPException(status_code=503, detail="Redactor service unavailable")
    
    try:
        clean_text, _, enriched = redactor.redact(request.prompt, return_enriched=True)
        return FilterResponse(
            original=request.prompt,
            redacted=clean_text,
            enriched_analysis=enriched
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing prompt: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3003))
    uvicorn.run(app, host="0.0.0.0", port=port)
