from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ECONOMIC_SPENDING_", env_file=".env", extra="ignore")

    data_path: Path = Field(default=Path("data/spending_events.jsonl"))
    default_currency: str = "ILS"


@lru_cache
def get_settings() -> Settings:
    return Settings()
