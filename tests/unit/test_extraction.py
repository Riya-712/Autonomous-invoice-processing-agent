from app.extraction.invoice_extractor import extract_invoice_data

def test_extract_fields():
    text='''Vendor: Acme Corporation\nVendor Tax ID: GSTIN27ACME1234Z1\nInvoice Number: ACME-2026-104\nInvoice Date: 2026-10-01\nDue Date: 2026-10-31\nSubtotal: ₹75,000.00\nTax: ₹13,500.00\nTotal Amount: ₹88,500.00\nPayment Terms: Net 30'''
    result=extract_invoice_data(text)
    assert result.invoice.invoice_number=="ACME-2026-104"
    assert result.invoice.total_amount==88500
    assert not result.missing_fields
