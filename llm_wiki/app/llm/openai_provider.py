import os
import httpx
import json
import re
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
from app.llm.base import LLMProvider

class OpenAIProvider(LLMProvider):
    """
    Cloud OpenAI LLM provider for ultra-fast, high-quality responses (0.8s - 1.5s latency).
    Defaults to gpt-4o-mini for optimal cost and speed.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.Client(timeout=45.0)

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-"))

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available:
            return "[OpenAI Fallback] No valid OPENAI_API_KEY found."

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3
        }

        try:
            resp = self.client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[OpenAI Provider Error] {e}"

    def structured_output(self, prompt: str, response_model: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
        if not self.is_available:
            return self._heuristic_fallback(prompt, response_model)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        schema_json = json.dumps(response_model.model_json_schema())
        sys_instructions = (
            f"{system_prompt or ''}\n"
            "You are a structured data extraction agent. Respond STRICTLY in valid JSON matching schema:\n"
            f"{schema_json}"
        )

        messages = [
            {"role": "system", "content": sys_instructions},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        try:
            resp = self.client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            raw_response = resp.json()["choices"][0]["message"]["content"]
            data_dict = json.loads(raw_response)
            return response_model(**data_dict)
        except Exception:
            return self._heuristic_fallback(prompt, response_model)

    def extract_entities_and_claims(self, text_content: str, domain: str) -> Dict[str, Any]:
        if not self.is_available:
            return self._regex_fallback(text_content, domain)

        sys_prompt = (
            "You are an expert knowledge synthesis agent for Obsidian LLM Wiki. "
            "Extract structured information from the input text and return ONLY a valid JSON object with keys: "
            "'summary' (string: concise 2-4 sentences in Hebrew or English matching input), "
            "'entities' (array of strings: important named entities/people/tools), "
            "'concepts' (array of strings: 3-6 key concepts/topics suitable for [[wikilinks]]), "
            "'claims' (array of strings: 1-3 factual claims or assertions made)."
        )
        prompt = f"Domain: {domain}\nContent:\n{text_content[:6000]}"

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        try:
            resp = self.client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            raw_json = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(raw_json)
            return {
                "summary": data.get("summary") or text_content[:300],
                "entities": data.get("entities") or [],
                "concepts": data.get("concepts") or [],
                "claims": data.get("claims") or [],
                "domain": domain
            }
        except Exception:
            return self._regex_fallback(text_content, domain)

    def _regex_fallback(self, text_content: str, domain: str) -> Dict[str, Any]:
        entities = list(set(re.findall(r'\b[A-Z][a-zA-Z0-9\-_]{2,}\b', text_content)))[:10]
        concepts = list(set(re.findall(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]', text_content)))
        if not concepts:
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
        fields = response_model.model_fields
        defaults = {}
        for fname, fval in fields.items():
            if fval.default is not None:
                defaults[fname] = fval.default
            elif fval.annotation == str:
                defaults[fname] = "fallback"
            elif fval.annotation == int:
                defaults[fname] = 0
            elif fval.annotation == float:
                defaults[fname] = 0.5
            elif fval.annotation == list or getattr(fval.annotation, '__origin__', None) == list:
                defaults[fname] = []
            elif fval.annotation == dict:
                defaults[fname] = {}
            else:
                defaults[fname] = None
        try:
            return response_model(**defaults)
        except Exception:
            return response_model.model_construct(**defaults)

