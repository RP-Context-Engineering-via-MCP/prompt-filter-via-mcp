"""
Prompt Enrichment Service — FastAPI app (Dual-Mode).

This service is refactored into:
- core/
  - config.py
  - llm_client.py
- services/
  - external_clients.py
  - enrichment_service.py
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from core.config import ATCE_CFG, REDIS_URL, REDIS_SESSION_TTL
from core.llm_client import get_llm_client
from services.external_clients import external_clients
from services.enrichment_service import fetch_user_context, sync_mcp_turns, format_atce_history
from context import (
    RedisConversationStore,
    assemble_messages,
    conversation_store,
    store_turn,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Active conversation store
# ---------------------------------------------------------------------------
if REDIS_URL:
    active_store: RedisConversationStore | None = RedisConversationStore(
        redis_url=REDIS_URL,
        ttl=REDIS_SESSION_TTL,
    )
    logger.info(f"[Store] Using Redis store: {REDIS_URL} (TTL={REDIS_SESSION_TTL}s)")
else:
    active_store = None
    logger.warning(
        "[Store] REDIS_URL not set — using in-memory store. "
        "Sessions will be lost on restart. Set REDIS_URL to enable persistence."
    )

# ---------------------------------------------------------------------------
# FastAPI lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Prompt Enrichment Service...")
    await external_clients.init_session()
    yield
    # Shutdown
    logger.info("Shutting down Prompt Enrichment Service...")
    await external_clients.close_session()
    if active_store is not None:
        await active_store.close()
        logger.info("[Store] Redis connection closed on shutdown")

app = FastAPI(
    title="Prompt Enrichment Service",
    version="2.0.0",
    lifespan=lifespan
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class EnrichRequest(BaseModel):
    prompt: str
    user_id: str
    session_id: str | None = None
    source: str = "web_client"
    mcp_client: str | None = None

class EnrichResponse(BaseModel):
    enriched_prompt: str
    llm_response: str | None = None
    session_id: str
    turn_index: int

class StoreTurnRequest(BaseModel):
    session_id: str          # full session key e.g. "user_id::default"
    user_message: str
    llm_response: str
    user_id: str | None = None
    selected_session_id: str | None = None

class StoreTurnResponse(BaseModel):
    session_id: str
    turn_index: int

# ---------------------------------------------------------------------------
# Background task: store turn + persist to Redis
# ---------------------------------------------------------------------------
async def _store_and_persist(
    session_id: str,
    user_message: str,
    llm_response: str,
    user_id: str | None = None,
    selected_session_id: str | None = None,
) -> None:
    try:
        store = active_store or conversation_store
        await store_turn(
            session_id=session_id,
            user_message=user_message,
            assistant_response=llm_response,
            cfg=ATCE_CFG,
            store=store,
        )

        if active_store is not None:
            logger.debug(f"[_store_and_persist] Persisting session={session_id} to Redis...")
            await active_store.persist(session_id)
            logger.debug(f"[_store_and_persist] Done persisting session={session_id}")

        # Also log to ChatLog so Claude Desktop's sync_mcp_turns() can pick up web client turns
        if user_id:
            try:
                import aiohttp
                from core.config import CHAT_LOGGER_URL
                payload = {
                    "session_id": session_id,
                    "selected_session_id": selected_session_id,
                    "user_id": user_id,
                    "source": "web_client",
                    "user_prompt": user_message,
                    "llm_response": llm_response,
                }
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.post(
                        f"{CHAT_LOGGER_URL}/api/chats",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 201:
                            logger.info(f"[_store_and_persist] web_client turn logged to ChatLog | user={user_id}")
                        else:
                            logger.warning(f"[_store_and_persist] ChatLog returned status={resp.status}")
            except Exception as exc:
                logger.error(f"[_store_and_persist] Failed to log to ChatLog: {exc}")

    except Exception as exc:
        logger.error(f"[_store_and_persist] ERROR for session={session_id}: {exc}", exc_info=True)


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
    store = active_store or conversation_store
    if active_store is not None:
        await active_store.ensure_loaded(session_id)

    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.debug_summary()


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if active_store is not None:
        await active_store.delete_remote(session_id)
        return {"deleted": session_id, "store": "redis"}

    deleted = conversation_store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id, "store": "in-memory"}


@app.post("/store_turn", response_model=StoreTurnResponse)
async def store_mcp_turn(request: StoreTurnRequest, background_tasks: BackgroundTasks):
    """
    Called by the MCP capture_chat tool after the LLM responds.
    Stores the user/assistant turn directly into ATCE (Redis) so future
    process_prompt calls have history context.
    """
    logger.info(
        f"[StoreTurn] session={request.session_id} | user_id={request.user_id} | "
        f"prompt_len={len(request.user_message)} | response_len={len(request.llm_response)}"
    )

    store = active_store or conversation_store

    if active_store is not None:
        await active_store.ensure_loaded(request.session_id)

    background_tasks.add_task(
        _store_and_persist,
        session_id=request.session_id,
        user_message=request.user_message,
        llm_response=request.llm_response,
        user_id=None,  # capture_chat already logs to chat-logger via logChat
        selected_session_id=request.selected_session_id,
    )

    session = store.get_or_create(request.session_id)
    return StoreTurnResponse(
        session_id=request.session_id,
        turn_index=session.turn_counter + 1,
    )


@app.post("/enrich", response_model=EnrichResponse)
async def enrich_prompt(request: EnrichRequest, background_tasks: BackgroundTasks):
    request_start = time.monotonic()

    logger.info(
        f"[EnrichService] source={request.source} | user_id={request.user_id} | "
        f"session_id={request.session_id} | prompt_len={len(request.prompt)}"
    )

    current_session = request.session_id
    if not current_session:
        current_session = await external_clients.get_current_session_id(request.user_id)

    actual_session_id = f"{request.user_id}::{current_session}"
    store = active_store or conversation_store

    if active_store is not None:
        await active_store.ensure_loaded(actual_session_id)

    if request.source == "mcp":
        logger.info(f"[EnrichService:mcp] session={actual_session_id} | MCP mode")

        t0 = time.monotonic()
        synced_count = await sync_mcp_turns(
            session_id=actual_session_id,
            user_id=request.user_id,
            selected_session_id=current_session,
            store=store,
            cfg=ATCE_CFG,
        )
        logger.info(f"[EnrichService:mcp_sync] synced {synced_count} turns | lat={time.monotonic() - t0:.3f}s")

        t0 = time.monotonic()
        user_context, last_source = await fetch_user_context(request.prompt, request.user_id, current_session)
        logger.info(f"[EnrichService:mcp_context] fetched context | lat={time.monotonic() - t0:.3f}s")

        current_client = request.mcp_client or request.source
        send_context = False
        
        if not last_source:
            logger.info(f"[EnrichService:mcp] First message. Injecting context for {current_client}.")
            send_context = True
        elif current_client != last_source:
            logger.info(f"[EnrichService:mcp] Client switch: {last_source} -> {current_client}. Injecting context & history.")
            send_context = True
        else:
            logger.info(f"[EnrichService:mcp] Continuing with {current_client}. Skipping context injection.")

        enriched_prompt = ""
        if send_context:
            enriched_prompt += f"{user_context}\n\n"
            if last_source:
                session_mem = store.get(actual_session_id)
                atce_history_str = format_atce_history(session_mem)
                if atce_history_str:
                    enriched_prompt += f"{atce_history_str}\n"
                    
        enriched_prompt += f"User Prompt: {request.prompt}"

        logger.debug(f"\n[MCP ENRICHED PROMPT]\n{enriched_prompt}\n")

        session = store.get_or_create(actual_session_id)
        
        return EnrichResponse(
            enriched_prompt=enriched_prompt,
            llm_response=None,
            session_id=actual_session_id,
            turn_index=session.turn_counter + 1,
        )

    # Web Client Mode
    logger.info(f"[EnrichService:web_client] session={actual_session_id} | Web client mode")

    t0 = time.monotonic()
    user_context, _ = await fetch_user_context(request.prompt, request.user_id, current_session)
    logger.info(f"[EnrichService:web_client_context] fetched context | lat={time.monotonic() - t0:.3f}s")

    messages = assemble_messages(
        session_id=actual_session_id,
        new_message=request.prompt,
        user_context=user_context,
        cfg=ATCE_CFG,
        store=store,
    )

    enriched_prompt_debug = "\n\n".join([f"[{m.get('role', 'unknown').upper()}]\n{m.get('content', '')}" for m in messages])
    logger.debug(f"\n[WEB_CLIENT ENRICHED PROMPT]\n{enriched_prompt_debug}\n")

    t0 = time.monotonic()
    try:
        from core.config import AZURE_OPENAI_KEY
        if not AZURE_OPENAI_KEY or AZURE_OPENAI_KEY == "your_api_key_here":
            logger.warning("OpenAI API Key not set. Returning mock response.")
            session = store.get_or_create(actual_session_id)
            llm_response = f"[MOCK RESPONSE] Turn {session.turn_counter + 1} | context: {len(messages)} msgs"
        else:
            client = get_llm_client()
            completion = await client.chat.completions.create(
                model=ATCE_CFG.model,
                messages=messages,
                max_tokens=ATCE_CFG.response_buffer,
                temperature=0.7,
            )
            llm_response = completion.choices[0].message.content.strip()
            
            usage = completion.usage
            logger.info(
                f"[EnrichService:llm] lat={time.monotonic() - t0:.2f}s | "
                f"prompt={usage.prompt_tokens if usage else -1} | "
                f"comp={usage.completion_tokens if usage else -1}"
            )
    except Exception as exc:
        logger.error(f"[EnrichService:llm_error] {exc}")
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    background_tasks.add_task(
        _store_and_persist,
        session_id=actual_session_id,
        user_message=request.prompt,
        llm_response=llm_response,
        user_id=request.user_id,
        selected_session_id=current_session,
    )

    session = store.get_or_create(actual_session_id)
    
    return EnrichResponse(
        enriched_prompt=enriched_prompt_debug,
        llm_response=llm_response,
        session_id=actual_session_id,
        turn_index=session.turn_counter + 1,
    )
