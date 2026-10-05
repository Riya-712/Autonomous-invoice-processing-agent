from app.config import settings
from app.models.invoice import InvoiceData, ExtractionResult
from app.policies.schemas import PolicyDecision
from app.policies.policy_loader import load_policy_text
import re

class PolicyEngine:
    def __init__(self):
        self.raw_policy = load_policy_text()

    def _limits(self) -> tuple[float, float]:
        auto = float(re.search(r"below INR\s*([0-9,]+)", self.raw_policy, re.IGNORECASE).group(1).replace(",", "")) if re.search(r"below INR\s*([0-9,]+)", self.raw_policy, re.IGNORECASE) else settings.approval_threshold
        manager = float(re.search(r"up to INR\s*([0-9,]+)", self.raw_policy, re.IGNORECASE).group(1).replace(",", "")) if re.search(r"up to INR\s*([0-9,]+)", self.raw_policy, re.IGNORECASE) else 500000.0
        return auto, manager

    def evaluate(self, extracted: ExtractionResult, duplicate_status: str) -> PolicyDecision:
        inv = extracted.invoice
        critical_missing = list(extracted.missing_fields)
        if duplicate_status in {"EXACT_DUPLICATE", "POTENTIAL_DUPLICATE", "CONFLICTING_EXISTING_RECORD"}:
            return PolicyDecision(
                allowed=False,
                approval_required=True,
                approval_role="AP reviewer",
                reason=f"Duplicate-control status is {duplicate_status}; creation is blocked pending review.",
                policy_rule="Duplicate policy: do not create a duplicate or resolve a conflict without human review.",
                critical_fields_missing=critical_missing,
            )
        if critical_missing:
            return PolicyDecision(
                allowed=False,
                approval_required=True,
                approval_role="AP reviewer",
                reason=f"Critical invoice fields are missing: {', '.join(critical_missing)}.",
                policy_rule="Exception policy: missing critical fields require human review unless safely derivable.",
                critical_fields_missing=critical_missing,
            )
        if inv.total_amount is None:
            return PolicyDecision(allowed=False, approval_required=True, approval_role="AP reviewer", reason="Total amount is missing.", policy_rule="Invoice policy: total amount is mandatory.", critical_fields_missing=[])
        auto_threshold, manager_threshold = self._limits()
        if inv.total_amount <= auto_threshold:
            return PolicyDecision(allowed=True, approval_required=False, approval_role=None, reason="Within autonomous approval threshold.", policy_rule=f"Approval matrix: <= INR {auto_threshold:,.0f} may be processed autonomously.", critical_fields_missing=[])
        if inv.total_amount <= manager_threshold:
            return PolicyDecision(allowed=False, approval_required=True, approval_role="Finance manager", reason=f"Amount ₹{inv.total_amount:,.2f} exceeds autonomous threshold.", policy_rule=f"Approval matrix: above INR {auto_threshold:,.0f} and up to INR {manager_threshold:,.0f} requires manager approval.", critical_fields_missing=[])
        return PolicyDecision(allowed=False, approval_required=True, approval_role="Finance controller", reason=f"Amount ₹{inv.total_amount:,.2f} exceeds manager threshold.", policy_rule=f"Approval matrix: > INR {manager_threshold:,.0f} requires finance controller approval.", critical_fields_missing=[])
