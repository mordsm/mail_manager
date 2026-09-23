import httpx
import json
import re
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, ValidationError
from app.llm.base import LLMProvider

class OllamaProvider(LLMProvider):
    """
    Local Ollama LLM provider implementation for low-cost, local-first classification,
    summarization, entity extraction, and wiki note synthesis.
    """
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model
        self.client = httpx.Client(timeout=30.0)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.base_url}/api/generate"
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
        }
        try:
            resp = self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except Exception as e:
            return f"[Ollama Provider Fallback] Unable to reach local model: {e}"

    def structured_output(self, prompt: str, response_model: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
        url = f"{self.base_url}/api/generate"
        schema_json = json.dumps(response_model.model_json_schema())
        sys_instructions = (
            f"{system_prompt or ''}\n"
            "You are a structured data extraction agent. Respond STRICTLY in valid JSON matching schema:\n"
            f"{schema_json}"
        )

        payload = {
            "model": self.model,
            "prompt": f"{sys_instructions}\n\nInput:\n{prompt}",
            "format": "json",
            "stream": False
        }
        try:
            resp = self.client.post(url, json=payload)
            resp.raise_for_status()
            raw_response = resp.json().get("response", "")
            data_dict = json.loads(raw_response)
            return response_model(**data_dict)
        except Exception as e:
            # Generate minimal fallback conforming instance
            return self._heuristic_fallback(prompt, response_model)

    def extract_entities_and_claims(self, text_content: str, domain: str) -> Dict[str, Any]:
        prompt = (
            f"Domain: {domain}\n"
            f"Content:\n{text_content[:3000]}\n\n"
            "Extract entities (people, companies, technologies, concepts), key claims, and candidate wikilinks."
        )
        try:
            res_text = self.generate(prompt, system_prompt="Extract structured knowledge units from document.")
            # Fallback regex extraction if unstructured
            entities = list(set(re.findall(r'\b[A-Z][a-zA-Z0-9\-_]{2,}\b', text_content)))[:10]
            concepts = list(set(re.findall(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]', text_content)))
            return {
                "summary": res_text[:500],
                "entities": entities,
                "concepts": concepts,
                "domain": domain
            }
        except Exception as e:
            return {
                "summary": text_content[:300] + "...",
                "entities": [],
                "concepts": [],
                "domain": domain,
                "error": str(e)
            }

    def _heuristic_fallback(self, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        # Fallback initializer for Pydantic models when Ollama is offline
        fields = response_model.model_fields
        fallback_data = {}
        for name, field in fields.items():
            if field.annotation == str:
                fallback_data[name] = "fallback_value"
            elif getattr(field.annotation, "__origin__", None) is list:
                fallback_data[name] = []
            elif field.annotation == bool:
                fallback_data[name] = True
            else:
                fallback_data[name] = "fallback"
        return response_model.model_construct(**fallback_data)

