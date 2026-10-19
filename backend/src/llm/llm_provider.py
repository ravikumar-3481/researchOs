from typing import Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from config import settings
from src.utils.logger import logger

_log = logger.bind(service="llm_provider")


class LLMProviderError(Exception):
    """Raised for any problem creating an LLM (bad provider, missing key, missing package)."""


PROVIDERS = {
    "openai": {"model": "gpt-4o-mini", "get_key": settings.get_openai_api_key},
    "groq": {"model": "openai/gpt-oss-20b", "get_key": settings.get_groq_api_key},
    "gemini": {"model": "gemini-2.5-flash", "get_key": settings.get_gemini_api_key},
}

# Provider aliases
PROVIDER_ALIASES = {
    "google": "gemini",
}



class LLM:
    def __init__(self) -> None:
        # Per-instance cache: same settings -> same model object
        self._cache: Dict[tuple, BaseChatModel] = {}

    def _get_api_key(self, provider: str) -> str:
        """Get the key using the getter function from config.py."""
        try:
            return PROVIDERS[provider]["get_key"]()
        except ValueError as exc:  # config getters raise ValueError if key is missing
            raise LLMProviderError(f"{exc}. Add it to your .env file.") from exc

    def _create_model(
        self, provider: str, model: str, api_key: str, **params
    ) -> BaseChatModel:
        """Import the provider's package only when needed, then build the model."""
        try:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model=model, api_key=api_key, **params)

            if provider == "groq":
                from langchain_groq import ChatGroq
                return ChatGroq(model=model, api_key=api_key, **params)

            if provider == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model, google_api_key=api_key, **params
                )

        except ImportError as exc:
            raise LLMProviderError(
                f"Package for '{provider}' is not installed: {exc}"
            ) from exc
        except Exception as exc:  # bad params, SDK errors, etc.
            raise LLMProviderError(
                f"Could not initialize {provider}/{model}: {exc}"
            ) from exc

        raise LLMProviderError(f"Unsupported provider: {provider}")

    def get_llm(
        self,
        provider: str = "groq",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout: int = 60,
        max_retries: int = 3,
    ) -> BaseChatModel:
        """Return a chat model for the given provider. Results are cached."""
        provider = provider.lower()
        provider = PROVIDER_ALIASES.get(provider, provider)
        if provider not in PROVIDERS:
            raise LLMProviderError(
                f"Unsupported provider '{provider}'. Choose from: {', '.join(PROVIDERS)}"
            )

        model = model or PROVIDERS[provider]["model"]
        cache_key = (provider, model, temperature, max_tokens, timeout, max_retries)

        if cache_key in self._cache:
            return self._cache[cache_key]

        llm = self._create_model(
            provider,
            model,
            self._get_api_key(provider),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._cache[cache_key] = llm
        _log.info(f"Initialized LLM provider={provider} model={model}")
        return llm

    def get_llm_with_fallbacks(
        self,
        primary: str,
        fallbacks: List[str],
        model: Optional[str] = None,  # applies to the PRIMARY only
        **kwargs,
    ) -> Runnable:
        """Primary model; if it fails at runtime, try each fallback in order."""
        main = self.get_llm(primary, model=model, **kwargs)

        backups = []
        for name in fallbacks:
            try:
                # Fallbacks use their own default model names
                backups.append(self.get_llm(name, **kwargs))
            except LLMProviderError as exc:
                _log.warning(f"Skipping fallback '{name}': {exc}")

        return main.with_fallbacks(backups) if backups else main

    # Method alias for convenience
    get_llm_with_fallback = get_llm_with_fallbacks


# Usage:
#   llms = LLM()
#   llm = llms.get_llm("groq")
#   llm = llms.get_llm("openai", temperature=0.7)
#   llm = llms.get_llm_with_fallbacks("groq", ["openai", "google"])
#   response = llm.invoke("Hello!")