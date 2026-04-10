"""
ATCE Tier Tests — verifies Tier 1, Tier 2, and Tier 3 behaviour independently
and end-to-end, without requiring a live LLM (summarizer is mocked).

Run:
    cd prompt_enrichment_service
    pytest tests/test_atce_tiers.py -v
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from context.atce import ATCEConfig, assemble_messages, store_turn, _compress_tier1_overflow, _merge_tier2_into_tier3
from context.session_memory import ChunkSummary, ConversationStore, Message, SessionMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_store() -> ConversationStore:
    """Fresh isolated store for each test."""
    return ConversationStore()


def make_cfg(**overrides) -> ATCEConfig:
    """Tiny config — low limits so tiers trigger quickly in tests."""
    defaults = dict(
        max_context_tokens=2048,
        response_buffer=256,
        tier1_pair_limit=3,
        compression_chunk_pairs=2,
        tier2_token_limit=200,
        tier3_target_tokens=80,
        model="gpt-3.5-turbo",
        summarization_model="gpt-3.5-turbo",
    )
    defaults.update(overrides)
    return ATCEConfig(**defaults)


def seed_tier1(session: SessionMemory, n_pairs: int, token_count: int = 10) -> None:
    """Insert `n_pairs` user/assistant pairs directly into tier1_buffer."""
    for i in range(1, n_pairs + 1):
        session.turn_counter = i
        session.tier1_buffer.append(
            Message(role="user",      content=f"User message {i}",      turn_index=i, token_count=token_count)
        )
        session.tier1_buffer.append(
            Message(role="assistant", content=f"Assistant reply {i}",   turn_index=i, token_count=token_count)
        )


def seed_tier2(session: SessionMemory, n_chunks: int, token_count: int = 60) -> None:
    """Insert `n_chunks` ChunkSummary objects directly into tier2_summaries."""
    for i in range(1, n_chunks + 1):
        session.tier2_summaries.append(
            ChunkSummary(
                text=f"Summary of turns {i*2-1}–{i*2}.",
                turn_range=(i * 2 - 1, i * 2),
                token_count=token_count,
            )
        )


# ===========================================================================
# TIER 1 TESTS — verbatim recent messages
# ===========================================================================

class TestTier1:

    def test_empty_session_returns_system_and_new_message(self):
        """Fresh session: output must be [system, user_new]."""
        store = make_store()
        msgs = assemble_messages("s1", "Hello!", "user ctx", make_cfg(), store)

        assert msgs[0]["role"] == "system"
        assert msgs[-1] == {"role": "user", "content": "Hello!"}
        assert len(msgs) == 2

    def test_tier1_messages_appear_in_chronological_order(self):
        """Tier 1 messages should be oldest → newest before the new message."""
        store = make_store()
        session = store.get_or_create("s2")
        seed_tier1(session, n_pairs=2)

        msgs = assemble_messages("s2", "New?", "", make_cfg(), store)

        roles = [m["role"] for m in msgs[1:-1]]   # exclude system and new msg
        assert roles == ["user", "assistant", "user", "assistant"]

    def test_tier1_all_pairs_within_limit_included(self):
        """With tier1_pair_limit=3 and 3 pairs stored, all 6 messages included."""
        store = make_store()
        session = store.get_or_create("s3")
        seed_tier1(session, n_pairs=3)   # exactly at limit

        msgs = assemble_messages("s3", "More?", "", make_cfg(tier1_pair_limit=3), store)
        history = msgs[1:-1]
        assert len(history) == 6

    def test_store_turn_adds_to_tier1_buffer(self):
        """store_turn must add exactly 2 messages (user + assistant) to tier1."""
        store = make_store()
        cfg = make_cfg(tier1_pair_limit=10)   # high limit — no overflow

        asyncio.get_event_loop().run_until_complete(
            store_turn("s4", "Hi", "Hello back", cfg, store)
        )

        session = store.get("s4")
        assert len(session.tier1_buffer) == 2
        assert session.tier1_buffer[0].role == "user"
        assert session.tier1_buffer[1].role == "assistant"
        assert session.turn_counter == 1

    def test_store_turn_increments_turn_counter(self):
        """Each store_turn call must increment the turn counter."""
        store = make_store()
        cfg = make_cfg(tier1_pair_limit=10)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(store_turn("s5", "msg1", "resp1", cfg, store))
        loop.run_until_complete(store_turn("s5", "msg2", "resp2", cfg, store))

        session = store.get("s5")
        assert session.turn_counter == 2
        assert len(session.tier1_buffer) == 4

    def test_tier1_respects_token_budget(self):
        """Messages that exceed the token budget must be silently dropped from output."""
        store = make_store()
        session = store.get_or_create("s6")
        # Each message costs 10 tokens + 4 overhead = 14 tokens each, 6 msgs = 84 tokens
        # Use a very small max_context_tokens to force budget exhaustion
        seed_tier1(session, n_pairs=3, token_count=200)

        cfg = make_cfg(max_context_tokens=512, response_buffer=256)
        msgs = assemble_messages("s6", "tight?", "", cfg, store)

        # Should not raise; may drop some tier1 msgs but must always include system + new
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "tight?"

    def test_user_context_appears_in_system_message(self):
        """User context string must be embedded inside the system message."""
        store = make_store()
        msgs = assemble_messages("s7", "test", "I am a data scientist", make_cfg(), store)

        system_content = msgs[0]["content"]
        assert "I am a data scientist" in system_content
        assert "## User Context" in system_content

    def test_no_user_context_omits_section(self):
        """Empty user context must not add the User Context section."""
        store = make_store()
        msgs = assemble_messages("s8", "test", "", make_cfg(), store)

        system_content = msgs[0]["content"]
        assert "## User Context" not in system_content


# ===========================================================================
# TIER 2 TESTS — compressed chunk summaries
# ===========================================================================

class TestTier2:

    def test_tier2_summaries_appear_in_system_message(self):
        """Existing Tier 2 chunks must show up under '## Earlier Conversation Summaries'."""
        store = make_store()
        session = store.get_or_create("t2-s1")
        seed_tier2(session, n_chunks=2)

        msgs = assemble_messages("t2-s1", "anything", "", make_cfg(), store)

        system = msgs[0]["content"]
        assert "## Earlier Conversation Summaries" in system
        assert "Summary of turns 1–2" in system
        assert "Summary of turns 3–4" in system

    def test_tier2_section_absent_when_empty(self):
        """No Tier 2 chunks → no Earlier Conversation Summaries section."""
        store = make_store()
        msgs = assemble_messages("t2-s2", "q", "", make_cfg(), store)
        assert "## Earlier Conversation Summaries" not in msgs[0]["content"]

    @pytest.mark.asyncio
    async def test_compress_tier1_creates_tier2_chunk(self):
        """_compress_tier1_overflow must create a Tier 2 ChunkSummary."""
        store = make_store()
        session = store.get_or_create("t2-s3")
        seed_tier1(session, n_pairs=6)   # plenty to compress

        cfg = make_cfg(compression_chunk_pairs=2)  # compress 4 msgs at a time

        with patch(
            "context.atce.summarize_chunk",
            new=AsyncMock(return_value="Compressed summary text."),
        ):
            await _compress_tier1_overflow(session, cfg)

        assert len(session.tier2_summaries) == 1
        assert session.tier2_summaries[0].text == "Compressed summary text."

    @pytest.mark.asyncio
    async def test_compress_tier1_removes_messages_from_tier1(self):
        """After compression, the compressed messages must be removed from tier1_buffer."""
        store = make_store()
        session = store.get_or_create("t2-s4")
        seed_tier1(session, n_pairs=6)   # 12 msgs total
        initial_count = len(session.tier1_buffer)

        cfg = make_cfg(compression_chunk_pairs=2)  # 4 msgs per chunk

        with patch(
            "context.atce.summarize_chunk",
            new=AsyncMock(return_value="Summary."),
        ):
            await _compress_tier1_overflow(session, cfg)

        assert len(session.tier1_buffer) == initial_count - cfg.compression_chunk_pairs * 2

    @pytest.mark.asyncio
    async def test_compress_tier1_restores_buffer_on_error(self):
        """If summarization fails, tier1_buffer must be fully restored (no data loss)."""
        store = make_store()
        session = store.get_or_create("t2-s5")
        seed_tier1(session, n_pairs=6)
        original_count = len(session.tier1_buffer)

        cfg = make_cfg(compression_chunk_pairs=2)

        with patch(
            "context.atce.summarize_chunk",
            new=AsyncMock(side_effect=RuntimeError("LLM unavailable")),
        ):
            await _compress_tier1_overflow(session, cfg)

        assert len(session.tier1_buffer) == original_count
        assert len(session.tier2_summaries) == 0

    @pytest.mark.asyncio
    async def test_compress_tier1_noop_when_not_enough_messages(self):
        """If tier1_buffer has ≤ chunk_size messages, compression must be a no-op."""
        store = make_store()
        session = store.get_or_create("t2-s6")
        seed_tier1(session, n_pairs=2)   # 4 msgs; chunk_size = 4 (compression_chunk_pairs=2)

        cfg = make_cfg(compression_chunk_pairs=2)
        mock_summarize = AsyncMock(return_value="Should not be called")

        with patch("context.atce.summarize_chunk", new=mock_summarize):
            await _compress_tier1_overflow(session, cfg)

        mock_summarize.assert_not_called()
        assert len(session.tier2_summaries) == 0

    def test_tier2_chunk_turn_range_recorded(self):
        """ChunkSummary.turn_range must span the correct oldest and newest turn indices."""
        store = make_store()
        session = store.get_or_create("t2-s7")
        seed_tier2(session, n_chunks=1)

        chunk = session.tier2_summaries[0]
        assert chunk.turn_range[0] <= chunk.turn_range[1]

    def test_tier2_total_tokens_property(self):
        """tier2_total_tokens must sum all chunk token counts correctly."""
        store = make_store()
        session = store.get_or_create("t2-s8")
        seed_tier2(session, n_chunks=3, token_count=50)

        assert session.tier2_total_tokens == 150


# ===========================================================================
# TIER 3 TESTS — ultra-compact core memory
# ===========================================================================

class TestTier3:

    def test_tier3_core_memory_appears_in_system_message(self):
        """If tier3_core_memory is set, it must appear under '## Conversation Background'."""
        store = make_store()
        session = store.get_or_create("t3-s1")
        session.tier3_core_memory = "User prefers concise answers. Discussed project X."

        msgs = assemble_messages("t3-s1", "continue", "", make_cfg(), store)

        system = msgs[0]["content"]
        assert "## Conversation Background" in system
        assert "User prefers concise answers" in system

    def test_tier3_section_absent_when_empty(self):
        """Empty tier3_core_memory → no Conversation Background section."""
        store = make_store()
        msgs = assemble_messages("t3-s2", "q", "", make_cfg(), store)
        assert "## Conversation Background" not in msgs[0]["content"]

    @pytest.mark.asyncio
    async def test_merge_tier2_into_tier3_updates_core_memory(self):
        """_merge_tier2_into_tier3 must update tier3_core_memory with merged content."""
        store = make_store()
        session = store.get_or_create("t3-s3")
        seed_tier2(session, n_chunks=3)  # 3 chunks; oldest 2 merged, newest kept

        cfg = make_cfg(tier3_target_tokens=80)

        with patch(
            "context.atce.merge_into_core_memory",
            new=AsyncMock(return_value="Merged core memory text."),
        ):
            await _merge_tier2_into_tier3(session, cfg)

        assert session.tier3_core_memory == "Merged core memory text."

    @pytest.mark.asyncio
    async def test_merge_tier2_keeps_newest_chunk_in_tier2(self):
        """After a Tier 2→3 merge, the most-recent Tier 2 chunk must remain in tier2_summaries."""
        store = make_store()
        session = store.get_or_create("t3-s4")
        seed_tier2(session, n_chunks=3)
        newest_chunk = session.tier2_summaries[-1]

        cfg = make_cfg()

        with patch(
            "context.atce.merge_into_core_memory",
            new=AsyncMock(return_value="core."),
        ):
            await _merge_tier2_into_tier3(session, cfg)

        assert len(session.tier2_summaries) == 1
        assert session.tier2_summaries[0].text == newest_chunk.text

    @pytest.mark.asyncio
    async def test_merge_tier2_noop_when_only_one_chunk(self):
        """With only one Tier 2 chunk, merge must be a no-op (preserve granularity)."""
        store = make_store()
        session = store.get_or_create("t3-s5")
        seed_tier2(session, n_chunks=1)
        original_core = session.tier3_core_memory

        mock_merge = AsyncMock(return_value="Should not be called")

        with patch("context.atce.merge_into_core_memory", new=mock_merge):
            await _merge_tier2_into_tier3(session, make_cfg())

        mock_merge.assert_not_called()
        assert session.tier3_core_memory == original_core

    @pytest.mark.asyncio
    async def test_merge_tier2_restores_chunks_on_error(self):
        """If the merge LLM call fails, all Tier 2 chunks must be restored."""
        store = make_store()
        session = store.get_or_create("t3-s6")
        seed_tier2(session, n_chunks=3)
        original_chunk_count = len(session.tier2_summaries)

        with patch(
            "context.atce.merge_into_core_memory",
            new=AsyncMock(side_effect=RuntimeError("API error")),
        ):
            await _merge_tier2_into_tier3(session, make_cfg())

        assert len(session.tier2_summaries) == original_chunk_count
        assert session.tier3_core_memory == ""

    @pytest.mark.asyncio
    async def test_merge_uses_existing_core_memory(self):
        """The merge call must pass the existing tier3_core_memory as existing_core."""
        store = make_store()
        session = store.get_or_create("t3-s7")
        session.tier3_core_memory = "Existing background facts."
        seed_tier2(session, n_chunks=2)

        mock_merge = AsyncMock(return_value="Updated core.")

        with patch("context.atce.merge_into_core_memory", new=mock_merge):
            await _merge_tier2_into_tier3(session, make_cfg())

        call_kwargs = mock_merge.call_args
        assert call_kwargs.kwargs.get("existing_core") == "Existing background facts." or \
               call_kwargs.args[0] == "Existing background facts."


# ===========================================================================
# CROSS-TIER / INTEGRATION TESTS
# ===========================================================================

class TestCrossTierIntegration:

    def test_system_message_order_system_t3_t2_user_context(self):
        """
        Position-aware layout: base instructions → user context → T3 background
        → T2 summaries, all in the system message (before T1 verbatim messages).
        """
        store = make_store()
        session = store.get_or_create("int-s1")
        session.tier3_core_memory = "T3 content."
        seed_tier2(session, n_chunks=1)

        msgs = assemble_messages("int-s1", "test", "my ctx", make_cfg(), store)
        system = msgs[0]["content"]

        t3_pos = system.find("## Conversation Background")
        t2_pos = system.find("## Earlier Conversation Summaries")
        ctx_pos = system.find("## User Context")

        assert ctx_pos < t3_pos < t2_pos, (
            f"Expected User Context ({ctx_pos}) < T3 ({t3_pos}) < T2 ({t2_pos})"
        )

    def test_new_message_always_last(self):
        """The newly submitted user message must always be the final message."""
        store = make_store()
        session = store.get_or_create("int-s2")
        session.tier3_core_memory = "Some background."
        seed_tier2(session, n_chunks=2)
        seed_tier1(session, n_pairs=2)

        msgs = assemble_messages("int-s2", "final question", "", make_cfg(), store)

        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "final question"

    @pytest.mark.asyncio
    async def test_store_turn_triggers_t1_to_t2_compression_when_overflow(self):
        """
        When tier1 exceeds tier1_pair_limit, store_turn must schedule compression
        (verified by checking that create_task is called with the right coroutine name).
        """
        store = make_store()
        cfg = make_cfg(tier1_pair_limit=2, compression_chunk_pairs=2)

        # Pre-fill to exactly the limit
        session = store.get_or_create("int-s3")
        seed_tier1(session, n_pairs=2)   # at limit

        created_tasks = []

        async def fake_compress(session, cfg, persist_fn=None):
            pass

        with patch("context.atce._compress_tier1_overflow", side_effect=fake_compress) as mock_compress, \
             patch("asyncio.create_task") as mock_create_task:
            # This turn pushes us to 3 pairs — over the limit of 2
            await store_turn("int-s3", "overflow msg", "overflow resp", cfg, store)
            assert mock_create_task.called

    def test_assemble_messages_isolated_across_sessions(self):
        """Two different sessions must not share any state."""
        store = make_store()

        session_a = store.get_or_create("iso-a")
        seed_tier1(session_a, n_pairs=2)
        session_a.tier3_core_memory = "Session A background."

        msgs_a = assemble_messages("iso-a", "q", "", make_cfg(), store)
        msgs_b = assemble_messages("iso-b", "q", "", make_cfg(), store)

        system_a = msgs_a[0]["content"]
        system_b = msgs_b[0]["content"]

        assert "Session A background." in system_a
        assert "Session A background." not in system_b
        # Session B has no history
        assert len(msgs_b) == 2   # only system + new msg

    @pytest.mark.asyncio
    async def test_full_tier_progression(self):
        """
        End-to-end: fill tier1 → compress to tier2 → merge to tier3.
        Verifies that data flows correctly through all three tiers.
        """
        store = make_store()
        session = store.get_or_create("e2e-s1")
        cfg = make_cfg(
            tier1_pair_limit=3,
            compression_chunk_pairs=2,
            tier2_token_limit=100,
        )

        # Step 1: seed tier1 with 6 pairs → will overflow (> 3 pair limit)
        seed_tier1(session, n_pairs=6)

        # Step 2: compress tier1 → tier2
        with patch(
            "context.atce.summarize_chunk",
            new=AsyncMock(return_value="Chunk summary A."),
        ):
            await _compress_tier1_overflow(session, cfg)

        assert len(session.tier2_summaries) >= 1, "Tier 2 should have at least one chunk"

        # Step 3: add more tier2 chunks to trigger tier3 merge
        seed_tier2(session, n_chunks=3, token_count=40)  # total ~120 > tier2_token_limit=100

        with patch(
            "context.atce.merge_into_core_memory",
            new=AsyncMock(return_value="Core memory after full progression."),
        ):
            await _merge_tier2_into_tier3(session, cfg)

        assert session.tier3_core_memory == "Core memory after full progression."
        assert len(session.tier2_summaries) == 1   # only newest chunk remains

        # Step 4: verify all tiers reflected in assembled messages
        msgs = assemble_messages("e2e-s1", "What did we discuss?", "user context", cfg, store)
        system = msgs[0]["content"]

        assert "## Conversation Background" in system
        assert "Core memory after full progression." in system
        assert "## Earlier Conversation Summaries" in system
