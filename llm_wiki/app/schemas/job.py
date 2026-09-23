from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from datetime import datetime

JobStatus = Literal["QUEUED", "PROCESSING", "NEEDS_REVIEW", "COMPLETED", "FAILED", "DUPLICATE"]

class IngestionJob(BaseModel):
    job_id: str
    content_hash: str
    source_filename: str
    domain: str
    target_raw_path: str
    status: JobStatus = "QUEUED"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    error_message: Optional[str] = None
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict)

