import logging
import asyncio
import time
from fastapi import HTTPException
from core.config import ATCE_CFG
from services.external_clients import external_clients
from context import store_turn, assemble_messages

logger = logging.getLogger(__name__)

async def fetch_user_context(prompt: str, user_id: str, session_id: str) -> str:
    """Fetches and formats user context from various services."""
    try:
        profile_id, (recent_history, last_source) = await asyncio.gather(
            external_clients.get_predefined_profile_id(user_id),
            external_clients.get_latest_chat_log(user_id, session_id),
        )

        profile_ctx, behavior_ctx, core_behavior_ctx = await asyncio.gather(
            external_clients.get_predefined_profile(profile_id),
            external_clients.get_behavior_extraction_data(prompt, user_id, session_id, recent_history),
            external_clients.get_user_core_behavior_extraction(user_id),
        )
        
        user_context = (
            f"Profile: {profile_ctx}\n"
            f"Behavior: {behavior_ctx}\n"
            f"Core behavior: {core_behavior_ctx}\n"
            "This is user behaviour context, when if generating the prompt if those behaviours are use full use them. Not Print this again. Provide user requested prompt answer."
        )
        return user_context, last_source

    except Exception as exc:
        logger.error(f"[UserContext] Error fetching context for {user_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Error fetching user context: {exc}")


async def sync_mcp_turns(session_id: str, user_id: str, selected_session_id: str, store, cfg) -> int:
    """
    Fetches unsynced chat logs from chat-logger-backend (MongoDB) and
    injects them into ATCE via store_turn().
    """
    from core.config import CHAT_LOGGER_URL
    import aiohttp
    
    synced = 0
    try:
        session = store.get_or_create(session_id)
        current_turn = session.turn_counter

        # Query by user_id only — no selected_session_id filter.
        # The browser extension may save with a different or null selected_session_id
        # (whatever is in chrome.storage.sync), so filtering by it would miss those logs.
        url = f"{CHAT_LOGGER_URL}/api/chats?user_id={user_id}&limit=100"

        logger.info(
            f"[sync_mcp_turns] session={session_id} | fetching unsynced turns | current_atce_turn={current_turn}"
        )

        async with aiohttp.ClientSession() as http_session:
             async with http_session.get(url, timeout=10) as response:
                 if response.status != 200:
                     logger.warning(f"[sync_mcp_turns] backend returned status={response.status}")
                     return 0
                 chat_logs = await response.json()

        last_synced_id = session.facts.get("last_synced_mongo_id")
        start_idx = 0

        if last_synced_id:
            for i, log in enumerate(chat_logs):
                if log.get("_id") == last_synced_id:
                    start_idx = i + 1
                    break
        elif session.turn_counter > 0:
            last_user_msg = next((m.content for m in reversed(session.tier1_buffer) if m.role == "user"), None)
            if last_user_msg:
                for i in range(len(chat_logs) - 1, -1, -1):
                     if chat_logs[i].get("user_prompt") == last_user_msg:
                         start_idx = i + 1
                         break
            else:
                 start_idx = len(chat_logs)

        unsynced_logs = chat_logs[start_idx:]
        
        if not unsynced_logs:
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

        if unsynced_logs:
            session.facts["last_synced_mongo_id"] = unsynced_logs[-1].get("_id", "")
            
        return synced

    except Exception as exc:
        logger.error(f"[sync_mcp_turns] Error parsing logs: {exc}", exc_info=True)
        return synced


def format_atce_history(session_mem) -> str:
    """Format previous conversation history from ATCE memory."""
    if not session_mem:
        return ""
        
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
    return "\n".join(history_lines)
