from scripts.generate_data import main
from app.models.invoice import InvoiceData
from app.tools.tool_registry import check_duplicate_invoice
from datetime import date

def setup_module():
    main()

def test_exact_duplicate():
    inv=InvoiceData(vendor_name="Acme Corporation",invoice_number="ACME-2026-104",invoice_date=date(2026,10,1),due_date=date(2026,10,31),total_amount=88500)
    result=check_duplicate_invoice(inv)
    assert result.data["status"]=="EXACT_DUPLICATE"

def test_conflicting_record():
    inv=InvoiceData(vendor_name="Reliance Industrial Services",invoice_number="RIS-2026-CONFLICT",invoice_date=date(2026,10,3),due_date=date(2026,11,2),total_amount=96760)
    result=check_duplicate_invoice(inv)
    assert result.data["status"]=="CONFLICTING_EXISTING_RECORD"
