"""
ATCE Session Memory — data structures for the tiered context store.

Memory hierarchy per session:
  Tier 1  — Full-fidelity recent messages (verbatim)
  Tier 2  — Compressed chunk summaries of older messages
  Tier 3  — Ultra-compact running summary of all archived content
  facts   — Lightweight key-value store for extracted named facts
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Message:
    """A single conversation turn stored in Tier 1."""
    role: str           # "user" | "assistant"
    content: str
    turn_index: int     # global monotonic turn counter for the session
    token_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChunkSummary:
    """A compressed summary of a contiguous block of Tier 1 messages."""
    text: str
    turn_range: tuple[int, int]   # (first_turn_index, last_turn_index)
    token_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionMemory:
    """
    Complete in-memory state for a single chat session.

    Tier 1  — list[Message]         : recent verbatim messages
    Tier 2  — list[ChunkSummary]    : older compressed chunks (oldest → newest)
    Tier 3  — str                   : ultra-compact long-range core memory
    facts   — dict[str, str]        : extracted key facts (e.g. user preferences)
    """
    session_id: str
    tier1_buffer: list[Message] = field(default_factory=list)
    tier2_summaries: list[ChunkSummary] = field(default_factory=list)
    tier3_core_memory: str = ""
    facts: dict[str, str] = field(default_factory=dict)
    turn_counter: int = 0   # incremented once per user→assistant round-trip

    @property
    def tier1_pair_count(self) -> int:
        """Number of user/assistant pairs stored in Tier 1."""
        return len(self.tier1_buffer) // 2

    @property
    def tier2_total_tokens(self) -> int:
        return sum(s.token_count for s in self.tier2_summaries)

    def debug_summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "turn_counter": self.turn_counter,
            "tier1_messages": len(self.tier1_buffer),
            "tier2_chunks": len(self.tier2_summaries),
            "tier2_tokens": self.tier2_total_tokens,
            "tier3_tokens": len(self.tier3_core_memory.split()) if self.tier3_core_memory else 0,
            "facts_count": len(self.facts),
        }


class ConversationStore:
    """
    Thread-safe in-memory store for all active session memories.
    This is the MVP store; replace with Redis or DB for persistence.
    """

    def __init__(self):
        self._sessions: dict[str, SessionMemory] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> SessionMemory:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemory(session_id=session_id)
            return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionMemory]:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def all_session_ids(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)


# Module-level singleton — shared across the entire FastAPI process
conversation_store = ConversationStore()
