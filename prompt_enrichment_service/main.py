"""
Prompt Enrichment Service — FastAPI app (Dual-Mode).

Two modes controlled by the `source` field in the request:

  source="mcp" (LLM web apps — ChatGPT, Claude, Gemini, etc.):
    1. Sync unsynced chat logs from MongoDB into ATCE Redis.
    2. Fetch user behavior enrichment (profile, behavior, core behavior).
    3. Return enriched user prompt + behaviors ONLY (no LLM call, no ATCE history).
       LLM apps maintain their own conversation context.

  source="web_client" (own chat platform):
    1. Fetch user context concurrently.
    2. Use ATCE to assemble a token-budget-aware, tiered context message list.
    3. Call the OpenAI API with the assembled context.
    4. Persist the completed turn asynchronously.
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
CHAT_LOGGER_URL = os.environ.get("CHAT_LOGGER_URL", "http://localhost:3005")
PREDEFINED_PROFILE_URL = os.environ.get("PREDEFINED_PROFILE_URL", "http://localhost:8002")
BEHAVIOR_EXTRACTION_URL = os.environ.get("BEHAVIOR_EXTRACTION_URL", "http://localhost:8001")

# ---------------------------------------------------------------------------
# Active conversation store
# If REDIS_URL is set, use Redis (durable). Otherwise fall back to in-memory.
# ---------------------------------------------------------------------------

_redis_url = os.environ.get("REDIS_URL", "")

if _redis_url:
    _redis_ttl = int(os.environ.get("REDIS_SESSION_TTL", 432000))
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
    source: str = "web_client"     # "mcp" | "web_client" — determines enrichment mode
    mcp_client: str | None = None  # Optional: specific client name (e.g., 'claude_desktop')


class EnrichResponse(BaseModel):
    enriched_prompt: str    # The assembled system message (for debugging/logging)
    llm_response: str | None = None  # None when source="mcp"
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

async def get_predefined_profile_id(user_id: str) -> str:
    """Fetch the predefined profile ID for the given user from the User Manager."""
    try:
        url = f"{USER_MANAGER_URL}/api/users/{user_id}/predefined-profile-id"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("predefined_profile_id")
                else:
                    logger.warning(f"[UserManager] Failed to get predefined profile id for user {user_id}: {response.status}")
    except Exception as exc:
        logger.error(f"[UserManager] Error fetching predefined profile id for user {user_id}: {exc}")
    return ""


async def get_predefined_profile(profile_id: str) -> str:
    """Fetch the predefined profile details given a profile ID."""
    if not profile_id:
        return "No predefined profile available."
    try:
        url = f"{PREDEFINED_PROFILE_URL}/api/predefined-profiles/{profile_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    profile_str = []
                    if data.get("profile_name"):
                        profile_str.append(f"Profile: {data['profile_name']}")
                    if data.get("context_statement"):
                        profile_str.append(f"Context: {data['context_statement']}")
                    if data.get("assumptions"):
                        profile_str.append("Assumptions: " + ", ".join(data["assumptions"]))
                    if data.get("ai_guidance"):
                        profile_str.append("Guidance: " + ", ".join(data["ai_guidance"]))
                    if data.get("preferred_response_style"):
                        profile_str.append("Style: " + ", ".join(data["preferred_response_style"]))
                    if data.get("context_injection_prompt"):
                        profile_str.append(f"Injection: {data['context_injection_prompt']}")
                    return "\n".join(profile_str) if profile_str else "Empty Predefined Profile."
                else:
                    logger.warning(f"[ProfileService] Failed to get profile {profile_id}: {response.status}")
    except Exception as exc:
        logger.error(f"[ProfileService] Error fetching profile {profile_id}: {exc}")
    return "Failed to fetch predefined profile."


async def get_latest_chat_log(user_id: str, selected_session_id: str) -> tuple[list, str | None]:
    """Fetch the latest chat turn for behavior extraction, and the source of that log."""
    try:
        url = f"{CHAT_LOGGER_URL}/api/chats?user_id={user_id}&selected_session_id={selected_session_id}&limit=1&sort_desc=true"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    chat_logs = await response.json()
                    recent_history = []
                    last_source = None
                    if chat_logs:
                        log = chat_logs[0]
                        last_source = log.get("source")
                        if log.get("user_prompt"):
                            recent_history.append({"role": "user", "text": log["user_prompt"]})
                        if log.get("llm_response"):
                            recent_history.append({"role": "assistant", "text": log["llm_response"]})
                    return recent_history, last_source
                else:
                    logger.warning(f"[ChatLogger] Failed to get latest chat log: {response.status}")
    except Exception as exc:
        logger.error(f"[ChatLogger] Error fetching latest chat logs: {exc}")
    return [], None


async def get_behavior_extraction_data(prompt: str, user_id: str, session_id: str, recent_history: list) -> str:
    """Post to Behavior Extraction service and return the extracted string."""
    try:
        url = f"{BEHAVIOR_EXTRACTION_URL}/v2/extract"
        payload = {
            "prompt": prompt,
            "user_id": user_id,
            "session_id": session_id,
            "recent_history": recent_history
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("extracted_behavior") or data.get("behavior") or str(data)
                else:
                    logger.warning(f"[BehaviorService] Failed extraction: {response.status}")
    except Exception as exc:
        logger.error(f"[BehaviorService] Error positing to extraction: {exc}")
    return "No behavior extracted."


async def get_user_core_behavior_extraction(user_id: str | None = None) -> str:
    await asyncio.sleep(0.05)
    return "Chathura will provide the core_behavior mock"


# ---------------------------------------------------------------------------
# sync_mcp_turns — bridge MongoDB chat logs into ATCE Redis (source=mcp only)
# ---------------------------------------------------------------------------

async def sync_mcp_turns(
    session_id: str,
    user_id: str,
    selected_session_id: str,
    store,
    cfg: ATCEConfig,
) -> int:
    """
    Fetches unsynced chat logs from chat-logger-backend (MongoDB) and
    injects them into ATCE via store_turn().

    Only runs for source="mcp". Returns the number of turns synced.
    """
    synced = 0
    try:
        # Get current ATCE state to know how many turns are already synced
        session = store.get_or_create(session_id)
        current_turn = session.turn_counter

        url = (
            f"{CHAT_LOGGER_URL}/api/chats"
            f"?user_id={user_id}"
            f"&selected_session_id={selected_session_id}"
            f"&limit=100"
        )

        logger.info(
            "[sync_mcp_turns] session=%s | fetching unsynced turns from chat-logger-backend | "
            "current_atce_turn=%d | url=%s",
            session_id, current_turn, url,
        )

        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.warning(
                        "[sync_mcp_turns] session=%s | chat-logger-backend returned status=%d",
                        session_id, response.status,
                    )
                    return 0

                chat_logs = await response.json()

        logger.info(
            "[sync_mcp_turns] session=%s | fetched %d chat logs from MongoDB",
            session_id, len(chat_logs),
        )

        # Skip already-synced turns robustly by matching _id or last user prompt
        last_synced_id = session.facts.get("last_synced_mongo_id")
        start_idx = 0

        if last_synced_id:
            for i, log in enumerate(chat_logs):
                if log.get("_id") == last_synced_id:
                    start_idx = i + 1
                    break
        elif session.turn_counter > 0:
            # Legacy/fallback: find the last user message in tier1_buffer and match it
            last_user_msg = next((m.content for m in reversed(session.tier1_buffer) if m.role == "user"), None)
            if last_user_msg:
                for i in range(len(chat_logs) - 1, -1, -1):
                    if chat_logs[i].get("user_prompt") == last_user_msg:
                        start_idx = i + 1
                        break
            else:
                # If tier1 is empty (fully compressed to tier2) but turns exist, be safe
                start_idx = len(chat_logs)

        unsynced_logs = chat_logs[start_idx:]

        if not unsynced_logs:
            logger.info(
                "[sync_mcp_turns] session=%s | no new turns to sync",
                session_id,
            )
            return 0

        for log in unsynced_logs:
            user_prompt = log.get("user_prompt", "")
            llm_response = log.get("llm_response", "")

            if user_prompt and llm_response:
                await store_turn(
                    session_id=session_id,
                    user_message=user_prompt,
                    assistant_response=llm_response,
                    cfg=cfg,
                    store=store,
                )
                synced += 1
                logger.info(
                    "[sync_mcp_turns] session=%s | synced turn %d | "
                    "user_prompt_len=%d | llm_response_len=%d",
                    session_id, session.turn_counter,
                    len(user_prompt), len(llm_response),
                )

        # Update last synced ID in facts
        if unsynced_logs:
            session.facts["last_synced_mongo_id"] = unsynced_logs[-1].get("_id", "")

        # Persist to Redis after syncing
        if active_store is not None and synced > 0:
            await active_store.persist(session_id)
            logger.info(
                "[sync_mcp_turns] session=%s | persisted %d synced turns to Redis",
                session_id, synced,
            )

    except Exception as exc:
        logger.error(
            "[sync_mcp_turns] session=%s | ERROR syncing turns: %s",
            session_id, exc, exc_info=True,
        )

    return synced


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
    Main enrichment endpoint (Dual-Mode).

    source="mcp" flow:
      1. Resolve session ID.
      2. Sync unsynced turns from MongoDB into ATCE Redis.
      3. Fetch user behavior enrichment (3 services).
      4. Return enriched user prompt + behaviors ONLY (no LLM call).

    source="web_client" flow:
      1. Resolve session ID, ensure_loaded from Redis.
      2. Fetch user context concurrently.
      3. assemble_messages — build tiered, token-budget-aware message list.
      4. Call OpenAI API.
      5. Background task: store_turn + persist to Redis.
    """

    request_start = time.monotonic()

    logger.info(
        "[EnrichService:request] source=%s | user_id=%s | session_id=%s | prompt_len=%d chars",
        request.source, request.user_id, request.session_id, len(request.prompt),
    )

    # 0. Resolve the true session ID by combining user ID + fetched session ID
    current_session = request.session_id
    if not current_session:
        current_session = await get_current_session_id(request.user_id)

    actual_session_id = f"{request.user_id}::{current_session}"

    logger.info(
        "[EnrichService:session] actual_session_id=%s | source=%s | store=%s",
        actual_session_id, request.source,
        "redis" if active_store else "in-memory",
    )

    store = active_store or conversation_store

    # ===================================================================
    # SOURCE = "mcp" — LLM web apps (ChatGPT, Claude, Gemini, etc.)
    # Return: enriched user prompt + behavior services ONLY
    # LLM apps keep their own conversation context.
    # We sync MongoDB chat logs into ATCE for our own tracking.
    # ===================================================================
    if request.source == "mcp":
        logger.info(
            "[EnrichService:mcp] session=%s | MCP mode — returning behaviors only, no LLM call",
            actual_session_id,
        )

        # 1. Ensure session is loaded into L1 cache from Redis
        if active_store is not None:
            await active_store.ensure_loaded(actual_session_id)

        # 2. Sync unsynced turns from MongoDB into ATCE Redis
        t0 = time.monotonic()
        synced_count = await sync_mcp_turns(
            session_id=actual_session_id,
            user_id=request.user_id,
            selected_session_id=current_session,
            store=store,
            cfg=atce_cfg,
        )
        logger.info(
            "[EnrichService:mcp_sync] session=%s | synced %d turns | latency=%.3fs",
            actual_session_id, synced_count, time.monotonic() - t0,
        )

        # 3. Fetch user behavior enrichment concurrently
        t0 = time.monotonic()
        try:
            profile_id, (recent_history, last_source) = await asyncio.gather(
                get_predefined_profile_id(request.user_id),
                get_latest_chat_log(request.user_id, current_session),
            )
            
            profile_ctx, behavior_ctx, core_behavior_ctx = await asyncio.gather(
                get_predefined_profile(profile_id),
                get_behavior_extraction_data(request.prompt, request.user_id, current_session, recent_history),
                get_user_core_behavior_extraction(request.user_id),
            )
        except Exception as exc:
            logger.error("[EnrichService:mcp_ctx_error] session=%s | %s", actual_session_id, exc)
            raise HTTPException(status_code=500, detail=f"Error fetching user context: {exc}")

        user_context = (
            f"Profile: {profile_ctx}\n"
            f"Behavior: {behavior_ctx}\n"
            f"Core behavior: {core_behavior_ctx}"
        )

        logger.info(
            "[EnrichService:mcp_behaviors] session=%s | behavior_len=%d | core_behavior_len=%d | profile_len=%d | latency=%.3fs",
            actual_session_id, len(behavior_ctx), len(core_behavior_ctx), len(profile_ctx),
            time.monotonic() - t0,
        )

        # 3.5 Check if client switch happened
        atce_history_str = ""
        if request.mcp_client and last_source and request.mcp_client != last_source:
            logger.info(f"[EnrichService:mcp] Client switch detected {last_source} -> {request.mcp_client}")
            print(f">>> [SYS OUT] ATCE USED! User switched LLM clients from {last_source} to {request.mcp_client}. Injecting previous conversation history...")
            
            session_mem = store.get(actual_session_id)
            if session_mem:
                history_lines = ["\n--- Previous Conversation Context (ATCE) ---"]
                if session_mem.tier3_core_memory:
                    history_lines.append(f"Core Memory:\n{session_mem.tier3_core_memory}\n")
                
                if session_mem.tier2_summaries:
                    history_lines.append("Recent Topic Summaries:")
                    for s in session_mem.tier2_summaries:
                        history_lines.append(f"- {s.text}")
                    history_lines.append("")
                
                if session_mem.tier1_buffer:
                    history_lines.append("Recent Messages:")
                    for msg in session_mem.tier1_buffer:
                        role = "User" if msg.role == "user" else "Assistant"
                        history_lines.append(f"[{role}]: {msg.content}")
                
                history_lines.append("------------------------------------------\n")
                atce_history_str = "\n".join(history_lines)
            else:
                print(">>> [SYS OUT] ATCE NOT USED: No existing session found.")
        else:
            print(">>> [SYS OUT] ATCE NOT USED: Same LLM client or first message.")

        # 4. Build enriched prompt (user prompt + behaviors, maybe ATCE history)
        enriched_prompt = (
            f"{user_context}\n\n"
        )
        if atce_history_str:
            enriched_prompt += f"{atce_history_str}\n"

        enriched_prompt += f"User Prompt: {request.prompt}"

        print("\n\n=== [SYS OUT] MOCK MCP ENRICHED PROMPT ===")
        print(enriched_prompt)
        print("==========================================\n\n")

        session = store.get_or_create(actual_session_id)
        total_elapsed = time.monotonic() - request_start
        logger.info(
            "[EnrichService:mcp_done] session=%s | total_latency=%.2fs | "
            "enriched_prompt_len=%d chars | turn=%d | synced_turns=%d",
            actual_session_id, total_elapsed,
            len(enriched_prompt), session.turn_counter + 1, synced_count,
        )

        return EnrichResponse(
            enriched_prompt=enriched_prompt,
            llm_response=None,
            session_id=actual_session_id,
            turn_index=session.turn_counter + 1,
        )

    # ===================================================================
    # SOURCE = "web_client" — own chat platform
    # Full ATCE context assembly + OpenAI API LLM call
    # ===================================================================
    logger.info(
        "[EnrichService:web_client] session=%s | Web client mode — full ATCE + LLM call",
        actual_session_id,
    )

    # 1. Ensure session is loaded into L1 cache from Redis (no-op on cache hit)
    if active_store is not None:
        await active_store.ensure_loaded(actual_session_id)

    # 2. Fetch all user context concurrently
    t0 = time.monotonic()
    try:
        profile_id, (recent_history, last_source) = await asyncio.gather(
            get_predefined_profile_id(request.user_id),
            get_latest_chat_log(request.user_id, current_session),
        )

        profile_ctx, behavior_ctx, core_behavior_ctx = await asyncio.gather(
            get_predefined_profile(profile_id),
            get_behavior_extraction_data(request.prompt, request.user_id, current_session, recent_history),
            get_user_core_behavior_extraction(request.user_id),
        )
    except Exception as exc:
        logger.error("[EnrichService:user_ctx_error] session=%s | %s", actual_session_id, exc)
        raise HTTPException(status_code=500, detail=f"Error fetching user context: {exc}")

    logger.info(
        "[EnrichService:user_ctx_done] session=%s | behavior_len=%d | core_behavior_len=%d | profile_len=%d | latency=%.3fs",
        actual_session_id, len(behavior_ctx), len(core_behavior_ctx), len(profile_ctx),
        time.monotonic() - t0,
    )

    user_context = (
        f"Profile: {profile_ctx}\n"
        f"Behavior: {behavior_ctx}\n"
        f"Core behavior: {core_behavior_ctx}"
    )

    # 3. ATCE: assemble the token-budget-aware message list
    messages = assemble_messages(
        session_id=actual_session_id,
        new_message=request.prompt,
        user_context=user_context,
        cfg=atce_cfg,
        store=store,
    )

    debug_lines = []
    for m in messages:
        role = m.get("role", "unknown").upper()
        content = m.get("content", "")
        debug_lines.append(f"[{role}]\n{content}")
    enriched_prompt_debug = "\n\n".join(debug_lines)

    print("\n\n=== [SYS OUT] MOCK WEB_CLIENT ENRICHED PROMPT ===")
    print(enriched_prompt_debug)
    print("=================================================\n\n")

    # 4. Call LLM
    t0 = time.monotonic()
    try:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key == "your_api_key_here":
            # -- Mock path --
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
            # -- Real path --
            logger.info(
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
    logger.info(
        "[EnrichService:bg_task] session=%s | _store_and_persist registered",
        actual_session_id,
    )

    session = store.get_or_create(actual_session_id)
    total_elapsed = time.monotonic() - request_start
    logger.info(
        "[EnrichService:web_client_done] session=%s | total_latency=%.2fs | "
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
