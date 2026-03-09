"""
Service Token Authentication for Internal Service Communication

Protects internal Filter Engine endpoints from unauthorized external access.
Only requests with valid X-Service-Token header (matching INTERNAL_SERVICE_TOKEN env var)
are allowed to call the filter endpoints.

Usage in FastAPI routes:
    @app.post("/filter", dependencies=[Depends(verify_service_token)])
    async def filter_prompt(request: FilterRequest):
        ...
"""

import os
from fastapi import Header, HTTPException, Depends

INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")


async def verify_service_token(x_service_token: str = Header(...)) -> None:
    """
    FastAPI dependency for validating service-to-service X-Service-Token header.
    
    Args:
        x_service_token: The X-Service-Token header value
        
    Raises:
        HTTPException 403: If token is missing or invalid
        
    Usage:
        @app.post("/filter", dependencies=[Depends(verify_service_token)])
        def filter_endpoint(...):
            ...
    """
    if not INTERNAL_SERVICE_TOKEN:
        # If token is not configured, allow requests (for development/testing)
        # In production, ensure INTERNAL_SERVICE_TOKEN is always set
        return

    if x_service_token != INTERNAL_SERVICE_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: invalid service token"
        )
