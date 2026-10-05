from unittest import result
import json, uuid
from datetime import datetime, timezone
from app.models.state import WorkerState, ActionEvent
from app.models.invoice import InvoiceData, ExtractionResult
from app.models.tool_result import ToolResult
from app.agent.planner import LLMPlanner
from app.tools.tool_registry import build_registry
from app.tools.browser_tools import create_ap_invoice, submit_invoice, verify_invoice
from app.recovery.retry_handler import should_retry, wait_before_retry
from app.tracing.execution_trace import TraceLogger
from app.memory.execution_state import StateStore
from app.db import repositories as repo
from app.config import settings

WRITE_TOOLS = {"create_ap_invoice", "submit_invoice"}

class AutonomousAPWorker:
    def __init__(self, state: WorkerState | None = None):
        self.state=state
        self.registry=build_registry()
        self.planner=LLMPlanner(self.registry)
        self.trace=TraceLogger(state.task_id if state else str(uuid.uuid4()))
        self.store=StateStore(self.trace.task_id)

    def _set_time(self):
        now=datetime.now(timezone.utc).isoformat()
        if not self.state.created_at: self.state.created_at=now
        self.state.updated_at=now

    def _event(self, event_type, status, tool=None, details=None):
        self._set_time()
        ev=self.trace.add(event_type,status,tool,details)
        self.state.action_history.append(ActionEvent(**ev))
        self.store.save(self.state)
        self.trace.persist(self.state)

    def start(self, task: str) -> WorkerState:
        task_id=str(uuid.uuid4())
        self.state=WorkerState(task_id=task_id,user_task=task,status="RUNNING")
        self.trace=TraceLogger(task_id); self.store=StateStore(task_id)
        repo.create_worker_run(task_id)
        self._event("TASK_RECEIVED","ok",details={"task":task})
        return self.run_until_pause()

    def resume(self, approved: bool, decided_by: str = "human") -> WorkerState:
        if self.state is None:
            self.state=self.store.load()
        else:
            self.trace=TraceLogger(self.state.task_id)
            self.trace.events=[event.model_dump(mode="json") for event in self.state.action_history]
            self.store=StateStore(self.state.task_id)
        self.state.approval_status="approved" if approved else "denied"
        repo.save_approval(self.state.task_id,self.state.approval_status,self.state.approval_reason or "Human approval",decided_by)
        self._event("HUMAN_APPROVAL","approved" if approved else "denied",details={"decided_by":decided_by})
        if not approved:
            self.state.status="FAILED"; self.state.completed=False; self.state.failure_reason="Human approval denied"; repo.finish_worker_run(self.state.task_id,"FAILED")
            self.trace.persist(self.state); self.store.save(self.state); return self.state
        if self.state.duplicate_status in {"EXACT_DUPLICATE","POTENTIAL_DUPLICATE","CONFLICTING_EXISTING_RECORD"}:
            self.state.status="FAILED"; self.state.failure_reason="Human approval cannot override duplicate/conflict protection."; repo.finish_worker_run(self.state.task_id,"FAILED"); self._event("SAFE_STOP","failed",details={"reason":self.state.failure_reason}); self.store.save(self.state); return self.state
        if self.state.extracted is not None and self.state.extracted.invoice_number and self.state.extracted.invoice_date and self.state.extracted.total_amount is not None:
            self.state.policy_status="allowed"
            self.state.approval_required=False
            self.state.status="RUNNING"
            return self.run_until_pause()
        self.state.status="FAILED"; self.state.failure_reason="Approval was granted, but required invoice data is still incomplete."; repo.finish_worker_run(self.state.task_id,"FAILED"); self.store.save(self.state); return self.state

    def _allowed_tools(self) -> list[str]:
        s=self.state
        allowed=[]
        if not s.candidate_files: allowed.append("search_invoice_files")
        elif not s.selected_invoice_file: allowed.append("select_latest_invoice")
        elif not s.document_text: allowed.append("read_invoice")
        elif not s.extracted: allowed.append("extract_invoice_data")
        elif not s.extracted.due_date and s.extracted.invoice_date: allowed.extend(["lookup_vendor_payment_terms","compute_due_date_from_terms"])
        elif s.duplicate_status=="unknown": allowed.append("check_duplicate_invoice")
        elif s.policy_status=="not_checked": allowed.append("check_policy")
        if s.ap_record_id is None and s.policy_status=="allowed" and not s.approval_required and not s.draft_staged:
            allowed.append("create_ap_invoice")
        elif s.ap_record_id is None and s.policy_status=="allowed" and not s.approval_required and s.draft_staged:
            allowed.append("submit_invoice")
        if s.ap_record_id is not None and s.verification_status=="pending": allowed.append("verify_invoice")
        return list(dict.fromkeys(allowed))

    def _execute(self, name: str, args: dict) -> ToolResult:
        if name=="extract_invoice_data": return self.registry[name].handler(**args)
        if name=="check_duplicate_invoice":
            inv=InvoiceData.model_validate(args["invoice_data"]); return self.registry[name].handler(inv)
        if name=="check_policy":
            if self.state.extraction_meta is None:
                return ToolResult(
                    success=False,
                    tool_name=name,
                    observation="Policy check requires validated invoice extraction data.",
                    error_type="VALIDATION",
                    retryable=False,
                )
            return self.registry[name].handler(self.state.extraction_meta,self.state.duplicate_status)
        if name=="create_ap_invoice":
            if not self.state.extracted:
                return ToolResult(
                    success=False,
                    tool_name=name,
                    observation="No extracted invoice available.",
                    error_type="VALIDATION",
                    retryable=False,
                )
            # Stage form data in the simulated AP server so a later submit call is independently executed.
            import requests
            payload={"task_id":self.state.task_id,"vendor":self.state.extracted.vendor_name,"invoice_number":self.state.extracted.invoice_number,"invoice_date":self.state.extracted.invoice_date.isoformat() if self.state.extracted.invoice_date else None,"due_date":self.state.extracted.due_date.isoformat() if self.state.extracted.due_date else None,"subtotal":self.state.extracted.subtotal,"tax":self.state.extracted.tax,"total_amount":self.state.extracted.total_amount,"payment_terms":self.state.extracted.payment_terms}
            try:
                r=requests.post(f"{settings.ap_base_url}/api/drafts",json=payload,timeout=10); r.raise_for_status()
            except Exception as exc:
                return ToolResult(
                    success=False,
                    tool_name=name,
                    observation=f"Could not stage browser task draft: {exc}",
                    error_type="TRANSIENT",
                    retryable=True,
                )
            return create_ap_invoice(self.state.extracted, self.state.task_id)
        if name=="submit_invoice":
            # Use browser to click submit; before doing so ensure current form fields are staged server-side.
            import requests
            try:
                r=requests.post(f"{settings.ap_base_url}/api/invoices/submit",json={"task_id":self.state.task_id,"allow_failure":True},timeout=10)
                data=r.json()
            except Exception as exc:
                return ToolResult(
                    success=False,
                    tool_name=name,
                    observation=f"Submit API unavailable: {exc}",
                    error_type="TRANSIENT",
                    retryable=True,
                )
            if data.get("success"):
                # Open detail page via browser as evidence of actual UI persistence.
                return ToolResult(
                    success=True,
                    tool_name=name,
                    observation=f"Invoice submitted successfully with record ID {data['invoice_id']}.",
                    data={"invoice_id":data["invoice_id"]},
                )
            return ToolResult(
                success=False,
                tool_name=name,
                observation=data.get("message","Submit failed"),
                error_type=data.get("error_type","PERMANENT"),
                retryable=data.get("error_type")=="TRANSIENT",
            )
        if name=="verify_invoice":
            if self.state.ap_record_id is None or self.state.extracted is None:
                return ToolResult(
                    success=False,
                    tool_name=name,
                    observation="Verification preconditions not met.",
                    error_type="VALIDATION",
                    retryable=False,
                )
            return verify_invoice(self.state.ap_record_id,self.state.extracted)
        return self.registry[name].handler(**args)

    def _apply_result(self, result: ToolResult):
        self.state.last_observation=result.model_dump(mode="json")
        if result.tool_name=="search_invoice_files" and result.success:
            self.state.candidate_files=result.data["files"]
        elif result.tool_name=="select_latest_invoice" and result.success:
            self.state.selected_invoice_file=result.data["file_path"]
        elif result.tool_name=="read_invoice" and result.success:
            self.state.document_text=result.data.get("text")
        elif result.tool_name=="extract_invoice_data" and result.success:
            ext=ExtractionResult.model_validate(result.data["extraction"])
            self.state.extraction_meta=ext; self.state.extracted=ext.invoice
            self.state.vendor=ext.invoice.vendor_name
        elif result.tool_name=="lookup_vendor_payment_terms" and result.success:
            pass
        elif result.tool_name=="compute_due_date_from_terms" and result.success and self.state.extracted:
            self.state.extracted.due_date=__import__("datetime").date.fromisoformat(result.data["due_date"])
            self.state.extracted.payment_terms=result.data["basis"]
            if self.state.extraction_meta: self.state.extraction_meta.invoice=self.state.extracted; self.state.extraction_meta.missing_fields=[x for x in self.state.extraction_meta.missing_fields if x!="due_date"]; self.state.extraction_meta.derivations.append(f"due_date derived from {result.data['basis']}")
        elif result.tool_name=="check_duplicate_invoice" and result.success:
            self.state.duplicate_status=result.data["status"]
        elif result.tool_name=="check_policy" and result.success:
            decision=result.data["decision"]; self.state.policy_status="allowed" if decision["allowed"] else "blocked"; self.state.policy_reason=decision["reason"]
            self.state.approval_required=decision["approval_required"]; self.state.approval_reason=decision["reason"] + " " + decision["policy_rule"]
            if not decision["approval_required"]: self.state.approval_status="not_required"
        elif result.tool_name=="create_ap_invoice" and result.success:
            self.state.draft_staged=True
        elif result.tool_name=="submit_invoice" and result.success:
            self.state.ap_record_id=int(result.data["invoice_id"])
            self.state.draft_staged=False
        elif result.tool_name=="verify_invoice":
            self.state.verification_status="passed" if result.success else "failed"
            self.state.verification_evidence=result.data

    def run_until_pause(self) -> WorkerState:
        if self.state is None: raise RuntimeError("Worker state not initialized")
        while self.state.step_count < settings.worker_max_steps:
            self.state.step_count += 1
            self._event(
                "OBSERVE",
                "ok",
                details={
                    "step_count": self.state.step_count,
                    "status": self.state.status,
                    "vendor": self.state.vendor,
                    "selected_invoice_file": self.state.selected_invoice_file,
                    "duplicate_status": self.state.duplicate_status,
                    "policy_status": self.state.policy_status,
                    "approval_status": self.state.approval_status,
                    "ap_record_id": self.state.ap_record_id,
                },
            )
            # Safety gate before any write: policy blocked means approval is mandatory.
            if self.state.policy_status=="blocked" and self.state.approval_required and self.state.approval_status=="not_required":
                self.state.status="WAITING_FOR_APPROVAL"; self._event("HUMAN_APPROVAL_REQUIRED","pending",details={"reason":self.state.approval_reason})
                self.trace.persist(self.state); self.store.save(self.state); return self.state
            if self.state.policy_status=="blocked" and self.state.approval_required and self.state.approval_status=="approved" and self.state.duplicate_status in {"EXACT_DUPLICATE","POTENTIAL_DUPLICATE","CONFLICTING_EXISTING_RECORD"}:
                self.state.status="FAILED"; self.state.failure_reason="Policy requires human review before duplicate/conflict creation; approval does not override duplicate protection."; repo.finish_worker_run(self.state.task_id,"FAILED"); self._event("SAFE_STOP","failed",details={"reason":self.state.failure_reason}); return self.state
            if self.state.ap_record_id is not None and self.state.verification_status=="passed":
                self.state.status="COMPLETED"; self.state.completed=True; repo.finish_worker_run(self.state.task_id,"COMPLETED"); self._event("TASK_COMPLETED","ok",details=self.state.verification_evidence); return self.state
            allowed=self._allowed_tools()
            # Verification is host-enforced, never delegated to an LLM after submission.
            if self.state.ap_record_id is not None and self.state.verification_status=="pending":
                name,args,mode="verify_invoice",{},"host"
            else:
                name,args,mode=self.planner.choose(self.state,allowed)
            if not name:
                if self.state.extracted and self.state.extracted.due_date is None:
                    self.state.status="WAITING_FOR_APPROVAL"; self.state.approval_required=True; self.state.approval_status="pending"; self.state.approval_reason="Due date remains unresolved after safe derivation attempt."; self._event("HUMAN_APPROVAL_REQUIRED","pending",details={"reason":self.state.approval_reason}); return self.state
                self.state.status="FAILED"; self.state.failure_reason="No safe next action available."; repo.finish_worker_run(self.state.task_id,"FAILED"); self._event("SAFE_STOP","failed",details={"reason":self.state.failure_reason}); return self.state
            self._event("DECISION","ok",tool=name,details={"mode":mode,"arguments":args})
            if name in WRITE_TOOLS and (self.state.policy_status!="allowed" or (self.state.approval_required and self.state.approval_status!="approved")):
                self.state.status="FAILED"; self.state.failure_reason="Write action rejected by host safety gate."; self._event("SAFETY_BLOCK","failed",tool=name,details={"reason":self.state.failure_reason}); return self.state
            attempt=0
            while True:
                attempt+=1
                result=self._execute(name,args)
                print(f"\n[DEBUG] TOOL: {name}")
                print(f"[DEBUG] SUCCESS: {result.success}")
                print(f"[DEBUG] OBSERVATION: {result.observation}")
                print(f"[DEBUG] DATA: {result.data}\n")
                repo.log_attempt(self.state.task_id,self.state.ap_record_id,name,"success" if result.success else "failed",result.error_type,None if result.success else result.observation,attempt)
                self._event("TOOL_RESULT","success" if result.success else "failed",tool=name,details=result.model_dump(mode="json"))
                if result.success:
                    self._apply_result(result); self.store.save(self.state); break
                if should_retry(result.error_type,attempt):
                    self.state.retry_count += 1
                    self._event("RETRY","retrying",tool=name,details={"attempt":attempt+1,"error_type":result.error_type})
                    wait_before_retry(attempt)
                    continue
                if result.error_type in {"DUPLICATE","POLICY","AMBIGUITY","AUTHORIZATION","VALIDATION"}:
                    self.state.status="WAITING_FOR_APPROVAL"; self.state.approval_required=True; self.state.approval_status="pending"; self.state.approval_reason=result.observation; self._event("HUMAN_APPROVAL_REQUIRED","pending",tool=name,details={"reason":result.observation}); self.store.save(self.state); return self.state
                self.state.status="FAILED"; self.state.failure_reason=result.observation; repo.finish_worker_run(self.state.task_id,"FAILED"); self.store.save(self.state); return self.state
            self.store.save(self.state)
        self.state.status="FAILED"; self.state.failure_reason="Maximum worker steps exceeded."; repo.finish_worker_run(self.state.task_id,"FAILED"); self.trace.persist(self.state); self.store.save(self.state); return self.state
