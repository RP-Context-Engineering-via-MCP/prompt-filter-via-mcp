import logging
import aiohttp
from typing import Optional, Tuple

from core.config import (
    USER_MANAGER_URL,
    PREDEFINED_PROFILE_URL,
    CHAT_LOGGER_URL,
    BEHAVIOR_EXTRACTION_URL,
    CORE_BEHAVIOR_URL
)

logger = logging.getLogger(__name__)

class ExternalClients:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def init_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
            logger.info("Initialized aiohttp ClientSession")

    async def close_session(self):
        if self.session is not None:
            await self.session.close()
            self.session = None
            logger.info("Closed aiohttp ClientSession")

    async def get_current_session_id(self, user_id: str) -> str:
        """Fetch the current session ID for the given user from the User Manager."""
        if not self.session:
            raise RuntimeError("ClientSession is not initialized")
        try:
            url = f"{USER_MANAGER_URL}/api/users/{user_id}/current-session"
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("current_session_id") or "default"
                else:
                    logger.warning(f"[UserManager] Failed to get session for user {user_id}: {response.status}")
                    return "default"
        except Exception as exc:
            logger.error(f"[UserManager] Error fetching session for user {user_id}: {exc}")
            return "default"

    async def get_predefined_profile_id(self, user_id: str) -> str:
        """Fetch the predefined profile ID for the given user from the User Manager."""
        if not self.session:
            raise RuntimeError("ClientSession is not initialized")
        try:
            url = f"{USER_MANAGER_URL}/api/users/{user_id}/predefined-profile-id"
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("predefined_profile_id")
                else:
                    logger.warning(f"[UserManager] Failed to get predefined profile id for user {user_id}: {response.status}")
        except Exception as exc:
            logger.error(f"[UserManager] Error fetching predefined profile id for user {user_id}: {exc}")
        return ""

    async def get_predefined_profile(self, profile_id: str) -> str:
        """Fetch the predefined profile details given a profile ID."""
        if not profile_id:
            return "No predefined profile available."
        if not self.session:
            raise RuntimeError("ClientSession is not initialized")
        try:
            url = f"{PREDEFINED_PROFILE_URL}/api/predefined-profiles/{profile_id}"
            async with self.session.get(url, timeout=5) as response:
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

    async def get_latest_chat_log(self, user_id: str, selected_session_id: str) -> Tuple[list, Optional[str]]:
        """Fetch the latest chat turn for behavior extraction, and the source of that log."""
        if not self.session:
            raise RuntimeError("ClientSession is not initialized")
        try:
            url = f"{CHAT_LOGGER_URL}/api/chats?user_id={user_id}&selected_session_id={selected_session_id}&limit=1&sort_desc=true"
            async with self.session.get(url, timeout=5) as response:
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

    async def get_behavior_extraction_data(self, prompt: str, user_id: str, session_id: str, recent_history: list) -> str:
        """Post to Behavior Extraction service and return the extracted string."""
        if not self.session:
            raise RuntimeError("ClientSession is not initialized")
        try:
            url = f"{BEHAVIOR_EXTRACTION_URL}/v2/extract"
            payload = {
                "prompt": prompt,
                "user_id": user_id,
                "session_id": session_id,
                "recent_history": recent_history
            }
            async with self.session.post(url, json=payload, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("extracted_behavior") or data.get("behavior") or str(data)
                else:
                    logger.warning(f"[BehaviorService] Failed extraction: {response.status}")
        except Exception as exc:
            logger.error(f"[BehaviorService] Error positing to extraction: {exc}")
        return "No behavior extracted."

    async def get_user_core_behavior_extraction(self, user_id: str) -> str:
        """Fetch the core behavior (identity anchor prompt) for the user."""
        if not user_id:
            return "No Core Behavious found"
        if not self.session:
            raise RuntimeError("ClientSession is not initialized")
        try:
            url = f"{CORE_BEHAVIOR_URL}/{user_id}"
            logger.debug(f"[CoreBehavior] Fetching context for user: {user_id} from {url}")
            async with self.session.post(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    anchor_prompt = data.get("identity_anchor_prompt")
                    if anchor_prompt:
                        return anchor_prompt
                    else:
                        logger.warning(f"[CoreBehavior] No identity_anchor_prompt in response for user {user_id}")
                else:
                    logger.warning(f"[CoreBehavior] Failed to fetch core behavior for {user_id}: {response.status}")
        except Exception as exc:
            logger.error(f"[CoreBehavior] Error fetching core behavior for user {user_id}: {exc}")
        return "No Core Behavious found"

# Singleton instance
external_clients = ExternalClients()
