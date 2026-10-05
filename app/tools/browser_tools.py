from pathlib import Path
from typing import Any
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from app.config import settings, SCREENSHOT_DIR
from app.db import repositories as repo
from app.models.invoice import InvoiceData
from app.models.tool_result import ToolResult
from app.verification.verifier import compare_invoice

class APBrowser:
    def __init__(self):
        self.p = sync_playwright().start()
        self.browser = self.p.chromium.launch(headless=True)
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()
        self.base = settings.ap_base_url.rstrip("/")

    def close(self):
        self.context.close()
        self.browser.close()
        self.p.stop()

    def ensure_login(self):
        self.page.goto(f"{self.base}/login", wait_until="domcontentloaded")
        if "/login" in self.page.url:
            self.page.fill("#username", settings.demo_username)
            self.page.fill("#password", settings.demo_password)
            self.page.click("#login-btn")
            self.page.wait_for_load_state("domcontentloaded")

    def open_dashboard(self):
        self.ensure_login()
        self.page.goto(f"{self.base}/", wait_until="domcontentloaded")
        return self.page.title()

def open_ap_application() -> ToolResult:
    browser = APBrowser()
    try:
        title = browser.open_dashboard()
        return ToolResult(
            success=True,
            tool_name="open_ap_application",
            observation=f"Opened AP application: {title}",
            data={"url": browser.page.url, "page": "dashboard"},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name="open_ap_application",
            observation=f"Failed to open AP application: {exc}",
            error_type="TRANSIENT",
            retryable=True,
        )
    finally:
        browser.close()

def search_ap_invoice(vendor: str, invoice_number: str | None = None) -> ToolResult:
    browser = APBrowser()
    try:
        browser.ensure_login()
        browser.page.goto(f"{browser.base}/invoices", wait_until="domcontentloaded")
        browser.page.fill("#vendor", vendor)
        if invoice_number:
            browser.page.fill("#invoice_number", invoice_number)
        browser.page.click("#search-btn")
        browser.page.wait_for_load_state("networkidle")
        rows = browser.page.locator("#results tbody tr")
        results = []
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            vals = [cells.nth(j).inner_text() for j in range(cells.count())]
            if vals:
                results.append(vals)
        return ToolResult(
            success=True,
            tool_name="search_ap_invoice",
            observation=f"AP search returned {len(results)} records.",
            data={"rows": results},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name="search_ap_invoice",
            observation=f"AP search failed: {exc}",
            error_type="TRANSIENT",
            retryable=True,
        )
    finally:
        browser.close()

def create_ap_invoice(invoice_data: InvoiceData, task_id: str | None = None, screenshot_name: str | None = None) -> ToolResult:
    browser = APBrowser()
    try:
        browser.ensure_login()
        browser.page.goto(f"{browser.base}/invoices/new", wait_until="domcontentloaded")
        browser.page.fill("#vendor", invoice_data.vendor_name)
        browser.page.fill("#invoice_number", invoice_data.invoice_number or "")
        browser.page.fill("#invoice_date", invoice_data.invoice_date.isoformat() if invoice_data.invoice_date else "")
        browser.page.fill("#due_date", invoice_data.due_date.isoformat() if invoice_data.due_date else "")
        browser.page.fill("#subtotal", str(invoice_data.subtotal or ""))
        browser.page.fill("#tax", str(invoice_data.tax or ""))
        browser.page.fill("#total_amount", str(invoice_data.total_amount or ""))
        browser.page.fill("#payment_terms", invoice_data.payment_terms or "")
        name = screenshot_name or f"before_submit_{task_id or 'run'}.png"
        browser.page.screenshot(path=str(SCREENSHOT_DIR / name), full_page=True)
        return ToolResult(
            success=True,
            tool_name="create_ap_invoice",
            observation="Invoice fields entered into AP form; not yet submitted.",
            data={"page": "invoice_creation", "screenshot": name, "ready_to_submit": True},
        )
    except PlaywrightTimeoutError as exc:
        return ToolResult(
            success=False,
            tool_name="create_ap_invoice",
            observation=f"Browser timeout: {exc}",
            error_type="TRANSIENT",
            retryable=True,
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name="create_ap_invoice",
            observation=f"Could not populate AP invoice form: {exc}",
            error_type="PERMANENT",
            retryable=False,
        )
    finally:
        browser.close()

