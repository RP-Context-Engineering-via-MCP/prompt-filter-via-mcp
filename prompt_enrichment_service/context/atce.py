"""
ATCE — Adaptive Tiered Context Enrichment (core algorithm)

Two public entry points:

  assemble_messages(session_id, new_message, user_context, cfg?)
      → list[dict]   (OpenAI-format messages ready to send to the LLM)

  store_turn(session_id, user_message, assistant_response, cfg?)
      → None         (stores turn; fires async compression if tiers overflow)

Context layout produced (position-aware, informed by Liu et al. 2023):

  ┌──────────────────────────────────────┐  ← START (high LLM recall)
  │  SYSTEM message                      │
  │    • base system instructions        │
  │    • user enrichment context         │  (attention sink — always first)
  │    • Tier 3 core memory (if any)     │  (ultra-compact long-range summary)
  │    • Tier 2 chunk summaries (if any) │  (medium-range, middle zone)
  ├──────────────────────────────────────┤
  │  Tier 1 messages (verbatim)          │  (recent history)
  │    oldest → newest of those that fit │
  ├──────────────────────────────────────┤
  │  New user message                    │  ← END (high LLM recall)
  └──────────────────────────────────────┘
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Optional

from .session_memory import ChunkSummary, ConversationStore, Message, SessionMemory, conversation_store
from .summarizer import merge_into_core_memory, summarize_chunk
from .token_utils import count_tokens

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ATCEConfig:
    """Tunable parameters for the ATCE algorithm."""

    # Total token budget for one LLM call (input + output)
    max_context_tokens: int = 8192

    # Tokens reserved for the LLM's output (not consumed by input)
    response_buffer: int = 1024

    # Maximum number of user/assistant PAIRS kept verbatim in Tier 1
    # (3 pairs = 6 individual messages)
    tier1_pair_limit: int = 3

    # When Tier 1 overflows, compress this many pairs at once into one Tier 2 chunk
    compression_chunk_pairs: int = 4   # → 8 individual messages per chunk

    # Maximum total tokens across all Tier 2 chunk summaries before Tier 3 merge
    tier2_token_limit: int = 1000

    # Target token count for the Tier 3 core memory after a merge
    tier3_target_tokens: int = 150

    # OpenAI model used for inference (affects token counting)
    model: str = "gpt-3.5-turbo"

    # OpenAI model used for summarization (can be smaller/cheaper)
    summarization_model: str = "gpt-3.5-turbo"


# Default config — can be overridden at app startup
default_config = ATCEConfig()

_BASE_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable assistant. "
    "Use the provided user context and conversation history to give "
    "accurate, personalized, and coherent responses."
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_system_content(session: SessionMemory, user_context: str) -> str:
    """
    Compose the system message content following the position-aware layout:
      1. Base instructions  (attention sink)
      2. User context       (always present, fixed overhead)
      3. Tier 3 core memory (long-range background)
      4. Tier 2 summaries   (medium-range, placed in middle)
    """
    parts: list[str] = [_BASE_SYSTEM_PROMPT]

    if user_context:
        parts.append(f"\n## User Context\n{user_context.strip()}")

    if session.tier3_core_memory:
        parts.append(
            f"\n## Conversation Background\n"
            f"{session.tier3_core_memory.strip()}"
        )

    if session.tier2_summaries:
        summaries_text = "\n".join(
            f"[Turns {s.turn_range[0]}–{s.turn_range[1]}]: {s.text}"
            for s in session.tier2_summaries
        )
        parts.append(f"\n## Earlier Conversation Summaries\n{summaries_text}")

    return "\n".join(parts)


def _compute_history_budget(
    system_content: str,
    new_message: str,
    cfg: ATCEConfig,
    session_id: str = "",
) -> int:
    """
    How many tokens are available for Tier 1 verbatim messages after
    all fixed overhead is accounted for.
    """
    system_tokens  = count_tokens(system_content, cfg.model) + 4   # per-message overhead
    message_tokens = count_tokens(new_message, cfg.model)    + 4
    reply_priming  = 2

    used = system_tokens + message_tokens + reply_priming + cfg.response_buffer
    budget = max(0, cfg.max_context_tokens - used)

    logger.debug(
        "[ATCE:budget] session=%s | max=%d | system=%d | new_msg=%d | "
        "response_buffer=%d | available_for_history=%d",
        session_id, cfg.max_context_tokens,
        system_tokens, message_tokens,
        cfg.response_buffer, budget,
    )
    return budget


# ---------------------------------------------------------------------------
# Public: context assembly (called on every incoming request)
# ---------------------------------------------------------------------------

def assemble_messages(
    session_id: str,
    new_message: str,
    user_context: str,
    cfg: ATCEConfig | None = None,
    store: ConversationStore | None = None,
) -> list[dict]:
    """
    ATCE Phase 1 — Build the full messages list for the LLM.

    Returns an OpenAI-format list:
      [{"role": "system", "content": ...}, ..., {"role": "user", "content": new_message}]

    This function is synchronous and cheap (no I/O). It must not block.
    """
    cfg   = cfg   or default_config
    store = store or conversation_store

    session = store.get_or_create(session_id)

    logger.info(
        "[ATCE:assemble] session=%s turn=%d | tier1=%d msgs | tier2=%d chunks | tier3=%s",
        session_id,
        session.turn_counter + 1,
        len(session.tier1_buffer),
        len(session.tier2_summaries),
        "present" if session.tier3_core_memory else "empty",
    )

    # ── System message (fixed head) ────────────────────────────────────────
    system_content = _build_system_content(session, user_context)
    system_tokens  = count_tokens(system_content, cfg.model)
    messages: list[dict] = [{"role": "system", "content": system_content}]

    logger.debug(
        "[ATCE:system_msg] session=%s | system_tokens=%d (base=%d + user_ctx=%s + t3=%s + t2=%s)",
        session_id,
        system_tokens,
        count_tokens(_BASE_SYSTEM_PROMPT, cfg.model),
        "yes" if user_context else "no",
        "yes" if session.tier3_core_memory else "no",
        f"{len(session.tier2_summaries)} chunks" if session.tier2_summaries else "no",
    )

    # ── Tier 1: recent verbatim messages (high-fidelity tail) ──────────────
    # Walk newest → oldest, collect messages that fit the remaining budget.
    # Then reverse to restore chronological order before appending.
    history_budget = _compute_history_budget(system_content, new_message, cfg, session_id)

    selected: list[Message] = []
    dropped = 0
    for msg in reversed(session.tier1_buffer):
        cost = msg.token_count + 4   # +4 per-message overhead
        if history_budget >= cost:
            selected.append(msg)
            history_budget -= cost
        else:
            dropped += 1

    if dropped:
        logger.warning(
            "[ATCE:budget_exceeded] session=%s | %d Tier 1 messages could NOT fit "
            "(budget exhausted) — consider increasing max_context_tokens or tier1_pair_limit",
            session_id, dropped,
        )

    for msg in reversed(selected):   # restore chronological order
        messages.append({"role": msg.role, "content": msg.content})

    # ── New user message (tail — high recall zone) ─────────────────────────
    messages.append({"role": "user", "content": new_message})

    total_tokens = system_tokens + sum(
        count_tokens(m["content"], cfg.model) + 4 for m in messages[1:]
    ) + 2  # reply priming

    logger.info(
        "[ATCE:assemble_done] session=%s | final_msgs=%d (1 system + %d history + 1 new) | "
        "est_total_tokens=%d/%d | history_budget_remaining=%d",
        session_id,
        len(messages),
        len(selected),
        total_tokens,
        cfg.max_context_tokens,
        history_budget,
    )

    return messages


# ---------------------------------------------------------------------------
# Public: turn storage (called after every LLM response)
# ---------------------------------------------------------------------------

async def store_turn(
    session_id: str,
    user_message: str,
    assistant_response: str,
    cfg: ATCEConfig | None = None,
    store: ConversationStore | None = None,
) -> None:
    """
    ATCE Phase 2 — Persist a completed turn and trigger async compression
    if tiers overflow their capacity limits.

    This should be awaited AFTER returning the LLM response to the client
    (or fired as a background task so it does not add latency).
    """
    cfg   = cfg   or default_config
    store = store or conversation_store

    session = store.get_or_create(session_id)
    session.turn_counter += 1

    user_tokens = count_tokens(user_message, cfg.model)
    asst_tokens = count_tokens(assistant_response, cfg.model)

    # Store both messages in Tier 1
    for role, content, tok in [
        ("user",      user_message,      user_tokens),
        ("assistant", assistant_response, asst_tokens),
    ]:
        session.tier1_buffer.append(
            Message(
                role=role,
                content=content,
                turn_index=session.turn_counter,
                token_count=tok,
            )
        )

    logger.info(
        "[ATCE:store_turn] session=%s turn=%d | user=%d tokens | assistant=%d tokens | "
        "tier1=%d msgs (%d pairs) | limit=%d pairs",
        session_id,
        session.turn_counter,
        user_tokens,
        asst_tokens,
        len(session.tier1_buffer),
        session.tier1_pair_count,
        cfg.tier1_pair_limit,
    )

    # Build a persist callback if the store supports it (Redis store)
    persist_fn: Optional[Callable[[], Coroutine]] = getattr(store, "make_persist_fn", None)
    persist_fn = persist_fn(session_id) if persist_fn else None

    # Tier 1 overflow check — fire background compression without blocking
    if session.tier1_pair_count > cfg.tier1_pair_limit:
        logger.info(
            "[ATCE:overflow] session=%s | tier1 at %d pairs > limit %d — "
            "scheduling Tier 1→2 compression",
            session_id, session.tier1_pair_count, cfg.tier1_pair_limit,
        )
        asyncio.create_task(
            _compress_tier1_overflow(session, cfg, persist_fn=persist_fn),
            name=f"atce_compress_{session_id}_{session.turn_counter}",
        )


# ---------------------------------------------------------------------------
# Internal: tier compression (runs as background tasks)
# ---------------------------------------------------------------------------

async def _compress_tier1_overflow(
    session: SessionMemory,
    cfg: ATCEConfig,
    persist_fn: Optional[Callable[[], Coroutine]] = None,
) -> None:
    """
    Pop the oldest `compression_chunk_pairs` pairs from Tier 1,
    summarize them, and append the result as a new Tier 2 ChunkSummary.
    """
    chunk_size = cfg.compression_chunk_pairs * 2   # pairs → individual messages

    if len(session.tier1_buffer) <= chunk_size:
        return

    overflow: list[Message] = session.tier1_buffer[:chunk_size]
    session.tier1_buffer    = session.tier1_buffer[chunk_size:]

    input_tokens = sum(m.token_count for m in overflow)
    logger.info(
        "[ATCE:compress_t1] session=%s | compressing %d messages (turns %d–%d, ~%d tokens) → Tier 2",
        session.session_id,
        len(overflow),
        overflow[0].turn_index,
        overflow[-1].turn_index,
        input_tokens,
    )

    t0 = time.monotonic()
    try:
        summary_text = await summarize_chunk(
            overflow,
            target_tokens=300,
            model=cfg.summarization_model,
        )
        elapsed = time.monotonic() - t0

        chunk = ChunkSummary(
            text=summary_text,
            turn_range=(overflow[0].turn_index, overflow[-1].turn_index),
            token_count=count_tokens(summary_text, cfg.model),
        )
        session.tier2_summaries.append(chunk)

        logger.info(
            "[ATCE:compress_t1_done] session=%s | Tier 2 chunk created | "
            "input_tokens=%d → summary_tokens=%d (ratio=%.1fx) | "
            "latency=%.2fs | tier2_total=%d tokens (%d chunks)",
            session.session_id,
            input_tokens,
            chunk.token_count,
            input_tokens / max(chunk.token_count, 1),
            elapsed,
            session.tier2_total_tokens,
            len(session.tier2_summaries),
        )

        # Persist Tier 2 result to Redis before potentially merging further
        if persist_fn:
            await persist_fn()

        # Check Tier 2 overflow → trigger Tier 3 merge
        if session.tier2_total_tokens > cfg.tier2_token_limit:
            logger.info(
                "[ATCE:overflow] session=%s | tier2 at %d tokens > limit %d — "
                "scheduling Tier 2→3 merge",
                session.session_id, session.tier2_total_tokens, cfg.tier2_token_limit,
            )
            await _merge_tier2_into_tier3(session, cfg, persist_fn=persist_fn)

    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.error(
            "[ATCE:compress_t1_error] session=%s | Tier 1 compression FAILED after %.2fs: %s — "
            "restoring buffer to prevent data loss",
            session.session_id, elapsed, exc,
        )
        # Restore to avoid data loss on transient errors
        session.tier1_buffer = overflow + session.tier1_buffer


async def _merge_tier2_into_tier3(
    session: SessionMemory,
    cfg: ATCEConfig,
    persist_fn: Optional[Callable[[], Coroutine]] = None,
) -> None:
    """
    Merge all but the newest Tier 2 chunk into the Tier 3 core memory.
    The newest Tier 2 chunk is retained verbatim to preserve recent granularity.
    """
    if len(session.tier2_summaries) <= 1:
        return

    chunks_to_merge: list[ChunkSummary] = session.tier2_summaries[:-1]
    session.tier2_summaries              = session.tier2_summaries[-1:]

    input_tokens = (
        count_tokens(session.tier3_core_memory, cfg.model)
        + sum(c.token_count for c in chunks_to_merge)
    )
    logger.info(
        "[ATCE:merge_t2t3] session=%s | merging %d Tier 2 chunks (~%d tokens) into Tier 3",
        session.session_id,
        len(chunks_to_merge),
        input_tokens,
    )

    t0 = time.monotonic()
    try:
        session.tier3_core_memory = await merge_into_core_memory(
            existing_core=session.tier3_core_memory,
            chunks=[c.text for c in chunks_to_merge],
            target_tokens=cfg.tier3_target_tokens,
            model=cfg.summarization_model,
        )
        elapsed = time.monotonic() - t0
        output_tokens = count_tokens(session.tier3_core_memory, cfg.model)

        logger.info(
            "[ATCE:merge_t2t3_done] session=%s | Tier 3 updated | "
            "input_tokens=%d → core_tokens=%d (ratio=%.1fx) | "
            "latency=%.2fs | tier2_remaining=%d chunks",
            session.session_id,
            input_tokens,
            output_tokens,
            input_tokens / max(output_tokens, 1),
            elapsed,
            len(session.tier2_summaries),
        )

        # Persist the merged Tier 3 state to Redis
        if persist_fn:
            await persist_fn()

    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.error(
            "[ATCE:merge_t2t3_error] session=%s | Tier 3 merge FAILED after %.2fs: %s — "
            "restoring Tier 2 to prevent data loss",
            session.session_id, elapsed, exc,
        )
        # Restore Tier 2 chunks on failure to avoid data loss
        session.tier2_summaries = chunks_to_merge + session.tier2_summaries
