import httpx
import json
import re
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, ValidationError
from app.llm.base import LLMProvider

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL

class OllamaProvider(LLMProvider):
    """
    Local Ollama LLM provider implementation for low-cost, local-first classification,
    summarization, entity extraction, and wiki note synthesis.
    """
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=180.0)
        self._resolve_active_model()

    def _resolve_active_model(self) -> None:
        """
        Queries Ollama to verify if the configured model is available;
        if not, selects the best matching available model.
        """
        try:
            resp = self.client.get(f"{self.base_url}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                available_models = [m["name"] for m in resp.json().get("models", [])]
                if self.model in available_models:
                    return
                # Check for prefix match, e.g. "llama3.2" matching "llama3.2:latest"
                for m in available_models:
                    if m.startswith(self.model) or self.model.startswith(m.split(":")[0]):
                        self.model = m
                        return
                if available_models:
                    self.model = available_models[0]
        except Exception:
            pass  # Keep default configured model if server offline

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.base_url}/api/generate"
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": 380,
                "temperature": 0.2,
                "top_p": 0.9
            }
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
        """
        Uses Ollama to extract summary, entities, concepts, and claims in JSON format.
        """
        sys_prompt = (
            "You are an expert knowledge synthesis agent for Obsidian LLM Wiki. "
            "Extract structured information from the input text and return ONLY a valid JSON object with keys: "
            "'summary' (string: concise 2-4 sentences), "
            "'entities' (array of strings: important named entities/people/tools), "
            "'concepts' (array of strings: 3-6 key concepts/topics suitable for [[wikilinks]]), "
            "'claims' (array of strings: 1-3 factual claims or assertions made)."
        )
        prompt = f"Domain: {domain}\nContent:\n{text_content[:4000]}"
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{sys_prompt}\n\n{prompt}",
            "format": "json",
            "stream": False
        }
        try:
            resp = self.client.post(url, json=payload, timeout=45.0)
            if resp.status_code == 200:
                raw_json = resp.json().get("response", "{}")
                data = json.loads(raw_json)
                summary = data.get("summary") or text_content[:300]
                entities = data.get("entities") or []
                concepts = data.get("concepts") or []
                claims = data.get("claims") or []
                return {
                    "summary": summary,
                    "entities": entities,
                    "concepts": concepts,
                    "claims": claims,
                    "domain": domain
                }
        except Exception:
            pass

        # Fallback regex extraction if Ollama fails or format is invalid
        entities = list(set(re.findall(r'\b[A-Z][a-zA-Z0-9\-_]{2,}\b', text_content)))[:10]
        concepts = list(set(re.findall(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]', text_content)))
        if not concepts:
            # Extract common conceptual words
            words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', text_content) if w.lower() not in {"this", "that", "with", "from", "have"}]
            concepts = list(dict.fromkeys(words))[:5]

        return {
            "summary": text_content[:350].strip() + ("..." if len(text_content) > 350 else ""),
            "entities": entities,
            "concepts": concepts,
            "claims": [],
            "domain": domain
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

