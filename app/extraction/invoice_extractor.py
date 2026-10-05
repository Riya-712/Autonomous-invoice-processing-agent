import re
from datetime import datetime

from pypdf import PdfReader

from app.models.invoice import InvoiceData, ExtractionResult


DATE_PATTERNS = [
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%d/%b/%Y",
    "%d/%B/%Y",
]


def parse_date(value: str | None):
    if not value:
        return None

    value = value.strip()
    value = re.sub(r"\s+", " ", value)

    for fmt in DATE_PATTERNS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    # Fallback: find YYYY-MM-DD / YYYY/MM/DD anywhere in the value
    match = re.search(
        r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b",
        value
    )

    if match:
        normalized = match.group(0).replace("/", "-")

        try:
            return datetime.strptime(
                normalized,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            pass

    # Fallback: find DD-MM-YYYY / DD/MM/YYYY anywhere in the value
    match = re.search(
        r"\b\d{1,2}[-/]\d{1,2}[-/]20\d{2}\b",
        value
    )

    if match:
        normalized = match.group(0).replace("/", "-")

        try:
            return datetime.strptime(
                normalized,
                "%d-%m-%Y"
            ).date()
        except ValueError:
            pass

    return None


def money(value: str | None) -> float | None:
    if not value:
        return None

    # Keep only digits and decimal point.
    # This handles ₹, ■, $, commas, spaces, etc.
    cleaned = re.sub(r"[^0-9.]", "", value)

    return float(cleaned) if cleaned else None


def read_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)

    return "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )


def _match(pattern: str, text: str) -> str | None:
    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.MULTILINE
    )

    return match.group(1).strip() if match else None


def extract_invoice_data(document_text: str) -> ExtractionResult:

    vendor = (
        _match(
            r"Vendor\s*:\s*([^\r\n]+)",
            document_text
        )
        or _match(
            r"Supplier\s*:\s*([^\r\n]+)",
            document_text
        )
        or "Unknown Vendor"
    )

    invoice_number = _match(
        r"Invoice\s*(?:Number|No\.?)\s*:\s*(\S+)",
        document_text
    )

    invoice_date_raw = _match(
        r"Invoice\s*Date\s*:\s*([^\r\n]+)",
        document_text
    )

    due_date_raw = _match(
        r"Due\s*Date\s*:\s*([^\r\n]+)",
        document_text
    )

    # IMPORTANT:
    # PDF extraction may replace currency symbols with ■.
    # Therefore, don't specifically expect ₹.
    # Instead, allow any non-numeric characters before the number.
    subtotal_raw = _match(
        r"Subtotal\s*:\s*[^0-9\r\n]*([\d,]+(?:\.\d+)?)",
        document_text
    )

    tax_raw = _match(
        r"Tax\s*:\s*[^0-9\r\n]*([\d,]+(?:\.\d+)?)",
        document_text
    )

    total_raw = _match(
        r"Total\s*Amount\s*:\s*[^0-9\r\n]*([\d,]+(?:\.\d+)?)",
        document_text
    )

    terms = _match(
        r"Payment\s*Terms\s*:\s*([^\r\n]+)",
        document_text
    )

    tax_id = _match(
        r"Vendor\s*Tax\s*ID\s*:\s*(\S+)",
        document_text
    )

    invoice = InvoiceData(
        vendor_name=vendor,
        invoice_number=invoice_number,
        invoice_date=parse_date(invoice_date_raw),
        due_date=parse_date(due_date_raw),
        subtotal=money(subtotal_raw),
        tax=money(tax_raw),
        total_amount=money(total_raw),
        payment_terms=terms,
        vendor_tax_id=tax_id,
    )

    missing = [
        name
        for name, value in {
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "total_amount": invoice.total_amount,
        }.items()
        if value is None
    ]

    confidence = {
        field: (
            0.98 if field not in missing else 0.0
        )
        for field in [
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "due_date",
            "total_amount",
        ]
    }

    return ExtractionResult(
        invoice=invoice,
        missing_fields=missing,
        confidence=confidence,
    )