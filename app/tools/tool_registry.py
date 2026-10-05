import json
from app.models.tool_result import ToolResult
from app.models.invoice import InvoiceData
from app.models.state import WorkerState
from app.tools.base import Tool
from app.tools.file_tools import search_invoice_files, read_invoice
from app.tools.invoice_tools import select_latest_invoice, extract_from_document, lookup_vendor_payment_terms, compute_due_date_from_terms
from app.tools.policy_tools import check_policy
from app.tools.browser_tools import open_ap_application, search_ap_invoice, create_ap_invoice, submit_invoice, verify_invoice
from app.db import repositories as repo


def check_duplicate_invoice(invoice_data: InvoiceData) -> ToolResult:
    exact = repo.find_invoice_by_number_vendor(invoice_data.vendor_name, invoice_data.invoice_number or "")
    if exact:
        record = exact[0]
        conflicts=[]
        for field, expected, actual in [
            ("invoice_date", invoice_data.invoice_date.isoformat() if invoice_data.invoice_date else None, record.get("invoice_date")),
            ("due_date", invoice_data.due_date.isoformat() if invoice_data.due_date else None, record.get("due_date")),
            ("total_amount", invoice_data.total_amount, record.get("total_amount")),
        ]:
            if expected is not None and str(expected) != str(actual):
                conflicts.append(f"{field}: source={expected}, AP={actual}")
        if conflicts:
            status="CONFLICTING_EXISTING_RECORD"
        else:
            status="EXACT_DUPLICATE"
        return ToolResult(success=True, tool_name="check_duplicate_invoice", observation=f"Duplicate check: {status}", data={"status":status,"record":record,"conflicts":conflicts})
    if invoice_data.invoice_date and invoice_data.total_amount is not None:
        potential=repo.find_potential_duplicates(invoice_data.vendor_name, invoice_data.invoice_date.isoformat(), invoice_data.total_amount)
        if potential:
            return ToolResult(success=True, tool_name="check_duplicate_invoice", observation="Potential duplicate detected.", data={"status":"POTENTIAL_DUPLICATE","records":potential})
    return ToolResult(success=True, tool_name="check_duplicate_invoice", observation="No matching AP record found.", data={"status":"NO_MATCH"})

def build_registry():
    return {
        t.name: t for t in [
            Tool("search_invoice_files","Find invoice PDF files for a vendor.",{"type":"object","properties":{"vendor":{"type":"string"}},"required":["vendor"]},search_invoice_files),
            Tool("select_latest_invoice","Select the candidate invoice with the latest usable invoice date.",{"type":"object","properties":{"files":{"type":"array","items":{"type":"string"}}},"required":["files"]},select_latest_invoice),
            Tool("read_invoice","Read a PDF invoice and return its text.",{"type":"object","properties":{"file_path":{"type":"string"}},"required":["file_path"]},read_invoice),
            Tool("extract_invoice_data","Extract structured invoice fields from document text.",{"type":"object","properties":{"document_text":{"type":"string"}},"required":["document_text"]},extract_from_document),
            Tool("lookup_vendor_payment_terms","Retrieve unambiguous default payment terms from vendor master.",{"type":"object","properties":{"vendor":{"type":"string"}},"required":["vendor"]},lookup_vendor_payment_terms),
            Tool("compute_due_date_from_terms","Derive due date from invoice date and payment terms when terms are explicit, such as Net 30.",{"type":"object","properties":{"invoice_date":{"type":"string"},"payment_terms":{"type":"string"}},"required":["invoice_date","payment_terms"]},compute_due_date_from_terms),
            Tool("check_duplicate_invoice","Check AP for exact, potential or conflicting duplicates before creation.",{"type":"object","properties":{"invoice_data":{"type":"object"}},"required":["invoice_data"]},check_duplicate_invoice),
            Tool("check_policy","Evaluate deterministic company policies using the worker's validated invoice extraction and duplicate-check result.",{"type":"object","properties":{}},check_policy),
            Tool("open_ap_application","Open the simulated enterprise AP application.",{"type":"object","properties":{}},open_ap_application),
            Tool("search_ap_invoice","Search the AP application for an invoice.",{"type":"object","properties":{"vendor":{"type":"string"},"invoice_number":{"type":["string","null"]}},"required":["vendor"]},search_ap_invoice),
            Tool("create_ap_invoice","Populate and stage an AP invoice through the enterprise UI; this does not submit it.",{"type":"object","properties":{}},lambda **_: ToolResult(success=False,tool_name="create_ap_invoice",observation="Host executor must run this tool.",error_type="AUTHORIZATION",retryable=False)),
            Tool("submit_invoice","Submit the staged AP invoice through the enterprise UI.",{"type":"object","properties":{}},lambda **_: ToolResult(success=False,tool_name="submit_invoice",observation="Host executor must run this tool.",error_type="AUTHORIZATION",retryable=False)),
            Tool("verify_invoice","Independently re-read an AP record and compare it with expected invoice values.",{"type":"object","properties":{"invoice_id":{"type":"integer"},"expected":{"type":"object"}},"required":["invoice_id","expected"]},lambda **_: ToolResult(success=False,tool_name="verify_invoice",observation="Host executor must run this tool.",error_type="AUTHORIZATION",retryable=False)),
        ]
    }
