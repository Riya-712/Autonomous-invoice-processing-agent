from datetime import date

from app.extraction import invoice_extractor
from app.models.invoice import ExtractionResult, InvoiceData
from app.tools import invoice_tools


def test_select_latest_invoice_returns_latest_candidate(monkeypatch):
    invoices = {
        "older.pdf": InvoiceData(
            vendor_name="Acme",
            invoice_number="INV-OLD",
            invoice_date=date(2026, 1, 15),
        ),
        "latest.pdf": InvoiceData(
            vendor_name="Acme",
            invoice_number="INV-NEW",
            invoice_date=date(2026, 3, 10),
        ),
    }

    def fake_extract(document_text):
        return ExtractionResult(invoice=invoices[document_text])

    monkeypatch.setattr(invoice_extractor, "read_pdf_text", lambda path: path)
    monkeypatch.setattr(invoice_extractor, "extract_invoice_data", fake_extract)

    result = invoice_tools.select_latest_invoice(["older.pdf", "latest.pdf"])

    assert result.success
    assert result.data == {
        "file_path": "latest.pdf",
        "invoice_number": "INV-NEW",
        "invoice_date": "2026-03-10",
    }
