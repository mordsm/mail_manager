from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel

class LLMProvider(ABC):
    """
    Abstract interface for LLM provider decoupling.
    Business logic must consume this interface without hardcoding specific APIs.
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generates text response for prompt.
        """
        pass

    @abstractmethod
    def structured_output(self, prompt: str, response_model: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
        """
        Generates Pydantic-conforming structured output.
        """
        pass

    @abstractmethod
    def extract_entities_and_claims(self, text_content: str, domain: str) -> Dict[str, Any]:
        """
        Extracts entities, concepts, claims, signals, and wikilinks from raw source.
        """
        pass
