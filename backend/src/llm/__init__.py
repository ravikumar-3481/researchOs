from .llm_provider import LLM


llm = LLM()
get_llm = llm.get_llm
get_llm_with_fallbacks = llm.get_llm_with_fallbacks

__all__ = ["llm", "get_llm", "get_llm_with_fallbacks"]

