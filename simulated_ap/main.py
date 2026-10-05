from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.db.database import init_db
from app.db import repositories as repo

app = FastAPI(title="CentrAlign Simulated AP")
app.add_middleware(SessionMiddleware, secret_key="centralign-demo-secret")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
DRAFTS: dict[str, dict] = {}
SUBMIT_ATTEMPTS: dict[str, int] = {}

@app.on_event("startup")
def startup():
    init_db()


def render(name: str, **ctx):
    path = Path(__file__).parent / "templates" / name
    html = path.read_text(encoding="utf-8")
    for key, value in ctx.items():
        html = html.replace("{{" + key + "}}", str(value))
    return HTMLResponse(html)

@app.get("/login", response_class=HTMLResponse)
def login():
    return render("login.html", error="")

@app.post("/login")
def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == settings.demo_username and password == settings.demo_password:
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    return render("login.html", error="Invalid demo credentials")

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    rows = repo.list_invoices()
    return render("dashboard.html", total=len(rows), pending=sum(r["status"]=="PENDING" for r in rows), approved=sum(r["status"]=="APPROVED" for r in rows), duplicates=sum("duplicate" in (r["status"] or "").lower() for r in rows), failures=0)

@app.get("/invoices", response_class=HTMLResponse)
def invoices(request: Request, vendor: str = "", invoice_number: str = ""):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    rows = repo.list_invoices(vendor or None)
    if invoice_number:
        rows = [r for r in rows if r["invoice_number"].lower() == invoice_number.lower()]
    trs = "".join(f"<tr><td>{r['id']}</td><td>{r['vendor_name']}</td><td>{r['invoice_number']}</td><td>{r['invoice_date']}</td><td>{r['due_date'] or ''}</td><td>{r['total_amount'] or ''}</td><td>{r['status']}</td></tr>" for r in rows)
    return render("invoices.html", vendor=vendor, invoice_number=invoice_number, rows=trs)

@app.get("/invoices/new", response_class=HTMLResponse)
def new_invoice(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    return render("new_invoice.html", error="", error_display="none", created_id="")

@app.post("/invoices/new", response_class=HTMLResponse)
def create_from_ui(request: Request,
                   vendor: str = Form(...), invoice_number: str = Form(...), invoice_date: str = Form(...),
                   due_date: str = Form(""), subtotal: str = Form(""), tax: str = Form(""),
                   total_amount: str = Form(""), payment_terms: str = Form(""), task_id: str = Form("")):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    if task_id:
        DRAFTS[task_id] = {"vendor": vendor, "invoice_number": invoice_number, "invoice_date": invoice_date, "due_date": due_date, "subtotal": subtotal, "tax": tax, "total_amount": total_amount, "payment_terms": payment_terms}
    return render("new_invoice.html", error="", error_display="none", created_id="")


@app.post("/invoices/submit", response_class=HTMLResponse)
def submit_from_ui(request: Request,
                   vendor: str = Form(...), invoice_number: str = Form(...), invoice_date: str = Form(...),
                   due_date: str = Form(""), subtotal: str = Form(""), tax: str = Form(""),
                   total_amount: str = Form(""), payment_terms: str = Form(""), task_id: str = Form("")):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    if task_id:
        DRAFTS[task_id] = {"vendor": vendor, "invoice_number": invoice_number, "invoice_date": invoice_date, "due_date": due_date, "subtotal": subtotal, "tax": tax, "total_amount": total_amount, "payment_terms": payment_terms}
        result = api_submit({"task_id": task_id, "allow_failure": True})
        if result.get("success"):
            return render("new_invoice.html", error="", error_display="none", created_id=result["invoice_id"])
        return render("new_invoice.html", error=result.get("message", "Submit failed"), error_display="block", created_id="")
    return render("new_invoice.html", error="Missing worker task id", error_display="block", created_id="")

@app.post("/api/drafts")
def save_draft(payload: dict):
    DRAFTS[payload["task_id"]] = payload
    return {"ok": True}

@app.get("/api/drafts/{task_id}")
def get_draft(task_id: str):
    return DRAFTS.get(task_id, {})

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/invoices/submit")
def api_submit(payload: dict):
    task_id = payload["task_id"]
    draft = DRAFTS.get(task_id)
    if not draft:
        return {"success": False, "error_type": "VALIDATION", "message": "No staged draft"}
    SUBMIT_ATTEMPTS[task_id] = SUBMIT_ATTEMPTS.get(task_id, 0) + 1
    if settings.simulate_transient_failures and payload.get("allow_failure", True) and SUBMIT_ATTEMPTS[task_id] == 1:
        return {"success": False, "error_type": "TRANSIENT", "message": "Temporary AP save failure (simulated 503)."}
    try:
        existing = repo.find_invoice_by_number_vendor(draft["vendor"], draft["invoice_number"])
        if existing:
            return {"success": False, "error_type": "DUPLICATE", "message": "Duplicate invoice detected at submission boundary."}
        invoice_id = repo.create_invoice({
            "vendor_name": draft["vendor"], "invoice_number": draft["invoice_number"], "invoice_date": draft["invoice_date"],
            "due_date": draft["due_date"] or None, "subtotal": float(draft["subtotal"] or 0), "tax": float(draft["tax"] or 0),
            "total_amount": float(draft["total_amount"] or 0), "payment_terms": draft["payment_terms"],
        })
        return {"success": True, "invoice_id": invoice_id}
    except Exception as exc:
        return {"success": False, "error_type": "PERMANENT", "message": str(exc)}

@app.get("/invoices/{invoice_id}", response_class=HTMLResponse)
def invoice_detail(request: Request, invoice_id: int):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    row = repo.get_invoice(invoice_id)
    if not row:
        return HTMLResponse("Not found", status_code=404)
    return render("invoice_detail.html", vendor=row["vendor_name"], invoice_number=row["invoice_number"], invoice_date=row["invoice_date"], due_date=row["due_date"] or "", total=row["total_amount"] or 0, status=row["status"], invoice_id=row["id"])
