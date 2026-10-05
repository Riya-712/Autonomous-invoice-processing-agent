import json
from datetime import date
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from app.config import INVOICE_DIR, SEED_DIR, POLICY_DIR
from app.db.database import init_db, DB_PATH
from app.db import repositories as repo

VENDORS = [
    {"id":1,"vendor_name":"Acme Corporation","vendor_code":"ACM001","tax_id":"GSTIN27ACME1234Z1","address":"12 Industrial Estate, Pune, Maharashtra","default_payment_terms":"Net 30"},
    {"id":2,"vendor_name":"XYZ Components Pvt Ltd","vendor_code":"XYZ002","tax_id":"GSTIN27XYZC5678P2","address":"44 MIDC Road, Nashik, Maharashtra","default_payment_terms":"Net 45"},
    {"id":3,"vendor_name":"Reliance Industrial Services","vendor_code":"RIS003","tax_id":"GSTIN27REL9876Q3","address":"8 Business Park, Mumbai, Maharashtra","default_payment_terms":"Net 30"},
    {"id":4,"vendor_name":"Nova Technologies","vendor_code":"NOV004","tax_id":"GSTIN29NOVA4321R4","address":"21 Tech Hub, Bengaluru, Karnataka","default_payment_terms":"Net 15"},
    {"id":5,"vendor_name":"ABC Office Supplies","vendor_code":"ABC005","tax_id":"GSTIN27ABCO2468S5","address":"6 Market Lane, Pune, Maharashtra","default_payment_terms":"Net 30"},
]

INVOICES = [
    (1,"ACME-2026-101","2026-08-05", "2026-09-04", 60000, 10800, 70800, "Net 30", "normal"),
    (1,"ACME-2026-102","2026-09-05", "2026-10-05", 72000, 12960, 84960, "Net 30", "normal"),
    (1,"ACME-2026-103","2026-09-20", "2026-10-20", 90000, 16200, 106200, "Net 30", "approval"),
    (1,"ACME-2026-104","2026-10-01", "2026-10-31", 75000, 13500, 88500, "Net 30", "normal"),
    (1,"ACME-2026-105","2026-10-02", None, 68000, 12240, 80240, "Net 30", "missing_due"),
    (2,"XYZ-2026-201","2026-08-10", "2026-09-24", 50000, 9000, 59000, "Net 45", "normal"),
    (2,"XYZ-2026-202","2026-09-11", "2026-10-26", 82000, 14760, 96760, "Net 45", "normal"),
    (2,"XYZ-2026-203","2026-10-03", "2026-11-17", 125000, 22500, 147500, "Net 45", "approval"),
    (3,"RIS-2026-301","2026-08-12", "2026-09-11", 62000, 11160, 73160, "Net 30", "normal"),
    (3,"RIS-2026-302","2026-09-18", "2026-10-18", 77000, 13860, 90860, "Net 30", "normal"),
    (3,"RIS-2026-303","2026-10-02", "2026-11-01", 94000, 16920, 110920, "Net 30", "normal"),
    (4,"NOVA-2026-401","2026-08-15", "2026-08-30", 25000, 4500, 29500, "Net 15", "normal"),
    (4,"NOVA-2026-402","2026-09-19", "2026-10-04", 88000, 15840, 103840, "Net 15", "approval"),
    (4,"NOVA-2026-403","2026-10-01", "2026-10-16", 40000, 7200, 47200, "Net 15", "normal"),
    (5,"ABC-2026-501","2026-08-21", "2026-09-20", 30000, 5400, 35400, "Net 30", "normal"),
    (5,"ABC-2026-502","2026-09-14", "2026-10-14", 42000, 7560, 49560, "Net 30", "normal"),
    (5,"ABC-2026-503","2026-10-02", "2026-11-01", 58000, 10440, 68440, "Net 30", "normal"),
    (1,"ACME-2026-104-DUP","2026-10-01", "2026-10-31", 75000, 13500, 88500, "Net 30", "duplicate"),
    (3,"RIS-2026-CONFLICT","2026-10-03", "2026-11-02", 82000, 14760, 96760, "Net 30", "conflict"),
    (2,"XYZ-2026-204","2026-10-04", "2026-11-18", 61000, 10980, 71980, "Net 45", "normal"),
]

def draw_invoice(path: Path, vendor: dict, inv: tuple):
    _, number, inv_date, due_date, subtotal, tax, total, terms, scenario = inv
    c = canvas.Canvas(str(path), pagesize=A4)
    w,h=A4
    c.setFont("Helvetica-Bold", 18); c.drawString(50,h-60,"INVOICE")
    c.setFont("Helvetica",10)
    c.drawString(50,h-90,f"Vendor: {vendor['vendor_name']}")
    c.drawString(50,h-106,f"Vendor Tax ID: {vendor['tax_id']}")
    c.drawString(50,h-122,f"Address: {vendor['address']}")
    c.drawString(360,h-90,f"Invoice Number: {number}")
    c.drawString(360,h-106,f"Invoice Date: {inv_date}")
    if due_date:
        c.drawString(360,h-122,f"Due Date: {due_date}")
    elif scenario == "missing_due":
        c.drawString(360,h-122,"Due Date: ")
    c.line(50,h-140,545,h-140)
    c.drawString(60,h-170,"Line Items")
    c.drawString(60,h-195,"Enterprise services / materials")
    c.drawRightString(540,h-195,f"₹{subtotal:,.2f}")
    c.drawString(60,h-225,"Subtotal:"); c.drawRightString(540,h-225,f"₹{subtotal:,.2f}")
    c.drawString(60,h-245,"Tax:"); c.drawRightString(540,h-245,f"₹{tax:,.2f}")
    c.setFont("Helvetica-Bold",11); c.drawString(60,h-275,"Total Amount:"); c.drawRightString(540,h-275,f"₹{total:,.2f}")
    c.setFont("Helvetica",10); c.drawString(60,h-310,f"Payment Terms: {terms}")
    if scenario == "conflict":
        c.drawString(60,h-345,"Reference Note: Vendor portal total differs from AP record; review required.")
    c.drawString(50,80,"Synthetic document generated for CentrAlign AI technical evaluation.")
    c.save()

