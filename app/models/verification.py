from typing import Any
from pydantic import BaseModel, Field

class VerificationResult(BaseModel):
    verified: bool
    mismatches: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
