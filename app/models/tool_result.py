from typing import Any, Literal
from pydantic import BaseModel, Field

FailureType = Literal["TRANSIENT", "PERMANENT", "VALIDATION", "DUPLICATE", "POLICY", "AMBIGUITY", "AUTHORIZATION"]

class ToolResult(BaseModel):
    success: bool
    tool_name: str
    observation: str
    data: dict[str, Any] = Field(default_factory=dict)
    error_type: FailureType | None = None
    retryable: bool = False
