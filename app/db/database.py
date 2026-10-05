import sqlite3
from contextlib import contextmanager
from pathlib import Path
from app.config import settings

DB_PATH = Path(str(settings.database_url).replace("sqlite:///", ""))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY,
    vendor_name TEXT UNIQUE NOT NULL,
    vendor_code TEXT UNIQUE NOT NULL,
    tax_id TEXT,
    address TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    default_payment_terms TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    invoice_number TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT,
    subtotal REAL,
    tax REAL,
    total_amount REAL,
    payment_terms TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    source_file TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(vendor_id) REFERENCES vendors(id)
);

CREATE TABLE IF NOT EXISTS processing_attempts (
    id INTEGER PRIMARY KEY,
    task_id TEXT NOT NULL,
    invoice_id INTEGER,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT,
    attempt_number INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);

CREATE TABLE IF NOT EXISTS worker_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT
);
"""

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
