from datetime import date

from app.agent.worker import AutonomousAPWorker
from app.models.invoice import ExtractionResult, InvoiceData
from app.models.state import WorkerState
from app.tools.tool_registry import build_registry


def test_policy_check_uses_validated_worker_state_when_llm_arguments_are_flat():
    invoice = InvoiceData(
        vendor_name="Acme Corporation",
        invoice_number="A-1",
        invoice_date=date(2026, 10, 1),
        due_date=date(2026, 10, 31),
        total_amount=50000,
    )
    worker = object.__new__(AutonomousAPWorker)
    worker.state = WorkerState(
        task_id="test-task",
        user_task="Process the invoice.",
        extracted=invoice,
        extraction_meta=ExtractionResult(invoice=invoice),
        duplicate_status="NO_MATCH",
    )
    worker.registry = build_registry()

    result = worker._execute(
        "check_policy",
        {
            "extraction": invoice.model_dump(mode="json"),
            "duplicate_status": "EXACT_DUPLICATE",
        },
    )

    assert result.success
    assert result.data["decision"]["allowed"] is True
