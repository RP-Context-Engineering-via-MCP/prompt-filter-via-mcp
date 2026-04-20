import os
from dotenv import load_dotenv
from context import ATCEConfig

load_dotenv()

# Service URLs
USER_MANAGER_URL = os.environ.get("USER_MANAGER_URL", "http://localhost:8000")
CHAT_LOGGER_URL = os.environ.get("CHAT_LOGGER_URL", "http://localhost:3005")
PREDEFINED_PROFILE_URL = os.environ.get("PREDEFINED_PROFILE_URL", "http://localhost:8002")
BEHAVIOR_EXTRACTION_URL = os.environ.get("BEHAVIOR_EXTRACTION_URL", "http://localhost:8001")
CORE_BEHAVIOR_URL = os.environ.get("CORE_BEHAVIOR_URL", "http://localhost:6009/context")

# Redis Config
REDIS_URL = os.environ.get("REDIS_URL", "redis://default:4SSKIbQ1aCuRRCfmkAlbiZynWXR3rxVy@redis-14142.c265.us-east-1-2.ec2.cloud.redislabs.com:14142")
REDIS_SESSION_TTL = int(os.environ.get("REDIS_SESSION_TTL", 432000))

# ATCE Config
ATCE_CFG = ATCEConfig(
    max_context_tokens=int(os.environ.get("MAX_CONTEXT_TOKENS", 8192)),
    response_buffer=int(os.environ.get("RESPONSE_BUFFER", 1024)),
    tier1_pair_limit=int(os.environ.get("TIER1_PAIR_LIMIT", 10)),
    compression_chunk_pairs=int(os.environ.get("COMPRESSION_CHUNK_PAIRS", 4)),
    tier2_token_limit=int(os.environ.get("TIER2_TOKEN_LIMIT", 1500)),
    tier3_target_tokens=int(os.environ.get("TIER3_TARGET_TOKENS", 150)),
    model=os.environ.get("INFERENCE_MODEL", os.environ.get("CONDENSATION_MODEL", "gpt-4.1-mini")),
    summarization_model=os.environ.get("SUMMARIZATION_MODEL", os.environ.get("CONDENSATION_MODEL", "gpt-4.1-mini")),
)

# LLM Config
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", os.environ.get("OPENAI_API_KEY"))
OPENAI_API_VERSION = os.environ.get("OPENAI_API_VERSION", "2024-02-01")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", os.environ.get("OPENAI_ENDPOINT"))
