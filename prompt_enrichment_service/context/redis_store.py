"""
ATCE Redis Store — durable, Redis-backed conversation store.

Architecture: Write-through L1 cache + Redis backend
  ┌─────────────────────────────────────────────────────┐
  │  Request arrives                                    │
  │    └─ ensure_loaded(session_id)                     │
  │         ├─ L1 cache hit  → return immediately       │
  │         └─ L1 cache miss → load from Redis          │
  │              ├─ Redis hit  → deserialize + cache    │
  │              └─ Redis miss → create empty session   │
  │                                                     │
  │  assemble_messages()  → reads L1 cache (sync, fast) │
  │                                                     │
  │  After LLM response:                               │
  │    └─ store_turn()  → writes L1 cache               │
  │    └─ persist()     → serializes L1 → Redis         │
  │                                                     │
  │  After each compression (Tier1→2, Tier2→3):        │
  │    └─ persist()     → keeps Redis in sync           │
  └─────────────────────────────────────────────────────┘

Session TTL defaults to 24 h; configurable via REDIS_SESSION_TTL env var.
"""

import json
import logging
import threading
from datetime import datetime
from typing import Callable, Coroutine, Optional

import redis.asyncio as aioredis

from .session_memory import ChunkSummary, Message, SessionMemory

logger = logging.getLogger(__name__)

_KEY_PREFIX = "atce:session:"
DEFAULT_TTL  = 432_000   # 5 days


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize(session: SessionMemory) -> str:
    """Convert a SessionMemory to a compact JSON string for Redis storage."""
    return json.dumps(
        {
            "session_id":       session.session_id,
            "turn_counter":     session.turn_counter,
            "tier3_core_memory": session.tier3_core_memory,
            "facts":            session.facts,
            "tier1_buffer": [
                {
                    "role":        m.role,
                    "content":     m.content,
                    "turn_index":  m.turn_index,
                    "token_count": m.token_count,
                    "timestamp":   m.timestamp.isoformat(),
                }
                for m in session.tier1_buffer
            ],
            "tier2_summaries": [
                {
                    "text":        c.text,
                    "turn_range":  list(c.turn_range),
                    "token_count": c.token_count,
                    "created_at":  c.created_at.isoformat(),
                }
                for c in session.tier2_summaries
            ],
        },
        ensure_ascii=False,
    )


def _deserialize(raw: str) -> SessionMemory:
    """Reconstruct a SessionMemory from a JSON string loaded from Redis."""
    d = json.loads(raw)

    tier1 = [
        Message(
            role=m["role"],
            content=m["content"],
            turn_index=m["turn_index"],
            token_count=m["token_count"],
            timestamp=datetime.fromisoformat(m["timestamp"]),
        )
        for m in d.get("tier1_buffer", [])
    ]

    tier2 = [
        ChunkSummary(
            text=c["text"],
            turn_range=tuple(c["turn_range"]),
            token_count=c["token_count"],
            created_at=datetime.fromisoformat(c["created_at"]),
        )
        for c in d.get("tier2_summaries", [])
    ]

    return SessionMemory(
        session_id=d["session_id"],
        tier1_buffer=tier1,
        tier2_summaries=tier2,
        tier3_core_memory=d.get("tier3_core_memory", ""),
        facts=d.get("facts", {}),
        turn_counter=d.get("turn_counter", 0),
    )


# ---------------------------------------------------------------------------
# Redis store
# ---------------------------------------------------------------------------

