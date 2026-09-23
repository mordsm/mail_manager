import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Database Config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/llm_wiki")
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"

# LLM Config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Privacy Policies
PERSONAL_SENSITIVE_LOCAL_ONLY = os.getenv("PERSONAL_SENSITIVE_LOCAL_ONLY", "true").lower() == "true"

