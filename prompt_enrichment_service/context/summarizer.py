"""
ATCE Summarizer — async LLM-based compression for Tier 1 → Tier 2 and Tier 2 → Tier 3.

Uses OpenAI chat completions with low temperature for consistent, factual summaries.
A smaller/cheaper model (e.g. gpt-3.5-turbo) is intentionally used for summarization
to keep cost low even when the inference model is gpt-4.
"""

import logging
import os
import time

from openai import AsyncAzureOpenAI

from .session_memory import Message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_CHUNK_SUMMARIZE_PROMPT = """\
You are compressing a conversation segment into a concise, factual summary.

PRESERVE:
- Specific facts, numbers, names, dates mentioned by either party
- User decisions, stated preferences, and explicit requirements
- Key conclusions and any action items or commitments made
- Domain-specific context (code snippets referenced, topics, tasks)

OMIT:
- Pleasantries, greetings, and filler ("sure", "great question", etc.)
- Verbose re-explanations of background knowledge
- Redundant clarifications that were resolved

Target length: ~{target_tokens} tokens. Write in dense, factual prose.

Conversation segment:
{conversation}
"""

_CORE_MEMORY_MERGE_PROMPT = """\
Merge the following conversation summaries into a single ultra-compact \
"core memory" of AT MOST {target_tokens} tokens.

RULES:
- Retain only facts that cannot be inferred from user profile or general knowledge
- Prioritize: major user decisions, long-running preferences, key domain facts, \
  named entities central to the conversation
- Write dense factual prose (not bullet lists)
- Discard anything recoverable from context or common sense

Existing core memory:
{existing_core}

New summaries to absorb:
{new_summaries}
"""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_client: AsyncAzureOpenAI | None = None


def _get_client() -> AsyncAzureOpenAI:
    global _client
    if _client is None:
        _client = AsyncAzureOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            api_version=os.environ.get("OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.environ.get("OPENAI_ENDPOINT")
        )
    return _client


def _format_messages(messages: list[Message]) -> str:
    lines = []
    for msg in messages:
        prefix = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def summarize_chunk(
    messages: list[Message],
    target_tokens: int = 300,
    model: str = "gpt-3.5-turbo",
) -> str:
    """
    Compress a list of Message objects (a Tier 1 overflow chunk)
    into a Tier 2 summary string.
    """
    conversation_text = _format_messages(messages)
    prompt = _CHUNK_SUMMARIZE_PROMPT.format(
        target_tokens=target_tokens,
        conversation=conversation_text,
    )

    prompt_len = len(prompt)
    logger.debug(
        "[Summarizer:chunk] calling model=%s | input_messages=%d | prompt_chars=%d | max_tokens=%d",
        model, len(messages), prompt_len, target_tokens + 80,
    )

    t0 = time.monotonic()
    client = _get_client()
    response = await client.chat.completions.create(
        model=model, # Azure treats the model parameter as the deployment name
        messages=[{"role": "user", "content": prompt}],
        max_tokens=target_tokens + 80,   # small headroom above target
        temperature=0.1,                 # low temp → consistent, factual output
    )
    elapsed = time.monotonic() - t0

    result = response.choices[0].message.content.strip()
    usage = response.usage
    logger.info(
        "[Summarizer:chunk_done] model=%s | latency=%.2fs | "
        "prompt_tokens=%d | completion_tokens=%d | total_tokens=%d | output_chars=%d",
        model,
        elapsed,
        usage.prompt_tokens if usage else -1,
        usage.completion_tokens if usage else -1,
        usage.total_tokens if usage else -1,
        len(result),
    )
    return result


async def merge_into_core_memory(
    existing_core: str,
    chunks: list[str],
    target_tokens: int = 150,
    model: str = "gpt-3.5-turbo",
) -> str:
    """
    Merge multiple Tier 2 chunk texts plus the existing Tier 3 core memory
    into a single updated core memory string of at most `target_tokens` tokens.
    """
    new_summaries_text = "\n\n".join(
        f"[Segment {i + 1}]: {chunk}" for i, chunk in enumerate(chunks)
    )
    prompt = _CORE_MEMORY_MERGE_PROMPT.format(
        target_tokens=target_tokens,
        existing_core=existing_core or "(none — this is the first merge)",
        new_summaries=new_summaries_text,
    )

    logger.debug(
        "[Summarizer:core_merge] calling model=%s | chunks=%d | target_tokens=%d",
        model, len(chunks), target_tokens,
    )

    t0 = time.monotonic()
    client = _get_client()
    response = await client.chat.completions.create(
        model=model, # Azure treats this as the deployment name
        messages=[{"role": "user", "content": prompt}],
        max_tokens=target_tokens + 60,
        temperature=0.1,
    )
    elapsed = time.monotonic() - t0

    result = response.choices[0].message.content.strip()
    usage = response.usage
    logger.info(
        "[Summarizer:core_merge_done] model=%s | latency=%.2fs | "
        "prompt_tokens=%d | completion_tokens=%d | total_tokens=%d | output_chars=%d",
        model,
        elapsed,
        usage.prompt_tokens if usage else -1,
        usage.completion_tokens if usage else -1,
        usage.total_tokens if usage else -1,
        len(result),
    )
    return result