def draw_policy(path: Path, title: str, lines: list[str]):
    c = canvas.Canvas(str(path), pagesize=A4); w,h=A4
    y=h-60
    c.setFont("Helvetica-Bold",16); c.drawString(50,y,title); y-=30
    c.setFont("Helvetica",10)
    for line in lines:
        for chunk in [line[i:i+95] for i in range(0,len(line),95)] or [""]:
            c.drawString(50,y,chunk); y-=16
            if y<70:
                c.showPage(); y=h-60; c.setFont("Helvetica",10)
    c.save()

def main():
    init_db()
    if DB_PATH.exists(): DB_PATH.unlink(); init_db()
    for v in VENDORS: repo.upsert_vendor(v)
    for p in INVOICE_DIR.glob("*.pdf"): p.unlink()
    manifest=[]
    for v_id,num,inv_date,due_date,subtotal,tax,total,terms,scenario in INVOICES:
        vendor=next(v for v in VENDORS if v["id"]==v_id)
        filename=f"{num}.pdf"; path=INVOICE_DIR/filename
        draw_invoice(path,vendor,(v_id,num,inv_date,due_date,subtotal,tax,total,terms,scenario))
        manifest.append({"vendor":vendor["vendor_name"],"invoice_number":num,"invoice_date":inv_date,"due_date":due_date,"subtotal":subtotal,"tax":tax,"total_amount":total,"payment_terms":terms,"scenario":scenario,"file":str(path)})
        # seed the explicit duplicate/conflict records only below
    repo.insert_invoice({"id":1001,"vendor_id":1,"invoice_number":"ACME-2026-104","invoice_date":"2026-10-01","due_date":"2026-10-31","subtotal":75000,"tax":13500,"total_amount":88500,"payment_terms":"Net 30","status":"APPROVED","source_file":"existing://ap/1001"})
    repo.insert_invoice({"id":1002,"vendor_id":3,"invoice_number":"RIS-2026-CONFLICT","invoice_date":"2026-10-03","due_date":"2026-11-02","subtotal":90000,"tax":16200,"total_amount":106200,"payment_terms":"Net 30","status":"PENDING","source_file":"existing://ap/1002"})
    draw_policy(POLICY_DIR/"ap_policy.pdf","Accounts Payable Processing Policy",[
        "Required fields: vendor, invoice number, invoice date and total amount are mandatory.",
        "Due date may be derived only when vendor master payment terms are unambiguous; derivation must be logged.",
        "Amounts must be non-negative and internally consistent with subtotal plus tax.",
        "Critical missing fields that cannot be safely derived require human review.",
    ])
    draw_policy(POLICY_DIR/"approval_matrix.pdf","Approval Matrix",[
        "Invoices at or below INR 100000 may be submitted autonomously when all validation checks pass.",
        "Invoices above INR 100000 and up to INR 500000 require Finance Manager approval.",
        "Invoices above INR 500000 require Finance Controller approval.",
        "The worker must pause before a policy-controlled action and resume only after approval.",
    ])
    draw_policy(POLICY_DIR/"duplicate_invoice_policy.pdf","Duplicate Invoice Policy",[
        "Exact duplicate: same vendor and invoice number. Do not create another record.",
        "Potential duplicate: same vendor, invoice date and total amount. Escalate for review.",
        "Conflicting existing record: same vendor and invoice number but material field mismatch. Stop and escalate.",
    ])
    draw_policy(POLICY_DIR/"exception_handling_policy.pdf","Exception Handling Policy",[
        "Transient application failures may be retried at most two times with bounded backoff.",
        "Permanent validation failures must not be blindly retried.",
        "Do not retry duplicate creation, policy violations or approval requirements.",
        "All worker actions and outcomes must be captured in an execution trace.",
    ])
    (SEED_DIR/"invoices.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    (SEED_DIR/"scenarios.json").write_text(json.dumps({
        "happy_path":{"task":"Find the latest invoice from Acme Corporation and process it.","expected":"ACME-2026-105 is newest but missing due date; human review after safe derivation attempt"},
        "duplicate":{"task":"Find invoice ACME-2026-104 from Acme Corporation and process it.","expected":"duplicate protection blocks creation"},
        "approval":{"task":"Process the latest invoice from XYZ Components Pvt Ltd.","expected":"approval required because amount exceeds INR 100000"},
        "conflict":{"task":"Process invoice RIS-2026-CONFLICT from Reliance Industrial Services.","expected":"conflict detected; approval required"},
        "transient":{"task":"Process the latest invoice from ABC Office Supplies.","expected":"first submit fails transiently; retry succeeds and verifies"}
    },indent=2),encoding="utf-8")
    print("Generated invoices, policies and seeded AP database.")

if __name__ == "__main__": main()
