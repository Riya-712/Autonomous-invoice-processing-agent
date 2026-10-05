from pydantic import BaseModel, Field

class PolicyDecision(BaseModel):
    allowed: bool
    approval_required: bool
    approval_role: str | None = None
    reason: str
    policy_rule: str
    critical_fields_missing: list[str] = Field(default_factory=list)
