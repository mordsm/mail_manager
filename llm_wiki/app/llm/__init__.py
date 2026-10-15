import os
from typing import Optional
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.gemini_provider import GeminiProvider

def get_llm_provider(name: Optional[str] = None) -> LLMProvider:
    """
    Returns configured LLM provider according to parameter, env vars, or default.
    Options: 'gemini', 'ollama', 'openai'.
    """
    selected = (name or os.environ.get("LLM_PROVIDER", "")).lower()
    
    if selected == "gemini":
        return GeminiProvider()
    elif selected == "openai":
        return OpenAIProvider()
    elif selected == "ollama":
        return OllamaProvider()

    # Automatic smart selection:
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return GeminiProvider()
    elif os.environ.get("OPENAI_API_KEY") and not os.environ.get("OPENAI_API_KEY", "").startswith("sk-placeholder"):
        return OpenAIProvider()
    else:
        return OllamaProvider()

__all__ = ["LLMProvider", "OllamaProvider", "OpenAIProvider", "GeminiProvider", "get_llm_provider"]
