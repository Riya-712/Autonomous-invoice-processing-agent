from typing import Any
from app.models.invoice import InvoiceData
from app.models.verification import VerificationResult

def compare_invoice(expected: InvoiceData, actual: dict[str, Any]) -> VerificationResult:
    expected_map = {
        "vendor_name": expected.vendor_name,
        "invoice_number": expected.invoice_number,
        "invoice_date": expected.invoice_date.isoformat() if expected.invoice_date else None,
        "due_date": expected.due_date.isoformat() if expected.due_date else None,
        "total_amount": expected.total_amount,
    }
    mismatches: list[str] = []
    for key, exp in expected_map.items():
        act = actual.get(key)
        if key == "total_amount":
            if exp is None or act is None or abs(float(exp) - float(act)) > 0.01:
                mismatches.append(f"{key}: expected={exp}, actual={act}")
        elif str(exp) != str(act):
            mismatches.append(f"{key}: expected={exp}, actual={act}")
    verified = not mismatches and actual.get("status") in {"PENDING", "APPROVED"}
    return VerificationResult(verified=verified, mismatches=mismatches, evidence={"expected": expected_map, "actual": actual})
