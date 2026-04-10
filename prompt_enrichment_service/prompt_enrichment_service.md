# Prompt Enrichment Service — Deep System Analysis

**Document Type:** Deep Technical System Analysis
**Service Version:** 2.0.0
**Service Port:** 3004
**Runtime:** Python 3.10 / FastAPI / Uvicorn
**Analysis Date:** 2026-03-22

---

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Module Structure](#3-module-structure)
4. [Core Algorithm: ATCE](#4-core-algorithm-atce)
5. [Data Models & Structures](#5-data-models--structures)
6. [Session Memory Management](#6-session-memory-management)
7. [Storage Layer: Redis vs In-Memory](#7-storage-layer-redis-vs-in-memory)
8. [External Service Integrations](#8-external-service-integrations)
9. [API Endpoints](#9-api-endpoints)
10. [Dual-Mode Operation](#10-dual-mode-operation)
11. [LLM Integration](#11-llm-integration)
12. [Summarization Pipeline](#12-summarization-pipeline)
13. [Token Budget System](#13-token-budget-system)
14. [Configuration & Environment](#14-configuration--environment)
15. [Request Lifecycle (End-to-End)](#15-request-lifecycle-end-to-end)
16. [Concurrency Model](#16-concurrency-model)
17. [Error Handling & Resilience](#17-error-handling--resilience)
18. [Logging & Observability](#18-logging--observability)
19. [Containerization](#19-containerization)
20. [Testing](#20-testing)
21. [System Dependencies](#21-system-dependencies)
22. [Known Gaps & Open Issues](#22-known-gaps--open-issues)
23. [Research Foundation](#23-research-foundation)
24. [Improvement Recommendations](#24-improvement-recommendations)

---

## 1. Service Overview

The Prompt Enrichment Service is a FastAPI microservice that acts as the **intelligent context layer** between the MCP Server (or web client) and the LLM. Its primary responsibility is to transform a raw user prompt into a semantically rich, contextually aware message payload that enables the LLM to produce personalized, coherent, and history-aware responses.

### Core Responsibilities

| Responsibility | Description |
|---|---|
| **User Context Injection** | Fetches and injects user profile, behavioral patterns, and core behavioral anchor into every prompt |
| **Conversation Memory** | Maintains tiered session memory (ATCE) across all turns of a conversation |
| **Context Assembly** | Builds token-budget-aware LLM message arrays respecting position-bias findings |
| **History Sync (MCP)** | Pulls historical chat logs from MongoDB and injects them into session memory |
| **LLM Invocation (Web Mode)** | Directly calls Azure OpenAI and returns both the enriched prompt and the LLM response |
| **Client-Switch Detection** | Detects when user switches LLM clients and injects full ATCE history string |
| **Session Lifecycle** | Creates, retrieves, persists, and deletes session memory via Redis |

### Position in the System

```
MCP Server (port 3001)
    │
    ├── POST /filter  ──→  Prompt Filter Engine (port 3003)
    │
    └── POST /enrich  ──→  Prompt Enrichment Service (port 3004)  ← THIS SERVICE
                                    │
                                    ├── Redis (session memory)
                                    ├── User Manager (port 8080)
                                    ├── Predefined Profile Service (port 8002)
                                    ├── Behavior Extraction Service (port 8001)
                                    ├── Core Behavior Service (port 6009)
                                    ├── Chat Logger Backend (port 3005)
                                    └── Azure OpenAI (LLM calls)
```

---

## 2. Architecture Overview

The service is built around two distinct processing concerns that map to clean module boundaries:

```
prompt_enrichment_service/
├── main.py                    # FastAPI app, route handlers, lifespan hooks
├── core/
│   ├── config.py              # Env-var loading, ATCE config construction
│   └── llm_client.py          # Lazy-init Azure OpenAI async client singleton
├── services/
│   ├── external_clients.py    # All outbound HTTP calls (aiohttp singleton)
│   └── enrichment_service.py  # Business logic: fetch_user_context, sync_mcp_turns
└── context/                   # ATCE algorithm package
    ├── __init__.py            # Public exports
    ├── session_memory.py      # Data structures: Message, ChunkSummary, SessionMemory
    ├── atce.py                # Core algorithm: assemble_messages, store_turn
    ├── redis_store.py         # Write-through L1+Redis store
    ├── summarizer.py          # Async LLM-based compression (Tier 1→2, Tier 2→3)
    └── token_utils.py         # tiktoken-based token counting
```

### Design Principles

1. **Dual-mode gateway** — Supports two distinct caller types (MCP and Web Client) with different output contracts
2. **Non-blocking compression** — ATCE tier compression runs as `asyncio` background tasks; it never adds latency to the response path
3. **Write-through cache** — Redis is the durable store; in-process L1 dict is the fast read path
4. **Parallel I/O** — All external context fetches use `asyncio.gather()` for concurrent execution
5. **Graceful degradation** — Every external call has exception handling; failures return defaults, not crashes

---

## 3. Module Structure

### `main.py`

The application entry point. Responsibilities:

- Selects the active store (Redis if `REDIS_URL` is set, in-memory otherwise)
- Registers lifespan hooks for HTTP session and Redis client management
- Defines Pydantic request/response schemas
- Implements the two route handlers (`/enrich`, `/session/{id}/debug`, `/session/{id}` DELETE, `/health`)
- Dispatches background task `_store_and_persist` after web-client responses

### `core/config.py`

Loads all environment variables via `python-dotenv` and constructs the `ATCEConfig` instance that is shared across the application. Provides a single import point for all configuration values. Notable: supports multiple env-var aliases (e.g., `AZURE_OPENAI_KEY` or `OPENAI_API_KEY`) for backward compatibility.

### `core/llm_client.py`

Implements a lazy-initialized singleton `AsyncAzureOpenAI` client. The client is only created on first call to `get_llm_client()`, preventing import-time failures when the API key is absent (development). Thread-safety for initialization is not explicitly guarded but is safe under asyncio's single-threaded event loop.

### `services/external_clients.py`

Single `ExternalClients` class (module-level singleton `external_clients`) wrapping all outbound HTTP calls with `aiohttp`. Uses a single `ClientSession` initialized at app startup and closed on shutdown via FastAPI lifespan. Exposes:

- `get_current_session_id(user_id)` → User Manager
- `get_predefined_profile_id(user_id)` → User Manager
- `get_predefined_profile(profile_id)` → Predefined Profile Service
- `get_latest_chat_log(user_id, selected_session_id)` → Chat Logger
- `get_behavior_extraction_data(prompt, user_id, session_id, recent_history)` → Behavior Extraction
- `get_user_core_behavior_extraction(user_id)` → Core Behavior Service

### `services/enrichment_service.py`

Three functions:

1. `fetch_user_context(prompt, user_id, session_id)` — Orchestrates parallel context fetches and formats the composite user context string injected into the LLM system message.
2. `sync_mcp_turns(session_id, user_id, selected_session_id, store, cfg)` — Reconciles unsynced MongoDB chat logs into ATCE session memory.
3. `format_atce_history(session_mem)` — Serializes ATCE memory tiers to a human-readable string for client-switch injection.

### `context/` package

The ATCE implementation. Detailed in Section 4.

---

## 4. Core Algorithm: ATCE

**ATCE (Adaptive Tiered Context Enrichment)** is the research algorithm at the heart of this service. It solves the fundamental problem of maintaining semantically coherent, token-efficient conversation context across unlimited turns within a finite LLM context window.

### Research Motivation

The algorithm addresses four hard constraints:

| Constraint | Problem |
|---|---|
| **Context window overflow** | LLM inputs are finite; unbounded history always exceeds them |
| **Quadratic cost scaling** | Transformer attention is O(n²); naively re-sending full history is expensive |
| **API cost growth** | Every input token is billed; re-submitting 50K tokens per turn is prohibitive |
| **Lost-in-the-middle bias** | LLMs have U-shaped recall: best at START and END, worst in the middle |

### Three-Tier Memory Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│  SessionMemory                                               │
│                                                             │
│  Tier 1 — tier1_buffer    : List[Message]                   │
│    Full-fidelity verbatim messages (newest N pairs)         │
│    Default limit: 10 user/assistant pairs                   │
│    Eviction: overflow triggers async Tier 2 compression     │
│                                                             │
│  Tier 2 — tier2_summaries : List[ChunkSummary]              │
│    Compressed chunk summaries of older Tier 1 content       │
│    Target: ~300 tokens per chunk                            │
│    Eviction: overflow triggers async Tier 3 merge           │
│    Total limit: 1500 tokens                                 │
│                                                             │
│  Tier 3 — tier3_core_memory : str                           │
│    Ultra-compact running summary of all archived content    │
│    Target: ≤150 tokens                                      │
│    Continuously updated via merge                           │
│                                                             │
│  facts — dict[str, str]                                     │
│    Key-value store for extracted facts and sync state       │
│    Used for: last_synced_mongo_id (MongoDB sync cursor)     │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1 — Context Assembly (Per Request, Synchronous)

Called on every incoming `/enrich` request. No I/O. Returns an OpenAI-format message list.

**Layout (position-aware, informed by Liu et al. 2023):**

```
┌──────────────────────────────────────┐  ← START (High LLM recall zone)
│  SYSTEM message                      │
│    • Base system instructions        │  (attention sink — always first)
│    • User enrichment context         │  (profile + behavior + core behavior)
│    • Tier 3 core memory (if any)     │  (ultra-compact long-range summary)
│    • Tier 2 chunk summaries (if any) │  (medium-range context, middle zone)
├──────────────────────────────────────┤
│  Tier 1 messages (verbatim)          │  (recent history, newest → budget)
│    oldest → newest of those that fit │
├──────────────────────────────────────┤
│  New user message                    │  ← END (High LLM recall zone)
└──────────────────────────────────────┘
```

**Key implementation detail:** Tier 1 messages are selected newest-first (greedy fill within remaining token budget), then reversed to chronological order. This ensures the most recent content always fits, dropping only the oldest if the budget is tight.

### Phase 2 — Turn Storage & Tier Management (Post-Response, Async)

Called after every LLM response via FastAPI `BackgroundTasks`. Stores the turn in Tier 1 and triggers compression if tiers overflow.

**Compression cascade:**

```
store_turn() called
    │
    ├── Append [user_message, assistant_response] to Tier 1
    ├── Increment turn_counter
    │
    └── tier1_pair_count > tier1_pair_limit?
            │
            YES ──→ asyncio.create_task(_compress_tier1_overflow)
                        │
                        ├── Pop oldest compression_chunk_pairs*2 messages from Tier 1
                        ├── Call summarize_chunk() via Azure OpenAI (async)
                        ├── Append ChunkSummary to Tier 2
                        ├── persist() to Redis
                        │
                        └── tier2_total_tokens > tier2_token_limit?
                                │
                                YES ──→ _merge_tier2_into_tier3()
                                            │
                                            ├── Pop all but newest Tier 2 chunk
                                            ├── Call merge_into_core_memory() via Azure OpenAI
                                            ├── Update Tier 3 core memory
                                            └── persist() to Redis
```

### ATCE Configuration Parameters

| Parameter | Env Var | Default | Description |
|---|---|---|---|
| `max_context_tokens` | `MAX_CONTEXT_TOKENS` | 8192 | Total LLM context window budget |
| `response_buffer` | `RESPONSE_BUFFER` | 1024 | Tokens reserved for LLM output |
| `tier1_pair_limit` | `TIER1_PAIR_LIMIT` | 10 | Max user/assistant pairs in verbatim buffer |
| `compression_chunk_pairs` | `COMPRESSION_CHUNK_PAIRS` | 4 | Pairs to compress per Tier 2 chunk |
| `tier2_token_limit` | `TIER2_TOKEN_LIMIT` | 1500 | Max total tokens across all Tier 2 summaries |
| `tier3_target_tokens` | `TIER3_TARGET_TOKENS` | 150 | Target token count for Tier 3 core memory |
| `model` | `INFERENCE_MODEL` | `gpt-4.1-mini` | Model used for inference calls |
| `summarization_model` | `SUMMARIZATION_MODEL` | `gpt-4.1-mini` | Model used for compression/summarization |

### Complexity Analysis

| Operation | Time Complexity | Frequency |
|---|---|---|
| Context assembly | O(N1 + T2_count) | Every request |
| Token counting | O(total_tokens) | Every request |
| Tier 1 → 2 compression | O(C_size · T_llm) | Every N1 turns |
| Tier 2 → 3 merge | O(T2_max · T_llm) | Infrequently |
| Per-request overhead (amortized) | **O(1)** | — |

---

## 5. Data Models & Structures

### Pydantic Schemas (API Contract)

```python
class EnrichRequest(BaseModel):
    prompt: str                    # The user's raw (pre-filtered) prompt
    user_id: str                   # UUID of the authenticated user
    session_id: str | None = None  # Optional; fetched from User Manager if absent
    source: str = "web_client"     # "mcp" | "web_client"
    mcp_client: str | None = None  # Client name for switch detection (e.g. "claude_desktop")

class EnrichResponse(BaseModel):
    enriched_prompt: str           # Assembled enriched prompt (debug string in web mode)
    llm_response: str | None       # LLM response (web mode only; None for MCP mode)
    session_id: str                # Resolved compound session key: "{user_id}::{session_id}"
    turn_index: int                # Current turn number in this session
```

### Internal Data Structures

```python
@dataclass
class Message:
    role: str           # "user" | "assistant"
    content: str
    turn_index: int     # Global monotonic turn counter for the session
    token_count: int    # Pre-computed token count
    timestamp: datetime

@dataclass
class ChunkSummary:
    text: str
    turn_range: tuple[int, int]  # (first_turn_index, last_turn_index)
    token_count: int
    created_at: datetime

@dataclass
class SessionMemory:
    session_id: str
    tier1_buffer: list[Message]        # Verbatim recent messages
    tier2_summaries: list[ChunkSummary] # Compressed older chunks
    tier3_core_memory: str              # Ultra-compact long history
    facts: dict[str, str]              # Key facts + sync cursors
    turn_counter: int                  # Incremented each user→assistant round
```

### Session Key Convention

The session key stored in Redis and the in-memory store follows the compound format:

```
actual_session_id = f"{user_id}::{session_id}"
```

This namespaces sessions per user, preventing key collisions across users who might share similar session IDs.

---

## 6. Session Memory Management

### Session Lifecycle

```
Request arrives with user_id (+ optional session_id)
    │
    ├── session_id absent → GET /api/users/{user_id}/current-session
    │                         → resolved_session_id
    │
    ├── Compute: actual_session_id = f"{user_id}::{resolved_session_id}"
    │
    ├── Redis store? → await redis_store.ensure_loaded(actual_session_id)
    │                   ├── L1 hit  → use cached session
    │                   └── L1 miss → load from Redis (or create new)
    │
    └── Process request using session state
```

### Turn Counter

`session.turn_counter` is a monotonic integer incremented once per completed user→assistant exchange. It is stored in the `Message.turn_index` field for each message, enabling `ChunkSummary.turn_range` to accurately reference which turns are compressed in each chunk.

### facts Dictionary

Beyond user preferences, `facts` is used as a MongoDB sync cursor:

```python
session.facts["last_synced_mongo_id"] = "<MongoDB ObjectId of last synced log>"
```

On the next MCP sync, the service finds this ID in the chat log list and starts injecting from the next entry, ensuring no duplicate turns are stored.

---

## 7. Storage Layer: Redis vs In-Memory

### Decision Logic

```python
if REDIS_URL:  # env var is set and non-empty
    active_store = RedisConversationStore(redis_url=REDIS_URL, ttl=REDIS_SESSION_TTL)
else:
    active_store = None  # falls back to module-level conversation_store (in-memory)
```

### In-Memory Store (`ConversationStore`)

- `threading.Lock` protects the `_sessions` dict against concurrent access
- Sessions are **lost on process restart** (no persistence)
- Used as MVP / development fallback

### Redis Store (`RedisConversationStore`)

**Architecture: Write-through L1 cache + Redis backend**

```
Request path (sync, fast):
    assemble_messages() → reads L1 dict directly (no Redis I/O)

Write path (async):
    store_turn() → writes L1 dict
    persist()    → serializes L1 → Redis (setex with TTL)

On server restart:
    ensure_loaded() → L1 miss → Redis GET → deserialize → L1 write
```

**Serialization format:** JSON with explicit field mapping. All datetime objects serialized as ISO 8601 strings. `turn_range` tuple stored as JSON array.

**TTL:** Default 5 days (432,000 seconds), configurable via `REDIS_SESSION_TTL`.

**Redis key pattern:** `atce:session:{actual_session_id}`

**Connection settings:**
- `socket_connect_timeout`: 3 seconds
- `socket_timeout`: 5 seconds
- Lazy initialization: Redis client created on first access

**Double-checked locking in `ensure_loaded()`:** Acquires lock before L1 lookup, releases before Redis call, then re-acquires to write. This prevents multiple concurrent coroutines from all loading the same session from Redis simultaneously.

**Persist callback pattern:** `make_persist_fn(session_id)` returns a zero-argument coroutine used by the ATCE compression tasks to persist state after each tier transition, without the compression functions needing a direct reference to the Redis store.

---

## 8. External Service Integrations

All outbound HTTP calls use a single shared `aiohttp.ClientSession` (singleton `external_clients`). The session is initialized at FastAPI startup and closed on shutdown.

### Integration Map

| Service | URL | Method | Purpose | Timeout |
|---|---|---|---|---|
| User Manager | `{USER_MANAGER_URL}/api/users/{user_id}/current-session` | GET | Resolve current session ID | 5s |
| User Manager | `{USER_MANAGER_URL}/api/users/{user_id}/predefined-profile-id` | GET | Get profile ID | 5s |
| Predefined Profile | `{PREDEFINED_PROFILE_URL}/api/predefined-profiles/{profile_id}` | GET | Fetch full profile | 5s |
| Chat Logger | `{CHAT_LOGGER_URL}/api/chats?user_id=...&selected_session_id=...` | GET | Fetch latest chat log / MCP sync | 5–10s |
| Behavior Extraction | `{BEHAVIOR_EXTRACTION_URL}/v2/extract` | POST | Real-time behavior extraction | 15s |
| Core Behavior | `{CORE_BEHAVIOR_URL}/{user_id}` | POST | Identity anchor prompt | 5s |

### Context Fetch Strategy — Parallel Batching

`fetch_user_context()` uses two-stage `asyncio.gather()`:

```python
# Stage 1: two independent calls in parallel
profile_id, (recent_history, last_source) = await asyncio.gather(
    external_clients.get_predefined_profile_id(user_id),
    external_clients.get_latest_chat_log(user_id, session_id),
)

# Stage 2: three calls in parallel (profile_id needed from stage 1)
profile_ctx, behavior_ctx, core_behavior_ctx = await asyncio.gather(
    external_clients.get_predefined_profile(profile_id),
    external_clients.get_behavior_extraction_data(prompt, user_id, session_id, recent_history),
    external_clients.get_user_core_behavior_extraction(user_id),
)
```

Total external call latency = max(stage1) + max(stage2), not the sum of all 5 calls.

### Predefined Profile Parsing

The service extracts and formats specific fields from the profile response:

| Field | Label |
|---|---|
| `profile_name` | `Profile:` |
| `context_statement` | `Context:` |
| `assumptions` | `Assumptions:` (joined) |
| `ai_guidance` | `Guidance:` (joined) |
| `preferred_response_style` | `Style:` (joined) |
| `context_injection_prompt` | `Injection:` |

### User Context String Format

The assembled user context injected into the LLM system message:

```
Profile: {predefined_profile_text}
Behavior: {behavior_extraction_text}
Core behavior: {core_behavior_text}
This is user behaviour context, when if generating the prompt if those behaviours are use full use them. Not Print this again. Provide user requested prompt answer.
```

> **Note:** The instruction at the end contains a typo ("behaviours are use full") and grammatical issues. This is a known issue (see Section 22).

---

## 9. API Endpoints

### `POST /enrich`

The primary endpoint. Accepts `EnrichRequest`, returns `EnrichResponse`.

**Behavior by source:**

| `source` field | Behavior |
|---|---|
| `"mcp"` | Syncs MongoDB turns, fetches user context, assembles enriched prompt string. No LLM call. Returns `llm_response: null`. |
| `"web_client"` | Fetches user context, assembles ATCE message list, calls Azure OpenAI, stores turn async. Returns both `enriched_prompt` and `llm_response`. |

**Session resolution:** If `session_id` is null in the request, the service fetches `current_session_id` from User Manager. Falls back to `"default"` if the call fails.

### `GET /health`

Returns service status including:
- `status: "healthy"`
- `store`: `"redis"` or `"in-memory"`
- `active_sessions`: count of sessions in L1 cache
- `redis_reachable`: boolean (Redis mode only)

### `GET /session/{session_id}/debug`

Loads the session into L1 cache (if Redis mode) and returns `session.debug_summary()`:

```json
{
  "session_id": "...",
  "turn_counter": 12,
  "tier1_messages": 6,
  "tier2_chunks": 2,
  "tier2_tokens": 650,
  "tier3_tokens": 48,
  "facts_count": 1
}
```

Returns 404 if session not found.

### `DELETE /session/{session_id}`

- Redis mode: removes from both L1 cache and Redis (`delete_remote()`)
- In-memory mode: removes from dict, 404 if not found

---

## 10. Dual-Mode Operation

### MCP Mode

Called by the MCP Server (`source="mcp"`). The MCP Server manages the actual LLM interaction (it forwards the enriched prompt to whichever AI platform the user is using — Claude, ChatGPT, Gemini).

**Flow:**
1. Sync unsynced MongoDB turns into ATCE memory (`sync_mcp_turns`)
2. Fetch user context (parallel external calls)
3. Detect client switch (compare `mcp_client` vs `last_source` from chat log)
4. If client switch: serialize full ATCE history to string (`format_atce_history`)
5. Assemble enriched prompt string (NOT an OpenAI message array)
6. Return `enriched_prompt` with `llm_response: null`

**Enriched prompt format (MCP):**
```
{user_context}

{atce_history_str (if client switch)}
User Prompt: {request.prompt}
```

**Client switch injection:** When `mcp_client != last_source`, the service injects the full ATCE session history (Tier 3 core memory + Tier 2 summaries + Tier 1 recent messages) as a formatted string block. This enables seamless cross-LLM context handoff without the new LLM having any prior conversation history.

### Web Client Mode

Called directly by the React web client. The service acts as a full LLM proxy.

**Flow:**
1. Fetch user context (parallel external calls)
2. Assemble ATCE message array (OpenAI format with role/content)
3. Call Azure OpenAI with message array
4. Register `_store_and_persist` as FastAPI BackgroundTask (non-blocking)
5. Return both the debug-formatted enriched prompt and the LLM response

---

## 11. LLM Integration

### Client

`AsyncAzureOpenAI` from the `openai` Python SDK. Lazy-initialized singleton in `core/llm_client.py`.

### Configuration

| Env Var | Default | Description |
|---|---|---|
| `AZURE_OPENAI_KEY` / `OPENAI_API_KEY` | — | Azure OpenAI API key |
| `OPENAI_API_VERSION` | `2024-02-01` | Azure API version |
| `AZURE_OPENAI_ENDPOINT` / `OPENAI_ENDPOINT` | — | Azure deployment endpoint |

### Inference Call (Web Mode)

```python
completion = await client.chat.completions.create(
    model=ATCE_CFG.model,         # "gpt-4.1-mini" (Azure deployment name)
    messages=messages,             # ATCE-assembled message array
    max_tokens=ATCE_CFG.response_buffer,  # 1024
    temperature=0.7,
)
```

### Mock Fallback

If `AZURE_OPENAI_KEY` is not set or equals `"your_api_key_here"`, the service returns a mock response:
```
[MOCK RESPONSE] Turn {N} | context: {M} msgs
```
This allows local development without API credentials.

### Error Handling

LLM errors raise `HTTPException(status_code=502)` with the exception message, propagating the error to the caller.

---

## 12. Summarization Pipeline

### Tier 1 → Tier 2 Compression (`summarize_chunk`)

**Trigger:** `tier1_pair_count > tier1_pair_limit`
**Input:** Oldest `compression_chunk_pairs * 2` messages from Tier 1
**Target output:** ~300 tokens
**Model call:**

```python
response = await client.chat.completions.create(
    model=cfg.summarization_model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=target_tokens + 80,  # 380 tokens max
    temperature=0.1,                # Low temp for consistency
)
```

**Prompt strategy:** Instructs the LLM to preserve specific facts, numbers, names, user decisions, and key conclusions while omitting pleasantries, verbose re-explanations, and resolved clarifications.

**On failure:** The original messages are restored to Tier 1 buffer to prevent data loss.

### Tier 2 → Tier 3 Merge (`merge_into_core_memory`)

**Trigger:** `tier2_total_tokens > tier2_token_limit`
**Input:** All Tier 2 chunks except the newest + existing Tier 3 core memory
**Target output:** ≤150 tokens
**Key behavior:** The newest Tier 2 chunk is **retained verbatim** to preserve recent granularity. Only older chunks are merged into Tier 3.

**Merge prompt rules:**
- Retain only facts that cannot be inferred from the user profile or general knowledge
- Prioritize: major user decisions, long-running preferences, key domain facts, named entities
- Write in dense factual prose (not bullet lists)
- Discard anything recoverable from context or common sense

**On failure:** The merged Tier 2 chunks are restored; Tier 3 retains its previous value.

---

## 13. Token Budget System

### Token Counting (`token_utils.py`)

Uses `tiktoken` for accurate OpenAI-compatible token counts. Encoding is cached with `@lru_cache(maxsize=8)`.

**Per-message overhead accounting:**
```python
PER_MESSAGE_OVERHEAD = 4  # per-message role framing tokens
REPLY_PRIMING = 2         # tokens for reply priming
```

### Budget Calculation

```python
T_available = T_max - T_sys - tokens(new_message) - T_response_buffer - overhead

Where:
  T_max = max_context_tokens (default: 8192)
  T_sys = tokens(system_content) + 4  (system message overhead)
  T_response_buffer = response_buffer (default: 1024)
  overhead = 2  (reply priming)
```

**Remaining budget** is used to greedily include Tier 1 messages from newest to oldest. Any Tier 1 messages that don't fit trigger a warning log but are silently dropped (not an error).

---

## 14. Configuration & Environment

### Full Environment Variable Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `USER_MANAGER_URL` | `http://localhost:8080` | Yes | User Management Service base URL |
| `CHAT_LOGGER_URL` | `http://localhost:3005` | Yes | Chat Logger Backend base URL |
| `PREDEFINED_PROFILE_URL` | `http://localhost:8002` | Yes | Predefined Profile Service base URL |
| `BEHAVIOR_EXTRACTION_URL` | `http://localhost:8001` | Yes | Behavior Extraction Service base URL |
| `CORE_BEHAVIOR_URL` | `http://localhost:6009/context` | Yes | Core Behavior Service base URL |
| `REDIS_URL` | `""` | No | Redis connection URL; if empty, uses in-memory store |
| `REDIS_SESSION_TTL` | `432000` | No | Redis key TTL in seconds (default: 5 days) |
| `MAX_CONTEXT_TOKENS` | `8192` | No | Total LLM context window size |
| `RESPONSE_BUFFER` | `1024` | No | Reserved output token budget |
| `TIER1_PAIR_LIMIT` | `10` | No | Max verbatim message pairs |
| `COMPRESSION_CHUNK_PAIRS` | `4` | No | Pairs compressed per Tier 2 chunk |
| `TIER2_TOKEN_LIMIT` | `1500` | No | Max total Tier 2 token budget |
| `TIER3_TARGET_TOKENS` | `150` | No | Target Tier 3 core memory size |
| `INFERENCE_MODEL` | `gpt-4.1-mini` | No | Azure deployment name for inference |
| `SUMMARIZATION_MODEL` | `gpt-4.1-mini` | No | Azure deployment name for summarization |
| `AZURE_OPENAI_KEY` | — | Yes (web mode) | Azure OpenAI API key |
| `OPENAI_API_VERSION` | `2024-02-01` | No | Azure API version |
| `AZURE_OPENAI_ENDPOINT` | — | Yes (web mode) | Azure OpenAI endpoint URL |

### `.gitignore`

The service has a `.gitignore` file; the `venv/` directory is present in the repo folder but excluded from tracking.

---

## 15. Request Lifecycle (End-to-End)

### MCP Source Request

```
1. POST /enrich { prompt, user_id, session_id?, source="mcp", mcp_client }
2. Resolve session_id (GET User Manager if absent)
3. Compute actual_session_id = f"{user_id}::{session_id}"
4. ensure_loaded(actual_session_id) — Redis L1 warm-up
5. sync_mcp_turns():
   a. Get session.turn_counter
   b. GET /api/chats from Chat Logger (up to 100 logs)
   c. Find start index using facts["last_synced_mongo_id"] or last user message
   d. For each unsynced log: await store_turn()
   e. Update facts["last_synced_mongo_id"]
6. fetch_user_context() [parallel]:
   a. get_predefined_profile_id → get_predefined_profile
   b. get_latest_chat_log (for last_source)
   c. get_behavior_extraction_data
   d. get_user_core_behavior_extraction
7. Detect client switch (mcp_client != last_source)
8. If switch: format_atce_history(session_mem)
9. Build enriched_prompt string
10. Return EnrichResponse(enriched_prompt, llm_response=None, session_id, turn_index)
```

### Web Client Source Request

```
1. POST /enrich { prompt, user_id, session_id?, source="web_client" }
2. Resolve session_id (GET User Manager if absent)
3. Compute actual_session_id
4. ensure_loaded(actual_session_id)
5. fetch_user_context() [parallel] — same as MCP steps 6a-6d
6. assemble_messages(actual_session_id, prompt, user_context):
   a. get_or_create session
   b. Build system message with tiers (Tier 3, Tier 2, user context)
   c. Compute history budget
   d. Greedily fill Tier 1 messages (newest first)
   e. Append new user message
   f. Return OpenAI message array
7. Check AZURE_OPENAI_KEY → call Azure OpenAI or return mock
8. Register BackgroundTask: _store_and_persist(session_id, user_msg, llm_response)
9. Return EnrichResponse(enriched_prompt_debug, llm_response, session_id, turn_index)

Background task (non-blocking):
10. store_turn() — append to Tier 1, increment turn_counter
11. If Tier 1 overflows → asyncio.create_task(_compress_tier1_overflow)
12. persist() to Redis
```

---

## 16. Concurrency Model

The service runs on a single asyncio event loop (standard FastAPI/uvicorn single-worker). Concurrency characteristics:

| Component | Concurrency Model |
|---|---|
| FastAPI request handlers | Async coroutines on event loop |
| External HTTP calls | Async aiohttp, uses `asyncio.gather()` for parallelism |
| ATCE context assembly | Synchronous (no I/O, runs inline) |
| Tier compression | `asyncio.create_task()` — scheduled but non-blocking |
| Redis operations | Async (`redis.asyncio`) |
| ConversationStore dict | `threading.Lock` (defensive; not needed in single-loop asyncio but safe) |
| LLM client | `AsyncAzureOpenAI` — async |

### Background Task Naming

Each compression task is named for observability:
```python
asyncio.create_task(
    _compress_tier1_overflow(session, cfg, persist_fn=persist_fn),
    name=f"atce_compress_{session_id}_{session.turn_counter}",
)
```

---

## 17. Error Handling & Resilience

### External Call Failures

Every `external_clients` method wraps its call in a `try/except Exception`. On failure:

| Method | Failure Return |
|---|---|
| `get_current_session_id` | `"default"` |
| `get_predefined_profile_id` | `""` |
| `get_predefined_profile` | `"Failed to fetch predefined profile."` |
| `get_latest_chat_log` | `([], None)` |
| `get_behavior_extraction_data` | `"No behavior extracted."` |
| `get_user_core_behavior_extraction` | `"No Core Behavious found"` |

This means any single external service going down does not crash the enrichment service — it degrades gracefully with reduced context quality.

### ATCE Compression Failures

Both `_compress_tier1_overflow` and `_merge_tier2_into_tier3` implement rollback on exception:

```python
except Exception as exc:
    # Restore buffer to prevent data loss
    session.tier1_buffer = overflow + session.tier1_buffer
    # or
    session.tier2_summaries = chunks_to_merge + session.tier2_summaries
```

This prevents permanent data loss if the summarization LLM call fails transiently.

### LLM Inference Failures (Web Mode)

Propagated as `HTTPException(status_code=502, detail=f"LLM error: {exc}")`.

### Session Not Found

`GET /session/{id}/debug` and `DELETE /session/{id}` (in-memory mode) return HTTP 404 for unknown sessions.

---

## 18. Logging & Observability

All modules use Python `logging` with the module's `__name__`. Log format:

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Key Log Events

| Logger Tag | Level | When |
|---|---|---|
| `[ATCE:assemble]` | INFO | Start of context assembly, showing tier states |
| `[ATCE:system_msg]` | DEBUG | System message composition breakdown |
| `[ATCE:budget_exceeded]` | WARNING | Tier 1 messages could not fit in budget |
| `[ATCE:store_turn]` | INFO | Turn stored, tier counts, pair limit comparison |
| `[ATCE:overflow]` | INFO | Compression triggered |
| `[ATCE:compress_t1]` | INFO | Compression starting, inputs |
| `[ATCE:compress_t1_done]` | INFO | Compression complete, ratio, latency, Tier 2 total |
| `[ATCE:compress_t1_error]` | ERROR | Compression failed, buffer restored |
| `[ATCE:merge_t2t3]` | INFO | Tier 3 merge starting |
| `[ATCE:merge_t2t3_done]` | INFO | Merge complete, compression ratio, latency |
| `[ATCE:merge_t2t3_error]` | ERROR | Merge failed, Tier 2 restored |
| `[ATCE:budget]` | DEBUG | Budget breakdown per request |
| `[RedisStore:load]` | INFO | Session restored from Redis |
| `[RedisStore:new]` | INFO | New session created |
| `[RedisStore:load_error]` | ERROR | Redis load failure |
| `[RedisStore:persist]` | DEBUG | Successful Redis write |
| `[RedisStore:persist_error]` | ERROR | Redis write failure |
| `[Summarizer:chunk]` | DEBUG | Summarization call parameters |
| `[Summarizer:chunk_done]` | INFO | Summarization complete, token usage, latency |
| `[Summarizer:core_merge]` | DEBUG | Core memory merge parameters |
| `[Summarizer:core_merge_done]` | INFO | Merge complete, token usage, latency |
| `[EnrichService]` | INFO | Request start (source, user, session, prompt_len) |
| `[EnrichService:mcp_sync]` | INFO | MCP sync count and latency |
| `[EnrichService:llm]` | INFO | LLM call latency, prompt/completion tokens |
| `[EnrichService:llm_error]` | ERROR | LLM call failure |
| `[sync_mcp_turns]` | INFO / ERROR | Sync operation detail |
| `[UserContext]` | ERROR | Context fetch failure |

---

## 19. Containerization

### Dockerfile

```dockerfile
FROM python:3.10-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 3004
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3004"]
```

Base image: `python:3.10-slim` (minimal Debian). No multi-stage build. Dependencies installed before source copy to maximize Docker layer cache efficiency.

### Docker Compose Integration

Defined in `chatApp/docker-compose.yml` with service name `prompt-enrichment-service`. Connects to the `chat-app-network` bridge network, enabling hostname resolution for inter-service calls.

---

## 20. Testing

### Test Script: `test_enrich.py`

A simple integration test script (not a pytest suite) that POSTs to the live service:

- Tests MCP source with hardcoded `user_id` and `session_id`
- Tests web_client source with same payload
- Hardcoded user_id: `5ca4d3ee-a139-44f9-9f9a-84655025a8f2` (development fixture)

### Tests Directory

A `tests/` directory exists but was not populated with test files at analysis time.

### Test Logs

A `test_logs/` directory exists containing raw log output from manual test runs.

### Coverage Gaps

- No unit tests for ATCE algorithm (assemble_messages, store_turn)
- No unit tests for token counting or budget calculation
- No unit tests for serialization/deserialization (Redis round-trip)
- No mocked tests for external service failure scenarios
- No load/stress tests for tier compression under high concurrency

---

## 21. System Dependencies

### Python Dependencies (`requirements.txt`)

| Package | Purpose |
|---|---|
| `fastapi` | HTTP framework, dependency injection, background tasks |
| `uvicorn` | ASGI server |
| `openai` | Azure OpenAI SDK (`AsyncAzureOpenAI`) |
| `pydantic` | Request/response schema validation |
| `python-dotenv` | `.env` file loading |
| `tiktoken` | Accurate OpenAI-compatible token counting |
| `redis` | Redis async client (`redis.asyncio`) |
| `aiohttp` | Async HTTP client for external service calls |

### External Service Dependencies

| Service | Criticality | Failure Impact |
|---|---|---|
| User Manager (8080) | High | Session resolution fails → uses "default" |
| Redis | Medium | Falls back to in-memory (no persistence) |
| Azure OpenAI | High (web mode) | 502 error returned to caller |
| Azure OpenAI (summarizer) | Medium | Compression fails → rollback, data retained |
| Predefined Profile (8002) | Low | Reduced context quality |
| Behavior Extraction (8001) | Low | Reduced context quality |
| Core Behavior (6009) | Low | Reduced context quality |
| Chat Logger (3005) | Medium (MCP mode) | MCP sync fails → stale ATCE state |

---

## 22. Known Gaps & Open Issues

### Code-Level Issues

1. **Typo in user context instruction:** `"those behaviours are use full"` and `"Not Print this again"` — grammatically incorrect instruction that is injected into every LLM prompt. This may degrade response quality.

2. **MCP sync creates a new aiohttp session per call:** `sync_mcp_turns()` creates `aiohttp.ClientSession()` inline instead of reusing the `external_clients.session` singleton. This creates unnecessary connection overhead and bypasses connection pooling.

3. **`get_user_core_behavior_extraction` uses POST for a read:** The Core Behavior endpoint is accessed via HTTP POST at `{CORE_BEHAVIOR_URL}/{user_id}`. REST convention would use GET for a read-only fetch. This is a protocol mismatch.

4. **No authentication on API endpoints:** The service exposes `/enrich`, `/session/{id}/debug`, and `/session/{id}` with no authentication. Any caller with network access can read or delete session data.

5. **MCP mode does not call `store_turn`:** In MCP mode, the service returns the enriched prompt but does NOT store the turn in ATCE memory. Turn storage in MCP mode relies entirely on `sync_mcp_turns()` fetching the turn from MongoDB on the next request. This introduces a 1-request lag in ATCE memory.

6. **Hard-coded test user ID:** `5ca4d3ee-a139-44f9-9f9a-84655025a8f2` appears in `test_enrich.py` and in `chatApp/mcp-server/src/tools.js`. Should be parameterized.

7. **ATCE config in `atce.py` defaults differ from `core/config.py` defaults:** `atce.py` defaults `tier1_pair_limit=3` and `tier2_token_limit=1000`, while `core/config.py` sets `tier1_pair_limit=10` and `tier2_token_limit=1500`. The `ATCEConfig` instance from `config.py` is always used in production, but the mismatch could confuse developers testing with the module defaults.

8. **TODO comment in summarizer:** `# TODO: We can get the user session and do more comprihansive summary in tier 2 -> tier 3` — a typo-ridden placeholder indicating incomplete integration of user profile into Tier 3 compression.

9. **`enriched_prompt` field in web mode returns debug format:** The `EnrichResponse.enriched_prompt` field in web client mode returns a debug-formatted string (role headers + content) rather than the actual assembled prompt. This is not the format consumed by LLMs.

10. **No rate limiting or request queuing:** Under high load, many concurrent requests could trigger simultaneous Azure OpenAI calls, potentially exceeding rate limits.

### Architectural Gaps

11. **Fact extraction not implemented:** The research design specifies lightweight NLP-based fact extraction from each turn. The `facts` dict is currently only used as a MongoDB sync cursor. Named entity extraction, preference tracking, and decision recording are not implemented.

12. **Semantic retrieval not implemented:** The importance scoring function `importance(m, q) = α·R(m) + β·S(m,q) + γ·D(m) + δ·E(m,q)` from the research document is not implemented. Tier 1 selection is currently recency-only.

13. **Topic-boundary detection not implemented:** Chunk boundaries are fixed-size (`compression_chunk_pairs`) rather than semantically determined.

14. **Cross-session memory not implemented:** The `facts` dict resets per session. Long-running user preferences do not persist across sessions.

15. **No Tier 2 oldest-first filtering in budget-exhausted scenarios:** When the token budget is very tight, all Tier 2 summaries are included in the system message (oldest-first ordering is handled by list ordering, but no selective dropping of oldest Tier 2 chunks is implemented).

---

## 23. Research Foundation

The ATCE algorithm is grounded in the following published research:

| Paper | Key Contribution | Applied In |
|---|---|---|
| Liu et al. (2023) *Lost in the Middle* (arXiv:2307.03172) | U-shaped recall: best at START/END, worst in middle | Position-aware context layout (system message head + new message tail) |
| Xiao et al. (2023) *Streaming LLM with Attention Sinks* (arXiv:2309.17453) | Initial tokens attract disproportionate attention ("attention sinks") | User context and system prompt always placed first in system message |
| Packer et al. (2023) *MemGPT* (arXiv:2310.08560) | OS-inspired virtual context: RAM (active) + disk (archival) | Three-tier memory model; tier eviction on overflow |
| Li et al. (2023) *Selective Context* | 20–32x compression with <2% performance loss | Tier 2 and Tier 3 summarization approach |
| Mem0 (2024) | Selective fact extraction vs. full summarization | facts dict design (partially implemented) |

---

## 24. Improvement Recommendations

### High Priority

1. **Fix user context instruction string** — Remove typos, rewrite as clear LLM instruction.
2. **Reuse `external_clients.session` in `sync_mcp_turns`** — Eliminate per-call session creation.
3. **Add authentication middleware** — Require a Bearer token or API key for all endpoints.
4. **Implement MCP turn storage** — After injecting the enriched prompt, the MCP server should call back to store the completed turn (or the service should expose a `POST /store-turn` endpoint).

### Medium Priority

5. **Fix ATCE default config mismatch** — Align `ATCEConfig` defaults between `atce.py` and `core/config.py`.
6. **Add unit test suite** — Cover ATCE algorithm with pytest, mock the LLM summarizer with pre-defined responses.
7. **Implement lightweight fact extraction** — Use spaCy NER or regex to populate the `facts` dict with user preferences and stated decisions.
8. **Fix the `enriched_prompt` field in web mode** — Return the actual assembled prompt or a structured representation, not a debug string.

### Low Priority / Future Research

9. **Semantic importance scoring** — Implement the full `importance(m, q)` function for relevance-ranked Tier 1 selection.
10. **Topic-boundary detection** — Use sentence embedding similarity to detect natural chunk boundaries for better Tier 2 quality.
11. **Cross-session memory** — Persist user-level facts across sessions to maintain long-term user preferences.
12. **Adaptive tier sizing** — Dynamically adjust `tier1_pair_limit` based on average message length and remaining context budget.
13. **Streaming LLM responses** — Implement SSE streaming for web client mode to improve perceived latency.
14. **Metrics endpoint** — Expose Prometheus metrics for token usage, compression frequency, and summarization latency.

---

*Analysis generated from source code at commit state: 2026-03-22*
*All file paths relative to: `d:\SLIIIT\Research\Dev\chatApp\prompt_enrichment_service\`*
