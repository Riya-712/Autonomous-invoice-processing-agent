from datetime import date
from app.models.invoice import InvoiceData
from app.models.tool_result import ToolResult
from app.models.state import WorkerState
from app.db import repositories as repo
from app.extraction.invoice_extractor import extract_invoice_data


def read_pdf_text(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_from_document(document_text: str) -> ToolResult:
    try:
        result = extract_invoice_data(document_text)
        return ToolResult(
            success=True,
            tool_name="extract_invoice_data",
            observation="Structured invoice extraction completed.",
            data={"extraction": result.model_dump(mode="json")},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name="extract_invoice_data",
            observation=str(exc),
            error_type="VALIDATION",
            retryable=False,
        )

def select_latest_invoice(files: list[str]) -> ToolResult:
    if not files:
        return ToolResult(
            success=False,
            tool_name="select_latest_invoice",
            observation="No invoice candidates available.",
            error_type="VALIDATION",
            retryable=False,
        )

    candidates = []
    extraction_errors = []

    for path in files:
        try:
            pdf_text = read_pdf_text(path)
            extracted = extract_invoice_data(pdf_text)

            candidates.append(
                (
                    path,
                    extracted.invoice.invoice_date,
                    extracted.invoice.invoice_number,
                )
            )

        except Exception as exc:
            extraction_errors.append(
                {
                    "file": path,
                    "error": str(exc),
                }
            )

    dated = [
        candidate
        for candidate in candidates
        if candidate[1] is not None
    ]

    if not dated:
        return ToolResult(
            success=False,
            tool_name="select_latest_invoice",
            observation=(
                "Could not determine latest invoice because "
                "no candidate has a usable invoice date."
            ),
            data={
                "candidates": [c[0] for c in candidates],
                "extraction_errors": extraction_errors,
            },
            error_type="VALIDATION",
            retryable=False,
        )

    selected = max(dated, key=lambda x: x[1])

    return ToolResult(
        success=True,
        tool_name="select_latest_invoice",
        observation=f"Selected latest invoice candidate {selected[2]}.",
        data={
            "file_path": selected[0],
            "invoice_number": selected[2],
            "invoice_date": str(selected[1]),
        },
    )

def lookup_vendor_payment_terms(vendor: str) -> ToolResult:
    data = repo.get_vendor(vendor)
    if not data:
        return ToolResult(
            success=False,
            tool_name="lookup_vendor_payment_terms",
            observation="Vendor not found in vendor master.",
            error_type="VALIDATION",
            retryable=False,
        )
    return ToolResult(
        success=True,
        tool_name="lookup_vendor_payment_terms",
        observation="Retrieved vendor payment terms.",
        data={"vendor_name": vendor, "default_payment_terms": data.get("default_payment_terms")},
    )

def compute_due_date_from_terms(invoice_date: str, payment_terms: str) -> ToolResult:
    import re
    from datetime import timedelta, datetime
    m = re.search(r"(\d+)\s*days?", payment_terms.lower())
    if not m:
        return ToolResult(
            success=False,
            tool_name="compute_due_date_from_terms",
            observation="Payment terms are not machine-derivable.",
            error_type="AMBIGUITY",
            retryable=False,
        )
    d = datetime.fromisoformat(invoice_date).date() + timedelta(days=int(m.group(1)))
    return ToolResult(
        success=True,
        tool_name="compute_due_date_from_terms",
        observation=f"Derived due date as {d.isoformat()} from payment terms.",
        data={"due_date": d.isoformat(), "basis": payment_terms},
    )