def submit_invoice(task_id: str, screenshot_name: str | None = None) -> ToolResult:
    browser = APBrowser()
    try:
        browser.ensure_login()
        draft = browser.page.request.get(f"{browser.base}/api/drafts/{task_id}")
        if draft.status != 200 or not draft.json():
            return ToolResult(
                success=False,
                tool_name="submit_invoice",
                observation="No staged invoice draft found for task.",
                error_type="VALIDATION",
                retryable=False,
            )
        data = draft.json()
        browser.page.goto(f"{browser.base}/invoices/new", wait_until="domcontentloaded")
        for field in ["vendor", "invoice_number", "invoice_date", "due_date", "subtotal", "tax", "total_amount", "payment_terms"]:
            browser.page.fill(f"#{field}", str(data.get(field) or ""))
        browser.page.fill("#task_id", task_id)
        browser.page.click("#submit-btn")
        browser.page.wait_for_load_state("domcontentloaded")
        error = browser.page.locator("#submit-error")
        if error.is_visible() and error.inner_text().strip():
            msg = error.inner_text().strip()
            error_type = "TRANSIENT" if "Temporary" in msg else ("DUPLICATE" if "Duplicate" in msg else "PERMANENT")
            return ToolResult(
                success=False,
                tool_name="submit_invoice",
                observation=msg,
                data={"page": browser.page.url},
                error_type=error_type,
                retryable=error_type == "TRANSIENT",
            )
        record_id_text = browser.page.locator("#created-id").inner_text().strip()
        if not record_id_text:
            return ToolResult(
                success=False,
                tool_name="submit_invoice",
                observation="Submit form did not return a record ID.",
                error_type="TRANSIENT",
                retryable=True,
            )
        name = screenshot_name or f"after_submit_{task_id}.png"
        browser.page.screenshot(path=str(SCREENSHOT_DIR / name), full_page=True)
        return ToolResult(
            success=True,
            tool_name="submit_invoice",
            observation=f"Invoice submitted successfully with record ID {record_id_text}.",
            data={"invoice_id": int(record_id_text), "screenshot": name},
        )
    except PlaywrightTimeoutError as exc:
        return ToolResult(
            success=False,
            tool_name="submit_invoice",
            observation=f"Browser timeout: {exc}",
            error_type="TRANSIENT",
            retryable=True,
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name="submit_invoice",
            observation=f"Submit failed: {exc}",
            error_type="TRANSIENT",
            retryable=True,
        )
    finally:
        browser.close()

def verify_invoice(invoice_id: int, expected: InvoiceData) -> ToolResult:
    browser = APBrowser()
    try:
        browser.ensure_login()
        browser.page.goto(f"{browser.base}/invoices/{invoice_id}", wait_until="domcontentloaded")
        actual = {
            "vendor_name": browser.page.locator("#actual-vendor").inner_text(),
            "invoice_number": browser.page.locator("#actual-invoice-number").inner_text(),
            "invoice_date": browser.page.locator("#actual-invoice-date").inner_text(),
            "due_date": browser.page.locator("#actual-due-date").inner_text(),
            "total_amount": float(browser.page.locator("#actual-total").inner_text()),
            "status": browser.page.locator("#actual-status").inner_text(),
        }
        result = compare_invoice(expected, actual)
        return ToolResult(success=result.verified, tool_name="verify_invoice", observation="Independent verification passed." if result.verified else "Independent verification failed.", data=result.evidence)
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name="verify_invoice",
            observation=f"Verification failed: {exc}",
            error_type="TRANSIENT",
            retryable=True,
        )
    finally:
        browser.close()
