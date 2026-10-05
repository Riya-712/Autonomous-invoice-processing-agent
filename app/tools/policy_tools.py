from app.models.tool_result import ToolResult
from app.policies.policy_engine import PolicyEngine
from app.models.invoice import ExtractionResult

ENGINE = PolicyEngine()

def check_policy(extraction: ExtractionResult, duplicate_status: str) -> ToolResult:
    decision = ENGINE.evaluate(extraction, duplicate_status)
    return ToolResult(
        success=True,
        tool_name="check_policy",
        observation=decision.reason,
        data={
            "decision": decision.model_dump(mode="json"),
            "policy_text_loaded": bool(ENGINE.raw_policy),
        },
    )
