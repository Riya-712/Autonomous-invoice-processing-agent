from app.models.invoice import InvoiceData, ExtractionResult
from app.policies.policy_engine import PolicyEngine
from datetime import date

def extraction(amount=50000, missing=None):
    inv=InvoiceData(vendor_name="Acme Corporation",invoice_number="A-1",invoice_date=date(2026,10,1),due_date=date(2026,10,31),subtotal=amount/1.18,tax=amount-amount/1.18,total_amount=amount,payment_terms="Net 30")
    return ExtractionResult(invoice=inv,missing_fields=missing or [])

def test_autonomous_threshold():
    d=PolicyEngine().evaluate(extraction(50000),"NO_MATCH")
    assert d.allowed and not d.approval_required

def test_manager_approval():
    d=PolicyEngine().evaluate(extraction(150000),"NO_MATCH")
    assert not d.allowed and d.approval_required and d.approval_role=="Finance manager"

def test_duplicate_requires_review():
    d=PolicyEngine().evaluate(extraction(50000),"EXACT_DUPLICATE")
    assert not d.allowed and d.approval_required
