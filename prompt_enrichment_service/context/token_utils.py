"""
Token counting utilities using tiktoken.
Provides accurate token counts for OpenAI-compatible models.
"""

import tiktoken
from functools import lru_cache


@lru_cache(maxsize=8)
def _get_encoding(model: str):
    """Cache encodings to avoid reloading on every call."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base (used by gpt-3.5-turbo, gpt-4)
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count the number of tokens in a string for the given model."""
    if not text:
        return 0
    enc = _get_encoding(model)
    return len(enc.encode(text))


def count_messages_tokens(messages: list[dict], model: str = "gpt-3.5-turbo") -> int:
    """
    Count total tokens for an OpenAI messages list.
    Accounts for the per-message overhead (role + formatting tokens).
    """
    # OpenAI adds ~4 tokens per message for role framing + 2 for reply priming
    PER_MESSAGE_OVERHEAD = 4
    REPLY_PRIMING = 2

    total = REPLY_PRIMING
    for msg in messages:
        total += PER_MESSAGE_OVERHEAD
        total += count_tokens(msg.get("content", ""), model)
        total += count_tokens(msg.get("role", ""), model)
    return total
