from datetime import datetime, timezone
from typing import Any
from app.db.database import get_conn

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def upsert_vendor(v: dict[str, Any]) -> int:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO vendors(id, vendor_name, vendor_code, tax_id, address, status, default_payment_terms)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET vendor_name=excluded.vendor_name, vendor_code=excluded.vendor_code,
            tax_id=excluded.tax_id, address=excluded.address, status=excluded.status,
            default_payment_terms=excluded.default_payment_terms
        """, (v["id"], v["vendor_name"], v["vendor_code"], v.get("tax_id"), v.get("address"), v.get("status", "ACTIVE"), v.get("default_payment_terms")))
    return int(v["id"])

def insert_invoice(inv: dict[str, Any]) -> int:
    now = utc_now()
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO invoices(id, vendor_id, invoice_number, invoice_date, due_date, subtotal, tax,
                                 total_amount, payment_terms, status, source_file, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (inv.get("id"), inv["vendor_id"], inv["invoice_number"], inv["invoice_date"], inv.get("due_date"),
              inv.get("subtotal"), inv.get("tax"), inv.get("total_amount"), inv.get("payment_terms"),
              inv.get("status", "PENDING"), inv.get("source_file"), inv.get("created_at", now), inv.get("updated_at", now)))
        return int(inv.get("id") or cur.lastrowid)

def list_invoices(vendor: str | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        if vendor:
            rows = conn.execute("""
                SELECT i.*, v.vendor_name, v.vendor_code, v.default_payment_terms
                FROM invoices i JOIN vendors v ON v.id=i.vendor_id
                WHERE lower(v.vendor_name)=lower(?) ORDER BY i.invoice_date DESC, i.id DESC
            """, (vendor,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT i.*, v.vendor_name, v.vendor_code, v.default_payment_terms
                FROM invoices i JOIN vendors v ON v.id=i.vendor_id
                ORDER BY i.invoice_date DESC, i.id DESC
            """).fetchall()
    return [dict(r) for r in rows]

def get_invoice(invoice_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT i.*, v.vendor_name, v.vendor_code, v.tax_id, v.default_payment_terms
            FROM invoices i JOIN vendors v ON v.id=i.vendor_id WHERE i.id=?
        """, (invoice_id,)).fetchone()
    return dict(row) if row else None

def find_invoice_by_number_vendor(vendor: str, invoice_number: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT i.*, v.vendor_name, v.vendor_code, v.default_payment_terms
            FROM invoices i JOIN vendors v ON v.id=i.vendor_id
            WHERE lower(v.vendor_name)=lower(?) AND upper(i.invoice_number)=upper(?)
        """, (vendor, invoice_number)).fetchall()
    return [dict(r) for r in rows]

def find_potential_duplicates(vendor: str, invoice_date: str, total_amount: float) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT i.*, v.vendor_name, v.vendor_code
            FROM invoices i JOIN vendors v ON v.id=i.vendor_id
            WHERE lower(v.vendor_name)=lower(?)
              AND i.invoice_date=?
              AND abs(coalesce(i.total_amount, 0)-?) < 0.01
        """, (vendor, invoice_date, total_amount)).fetchall()
    return [dict(r) for r in rows]

def get_vendor(vendor: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM vendors WHERE lower(vendor_name)=lower(?)", (vendor,)).fetchone()
    return dict(row) if row else None

def create_invoice(data: dict[str, Any], source_file: str | None = None) -> int:
    with get_conn() as conn:
        vendor = conn.execute("SELECT id FROM vendors WHERE lower(vendor_name)=lower(?)", (data["vendor_name"],)).fetchone()
        if not vendor:
            raise ValueError(f"Unknown vendor: {data['vendor_name']}")
        now = utc_now()
        cur = conn.execute("""
            INSERT INTO invoices(vendor_id, invoice_number, invoice_date, due_date, subtotal, tax,
                                 total_amount, payment_terms, status, source_file, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?)
        """, (vendor["id"], data["invoice_number"], str(data["invoice_date"]), str(data.get("due_date")) if data.get("due_date") else None,
              data.get("subtotal"), data.get("tax"), data.get("total_amount"), data.get("payment_terms"), source_file, now, now))
        return int(cur.lastrowid)

def update_invoice_status(invoice_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE invoices SET status=?, updated_at=? WHERE id=?", (status, utc_now(), invoice_id))

def log_attempt(task_id: str, invoice_id: int | None, action: str, status: str, error_type: str | None, error_message: str | None, attempt_number: int) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO processing_attempts(task_id, invoice_id, action, status, error_type, error_message, attempt_number, timestamp)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, invoice_id, action, status, error_type, error_message, attempt_number, utc_now()))

def create_worker_run(task_id: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO worker_runs(id, task_id, status, started_at) VALUES(?, ?, 'RUNNING', ?)", (task_id, task_id, utc_now()))

def finish_worker_run(task_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE worker_runs SET status=?, completed_at=? WHERE id=?", (status, utc_now(), task_id))

def save_approval(task_id: str, status: str, reason: str, decided_by: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO approvals(task_id, status, reason, decided_by, decided_at) VALUES(?, ?, ?, ?, ?)", (task_id, status, reason, decided_by, utc_now()))
