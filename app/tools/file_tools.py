from pathlib import Path

from app.config import INVOICE_DIR
from app.models.tool_result import ToolResult
from app.extraction.invoice_extractor import read_pdf_text


def search_invoice_files(vendor: str) -> ToolResult:
    matches = []
    for path in sorted(Path(INVOICE_DIR).glob("*.pdf")):
        try:
            text = read_pdf_text(str(path))
        except Exception:
            continue
        if vendor.lower() in text.lower():
            matches.append(str(path))
    return ToolResult(
        success=True,
        tool_name="search_invoice_files",
        observation=f"Found {len(matches)} invoice candidates for {vendor}.",
        data={"files": matches},
    )

def read_invoice(file_path: str) -> ToolResult:
    path = Path(file_path)
    if not path.exists():
        return ToolResult(
            success=False,
            tool_name="read_invoice",
            observation="Invoice file not found.",
            data={"file_path": file_path},
            error_type="PERMANENT",
            retryable=False,
        )
    try:
        text = read_pdf_text(str(path))
        return ToolResult(
            success=True,
            tool_name="read_invoice",
            observation=f"Read invoice document: {path.name}",
            data={"file_path": str(path), "text": text},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name="read_invoice",
            observation=f"Could not read PDF: {exc}",
            data={"file_path": file_path},
            error_type="PERMANENT",
            retryable=False,
        )
