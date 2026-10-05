import json
from app.config import settings
from app.models.state import WorkerState
from app.tools.base import Tool

SYSTEM_PROMPT = """
You are the decision layer of an enterprise accounts-payable AI worker.
Your job is NOT to chat. Choose the single safest next tool action needed to accomplish the user's objective.
Never invent financial values. Never bypass policy. Never create an invoice before duplicate and policy checks pass.
After a tool result, use the observed environment state rather than assuming success.
Critical write actions are controlled by the host application; if state is incomplete, choose a read/check tool.
Return exactly one tool call when another action is appropriate. Do not provide a prose final answer until the host marks the task complete.
"""

class LLMPlanner:
    def __init__(self, tools: dict[str, Tool]):
        self.tools=tools
        self.client=None
        if settings.llm_api_key:
            from openai import OpenAI
            self.client=OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    def choose(self, state: WorkerState, allowed_tools: list[str]) -> tuple[str | None, dict, str]:
        if not self.client:
            return self._fallback(state, allowed_tools)
        tools=[self.tools[name].openai_definition() for name in allowed_tools if name in self.tools]
        context={
            "task":state.user_task,
            "vendor":state.vendor,
            "candidate_files":state.candidate_files,
            "selected_invoice_file":state.selected_invoice_file,
            "extracted":state.extracted.model_dump(mode="json") if state.extracted else None,
            "duplicate_status":state.duplicate_status,
            "policy_status":state.policy_status,
            "approval_status":state.approval_status,
            "ap_record_id":state.ap_record_id,
            "verification_status":state.verification_status,
            "last_observation":state.last_observation,
        }
        messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":json.dumps(context,default=str)}]
        try:
            response=self.client.chat.completions.create(model=settings.llm_model,messages=messages,tools=tools,tool_choice="auto",temperature=settings.llm_temperature)
            msg=response.choices[0].message
            if msg.tool_calls:
                call=msg.tool_calls[0]
                return call.function.name, json.loads(call.function.arguments or "{}"), "llm"
            return self._fallback(state, allowed_tools, "LLM returned no tool call")
        except Exception as exc:
            return self._fallback(state, allowed_tools, f"LLM unavailable: {exc}")

    def _fallback(self,state,allowed_tools,reason="deterministic fallback"):
        if state.vendor is None:
            # Task normalization is intentionally simple and safe: pull the phrase after 'from'.
            text=state.user_task
            low=text.lower()
            marker="from "
            if marker in low:
                vendor=text[low.index(marker)+len(marker):].split(" and ")[0].split(" process")[0].strip(" .")
                state.vendor=vendor
        if "search_invoice_files" in allowed_tools and not state.candidate_files:
            return "search_invoice_files", {"vendor":state.vendor or "Acme Corporation"}, reason
        if "select_latest_invoice" in allowed_tools and state.candidate_files and not state.selected_invoice_file:
            return "select_latest_invoice", {"files":state.candidate_files}, reason
        if "read_invoice" in allowed_tools and state.selected_invoice_file and state.document_text is None:
            return "read_invoice", {"file_path":state.selected_invoice_file}, reason
        if "extract_invoice_data" in allowed_tools and state.document_text:
            return "extract_invoice_data", {"document_text":state.document_text}, reason
        if "lookup_vendor_payment_terms" in allowed_tools and state.extracted and not state.extracted.due_date:
            return "lookup_vendor_payment_terms", {"vendor":state.extracted.vendor_name}, reason
        if "compute_due_date_from_terms" in allowed_tools and state.extracted and not state.extracted.due_date and state.last_observation:
            terms=state.last_observation.get("data",{}).get("default_payment_terms")
            if terms and state.extracted.invoice_date:
                return "compute_due_date_from_terms", {"invoice_date":state.extracted.invoice_date.isoformat(),"payment_terms":terms}, reason
        if "check_duplicate_invoice" in allowed_tools and state.extracted and state.duplicate_status=="unknown":
            return "check_duplicate_invoice", {"invoice_data":state.extracted.model_dump(mode="json")}, reason
        if "check_policy" in allowed_tools and state.extraction_meta and state.policy_status=="not_checked":
            return "check_policy", {}, reason
        if "create_ap_invoice" in allowed_tools and state.extracted:
            return "create_ap_invoice", {}, reason
        if "submit_invoice" in allowed_tools and state.draft_staged:
            return "submit_invoice", {}, reason
        return None, {}, reason
