from typing import Any, Literal
from pydantic import BaseModel, Field
from app.models.invoice import InvoiceData, ExtractionResult

class ActionEvent(BaseModel):
    timestamp: str
    event_type: str
    tool: str | None = None
    status: str
    details: dict[str, Any] = Field(default_factory=dict)

class WorkerState(BaseModel):
    task_id: str
    user_task: str
    vendor: str | None = None
    candidate_files: list[str] = Field(default_factory=list)
    selected_invoice_file: str | None = None
    document_text: str | None = None
    extracted: InvoiceData | None = None
    extraction_meta: ExtractionResult | None = None
    duplicate_status: str = "unknown"
    policy_status: str = "not_checked"
    policy_reason: str | None = None
    approval_required: bool = False
    approval_status: Literal["not_required", "pending", "approved", "denied"] = "not_required"
    approval_reason: str | None = None
    current_page: str | None = None
    last_observation: dict[str, Any] | None = None
    action_history: list[ActionEvent] = Field(default_factory=list)
    retry_count: int = 0
    verification_status: Literal["pending", "passed", "failed"] = "pending"
    verification_evidence: dict[str, Any] = Field(default_factory=dict)
    ap_record_id: int | None = None
    draft_staged: bool = False
    status: Literal["RUNNING", "WAITING_FOR_APPROVAL", "COMPLETED", "FAILED"] = "RUNNING"
    completed: bool = False
    failure_reason: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    autonomous: bool = True
    step_count: int = 0
