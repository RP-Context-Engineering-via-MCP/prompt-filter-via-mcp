from openai import AsyncAzureOpenAI
import logging
from .config import AZURE_OPENAI_KEY, OPENAI_API_VERSION, AZURE_OPENAI_ENDPOINT

logger = logging.getLogger(__name__)

_llm_client: AsyncAzureOpenAI | None = None

def get_llm_client() -> AsyncAzureOpenAI:
    global _llm_client
    if _llm_client is None:
        if not AZURE_OPENAI_KEY:
            logger.warning("OpenAI API Key is not set or empty. LLM calls will fail if attempted.")
        _llm_client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version=OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
    return _llm_client
