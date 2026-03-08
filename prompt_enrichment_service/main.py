"""
Prompt Enrichment Service — FastAPI app.

Responsibilities:
  1. Fetch user context (profile, behavior, core behavior) concurrently.
  2. Use ATCE to assemble a token-budget-aware, tiered context message list.
  3. Call the LLM with the assembled context.
  4. Persist the completed turn asynchronously (fires Tier 1→2→3 compression
     in the background without blocking the response).
"""

import asyncio
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from openai import AsyncAzureOpenAI
from pydantic import BaseModel
import aiohttp

from context import (
    ATCEConfig,
    RedisConversationStore,
    assemble_messages,
    conversation_store,
    store_turn,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Prompt Enrichment Service", version="2.0.0")

USER_MANAGER_URL = os.environ.get("USER_MANAGER_URL", "http://localhost:8080")

# ---------------------------------------------------------------------------
# Active conversation store
# If REDIS_URL is set, use Redis (durable). Otherwise fall back to in-memory.
# ---------------------------------------------------------------------------

_redis_url = os.environ.get("REDIS_URL", "")

if _redis_url:
    _redis_ttl = int(os.environ.get("REDIS_SESSION_TTL", 86400))
    active_store: RedisConversationStore | None = RedisConversationStore(
        redis_url=_redis_url,
        ttl=_redis_ttl,
    )
    logger.info("[Store] Using Redis store: %s (TTL=%ds)", _redis_url, _redis_ttl)
else:
    active_store = None   # fallback: ATCE will use in-memory conversation_store
    logger.warning(
        "[Store] REDIS_URL not set — using in-memory store. "
        "Sessions will be lost on restart. Set REDIS_URL to enable persistence."
    )


# ---------------------------------------------------------------------------
# FastAPI lifecycle — close Redis connection on shutdown
# ---------------------------------------------------------------------------

@app.on_event("shutdown")
async def _shutdown():
    if active_store is not None:
        await active_store.close()
        logger.info("[Store] Redis connection closed on shutdown")


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

_llm_client: AsyncAzureOpenAI | None = None


def _get_llm_client() -> AsyncAzureOpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncAzureOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            api_version=os.environ.get("OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.environ.get("OPENAI_ENDPOINT"),
        )
    return _llm_client


# ---------------------------------------------------------------------------
# ATCE config (adjust defaults here or via env vars)
# ---------------------------------------------------------------------------

atce_cfg = ATCEConfig(
    max_context_tokens=int(os.environ.get("MAX_CONTEXT_TOKENS", 8192)),
    response_buffer=int(os.environ.get("RESPONSE_BUFFER", 1024)),
    tier1_pair_limit=int(os.environ.get("TIER1_PAIR_LIMIT", 10)),
    compression_chunk_pairs=int(os.environ.get("COMPRESSION_CHUNK_PAIRS", 4)),
    tier2_token_limit=int(os.environ.get("TIER2_TOKEN_LIMIT", 1500)),
    tier3_target_tokens=int(os.environ.get("TIER3_TARGET_TOKENS", 150)),
    model=os.environ.get("INFERENCE_MODEL", os.environ.get("CONDENSATION_MODEL", "gpt-4.1-mini")),
    summarization_model=os.environ.get("SUMMARIZATION_MODEL", os.environ.get("CONDENSATION_MODEL", "gpt-4.1-mini")),
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class EnrichRequest(BaseModel):
    prompt: str
    user_id: str                # Required: identifies the user for fetching context
    session_id: str | None = None  # Optional: identifies the conversation session if known


class EnrichResponse(BaseModel):
    enriched_prompt: str    # The assembled system message (for debugging/logging)
    llm_response: str
    session_id: str
    turn_index: int


# ---------------------------------------------------------------------------
# Mock user context APIs & External API Calls
# ---------------------------------------------------------------------------

async def get_current_session_id(user_id: str) -> str:
    """Fetch the current session ID for the given user from the User Manager."""
    try:
        url = f"{USER_MANAGER_URL}/api/users/{user_id}/current-session"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("current_session_id") or "default"
                else:
                    logger.warning(f"[UserManager] Failed to get session for user {user_id}: {response.status}")
                    return "default"
    except Exception as exc:
        logger.error(f"[UserManager] Error fetching session for user {user_id}: {exc}")
        return "default"

async def get_user_behavior_extraction(user_id: str | None = None) -> str:
    await asyncio.sleep(0.05)
    return "User prefers clear, stepwise, and actionable instructions."


async def get_user_core_behavior_extraction(user_id: str | None = None) -> str:
    await asyncio.sleep(0.05)
    return "User is a software engineer interested in AI and robust system architectures."


async def get_user_profile_information(user_id: str | None = None) -> str:
    await asyncio.sleep(0.05)
    return "Technical background; prefers Python and Node.js."


# ---------------------------------------------------------------------------
# Background task: store turn + persist to Redis
# ---------------------------------------------------------------------------

async def _store_and_persist(
    session_id: str,
    user_message: str,
    llm_response: str,
) -> None:
    """
    Called as a FastAPI BackgroundTask after each response.
    1. Stores the turn in the ATCE tier buffer (may fire Tier 1→2 compression).
    2. Persists the updated session to Redis (if Redis store is active).
    Compression callbacks (persist_fn) handle Tier 2→3 persistence internally.
    """
    try:
        store = active_store or conversation_store
        await store_turn(
            session_id=session_id,
            user_message=user_message,
            assistant_response=llm_response,
            cfg=atce_cfg,
            store=store,
        )

        # Persist current state to Redis after storing the turn
        if active_store is not None:
            logger.info("[_store_and_persist] Persisting session=%s to Redis...", session_id)
            await active_store.persist(session_id)
            logger.info("[_store_and_persist] Done persisting session=%s", session_id)
    except Exception as exc:
        logger.error("[_store_and_persist] ERROR for session=%s: %s", session_id, exc, exc_info=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    store = active_store or conversation_store
    result = {
        "status": "healthy",
        "service": "Prompt Enrichment Service",
        "version": "2.0.0",
        "store": "redis" if active_store else "in-memory",
        "active_sessions": store.session_count(),
    }
    if active_store is not None:
        result["redis_reachable"] = await active_store.ping()
    return result


@app.get("/session/{session_id}/debug")
async def session_debug(session_id: str):
    """Return the memory state of a session (for development and evaluation)."""
    store = active_store or conversation_store

    # For Redis store, ensure the session is loaded before reading
    if active_store is not None:
        await active_store.ensure_loaded(session_id)

    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.debug_summary()


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Evict a session from memory and (if Redis) from the remote store."""
    if active_store is not None:
        await active_store.delete_remote(session_id)
        return {"deleted": session_id, "store": "redis"}

    deleted = conversation_store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id, "store": "in-memory"}


@app.post("/enrich", response_model=EnrichResponse)
async def enrich_prompt(request: EnrichRequest, background_tasks: BackgroundTasks):
    """
    Main enrichment endpoint.

    Flow:
      1. ensure_loaded  — hydrate session from Redis if not in L1 cache.
      2. Fetch user context (profile + behavior) concurrently.
      3. assemble_messages — build tiered, token-budget-aware message list.
      4. Call LLM.
      5. Background task: store_turn + persist to Redis.
    """

    request_start = time.monotonic()
    
    logger.info(f"[INFO] Process started for prompt enrichment. Received user_id: {request.user_id}, session_id: {request.session_id}")

    # 0. Resolve the true session ID by combining user ID + fetched session ID
    current_session = request.session_id
    if not current_session:
        current_session = await get_current_session_id(request.user_id)
        
    actual_session_id = f"{request.user_id}::{current_session}"

    logger.info(
        "[EnrichService:request] actual_session_id=%s user=%s | prompt_len=%d chars | store=%s",
        actual_session_id,
        request.user_id,
        len(request.prompt),
        "redis" if active_store else "in-memory",
    )

    # 1. Ensure session is loaded into L1 cache from Redis (no-op on cache hit)
    if active_store is not None:
        await active_store.ensure_loaded(actual_session_id)

    # 2. Fetch all user context concurrently
    t0 = time.monotonic()
    try:
        behavior_ctx, core_behavior_ctx, profile_ctx = await asyncio.gather(
            get_user_behavior_extraction(request.user_id),
            get_user_core_behavior_extraction(request.user_id),
            get_user_profile_information(request.user_id),
        )
    except Exception as exc:
        logger.error("[EnrichService:user_ctx_error] session=%s | %s", actual_session_id, exc)
        raise HTTPException(status_code=500, detail=f"Error fetching user context: {exc}")

    logger.debug(
        "[EnrichService:user_ctx_done] session=%s | latency=%.3fs",
        actual_session_id, time.monotonic() - t0,
    )

    user_context = (
        f"Profile: {profile_ctx}\n"
        f"Behavior: {behavior_ctx}\n"
        f"Core behavior: {core_behavior_ctx}"
    )

    # 3. ATCE: assemble the token-budget-aware message list
    store = active_store or conversation_store
    messages = assemble_messages(
        session_id=actual_session_id,
        new_message=request.prompt,
        user_context=user_context,
        cfg=atce_cfg,
        store=store,
    )

    enriched_prompt_debug = messages[0]["content"] if messages else ""

    # 4. Call LLM
    t0 = time.monotonic()
    try:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key == "your_api_key_here":
            # ── Mock path ────────────────────────────────────────────────────
            logger.warning(
                "[EnrichService:mock_llm] session=%s | OPENAI_API_KEY not set — mock response",
                actual_session_id,
            )
            session = store.get_or_create(actual_session_id)
            llm_response = (
                f"[MOCK RESPONSE] Received: '{request.prompt}'. "
                f"Turn {session.turn_counter + 1} | session '{actual_session_id}'. "
                f"Context: {len(messages)} msgs "
                f"({len([m for m in messages if m['role'] != 'system'])} history + system)."
            )
        else:
            # ── Real path ────────────────────────────────────────────────────
            logger.debug(
                "[EnrichService:llm_call] session=%s | model=%s | messages=%d",
                actual_session_id, atce_cfg.model, len(messages),
            )
            client = _get_llm_client()
            completion = await client.chat.completions.create(
                model=atce_cfg.model,
                messages=messages,
                max_tokens=atce_cfg.response_buffer,
                temperature=0.7,
            )
            llm_response = completion.choices[0].message.content.strip()
            usage = completion.usage
            logger.info(
                "[EnrichService:llm_done] session=%s | latency=%.2fs | "
                "prompt_tokens=%d | completion_tokens=%d | total_tokens=%d",
                actual_session_id,
                time.monotonic() - t0,
                usage.prompt_tokens if usage else -1,
                usage.completion_tokens if usage else -1,
                usage.total_tokens if usage else -1,
            )

    except Exception as exc:
        logger.error(
            "[EnrichService:llm_error] session=%s | after %.2fs: %s",
            actual_session_id, time.monotonic() - t0, exc,
        )
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    # 5. Store turn + persist to Redis in the background (zero added latency)
    background_tasks.add_task(
        _store_and_persist,
        session_id=actual_session_id,
        user_message=request.prompt,
        llm_response=llm_response,
    )
    logger.debug(
        "[EnrichService:bg_task] session=%s | _store_and_persist registered",
        actual_session_id,
    )

    session = store.get_or_create(actual_session_id)
    total_elapsed = time.monotonic() - request_start
    logger.info(
        "[EnrichService:done] session=%s | total_latency=%.2fs | "
        "response_len=%d chars | turn=%d",
        actual_session_id,
        total_elapsed,
        len(llm_response),
        session.turn_counter + 1,
    )

    return EnrichResponse(
        enriched_prompt=enriched_prompt_debug,
        llm_response=llm_response,
        session_id=actual_session_id,
        turn_index=session.turn_counter + 1,
    )


# To run locally:
# uvicorn main:app --port 3004 --reload
