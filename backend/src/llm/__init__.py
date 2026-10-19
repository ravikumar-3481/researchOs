from .llm_provider import LLM, LLMProviderError

llm = LLM()
get_llm = llm.get_llm
get_llm_with_fallbacks = llm.get_llm_with_fallbacks
get_llm_with_fallback = llm.get_llm_with_fallbacks

__all__ = [
    "llm",
    "LLM",
    "LLMProviderError",
    "get_llm",
    "get_llm_with_fallbacks",
    "get_llm_with_fallback",
]