class RedisConversationStore:
    """
    Redis-backed conversation store with an in-process L1 cache.

    The L1 cache means assemble_messages() (sync) never touches Redis on
    each request — it reads from memory.  Redis is written to:
      • After every turn (via persist())
      • After every tier compression (via the persist_fn callback in atce.py)

    On server restart the session is rehydrated from Redis on the first
    ensure_loaded() call for that session_id.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl: int = DEFAULT_TTL,
    ) -> None:
        self._redis_url = redis_url
        self._ttl       = ttl
        self._client: aioredis.Redis | None = None
        self._local: dict[str, SessionMemory] = {}
        self._lock = threading.Lock()

    # ── Redis client (lazy-initialised) ─────────────────────────────────────

    def _redis(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=5,
            )
        return self._client

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    # ── Sync interface (L1 cache only — used by assemble_messages) ──────────

    def get_or_create(self, session_id: str) -> SessionMemory:
        """Synchronous read from L1 cache. Creates empty session if absent."""
        with self._lock:
            if session_id not in self._local:
                self._local[session_id] = SessionMemory(session_id=session_id)
            return self._local[session_id]

    def get(self, session_id: str) -> Optional[SessionMemory]:
        with self._lock:
            return self._local.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Remove from L1 cache (async Redis delete is handled by delete_remote)."""
        with self._lock:
            return self._local.pop(session_id, None) is not None

    def session_count(self) -> int:
        with self._lock:
            return len(self._local)

    def all_session_ids(self) -> list[str]:
        with self._lock:
            return list(self._local.keys())

    # ── Async interface ──────────────────────────────────────────────────────

    async def ensure_loaded(self, session_id: str) -> SessionMemory:
        """
        Guarantee the session is in the L1 cache before a request is processed.

        Call this once per request at the top of the handler:
            session = await redis_store.ensure_loaded(session_id)

        After this call, assemble_messages() (sync) is safe to use.
        """
        with self._lock:
            if session_id in self._local:
                return self._local[session_id]

        # Cache miss — attempt Redis load (outside lock to avoid blocking)
        session = await self._load_from_redis(session_id)

        with self._lock:
            # Double-checked lock: another coroutine may have created it
            if session_id not in self._local:
                self._local[session_id] = session
            return self._local[session_id]

    async def _load_from_redis(self, session_id: str) -> SessionMemory:
        try:
            raw = await self._redis().get(self._key(session_id))
            if raw:
                session = _deserialize(raw)
                logger.info(
                    "[RedisStore:load] session=%s restored from Redis | "
                    "turn=%d | tier1=%d msgs | tier2=%d chunks | tier3=%s",
                    session_id,
                    session.turn_counter,
                    len(session.tier1_buffer),
                    len(session.tier2_summaries),
                    "present" if session.tier3_core_memory else "empty",
                )
                return session

            logger.info(
                "[RedisStore:new] session=%s not found in Redis — starting fresh",
                session_id,
            )
        except Exception as exc:
            logger.error(
                "[RedisStore:load_error] session=%s | Redis error: %s — "
                "starting with empty session",
                session_id, exc,
            )

        return SessionMemory(session_id=session_id)

    async def persist(self, session_id: str) -> None:
        """
        Serialise the current L1 session state and write it to Redis.

        Call after store_turn() and after each compression step to keep
        Redis in sync with in-memory state.
        """
        with self._lock:
            session = self._local.get(session_id)

        if session is None:
            logger.warning(
                "[RedisStore:persist] session=%s not in L1 cache — skipping",
                session_id,
            )
            return

        try:
            raw = _serialize(session)
            await self._redis().setex(self._key(session_id), self._ttl, raw)
            logger.debug(
                "[RedisStore:persist] session=%s saved | turn=%d | "
                "tier1=%d msgs | tier2=%d chunks | tier3=%s | TTL=%ds | bytes=%d",
                session_id,
                session.turn_counter,
                len(session.tier1_buffer),
                len(session.tier2_summaries),
                "present" if session.tier3_core_memory else "empty",
                self._ttl,
                len(raw),
            )
        except Exception as exc:
            logger.error(
                "[RedisStore:persist_error] session=%s | %s",
                session_id, exc,
            )

    def make_persist_fn(self, session_id: str) -> Callable[[], Coroutine]:
        """
        Return a zero-argument coroutine function that persists session_id.
        Pass this into ATCE compression callbacks so tier transitions are
        written to Redis as soon as they complete.

        Usage in atce.py:
            persist_fn = store.make_persist_fn(session_id)   # if store supports it
            asyncio.create_task(_compress_tier1_overflow(session, cfg, persist_fn))
        """
        async def _persist():
            await self.persist(session_id)
        return _persist

    async def delete_remote(self, session_id: str) -> None:
        """Remove from both L1 cache and Redis."""
        self.delete(session_id)
        try:
            await self._redis().delete(self._key(session_id))
            logger.info("[RedisStore:delete] session=%s removed from Redis", session_id)
        except Exception as exc:
            logger.error("[RedisStore:delete_error] session=%s | %s", session_id, exc)

    async def ping(self) -> bool:
        """Return True if Redis is reachable — used in /health check."""
        try:
            return bool(await self._redis().ping())
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("[RedisStore] connection closed")
