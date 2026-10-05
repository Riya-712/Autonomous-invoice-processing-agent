import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from app.config import RUN_DIR
from app.models.state import WorkerState, ActionEvent

class TraceLogger:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.events: list[dict[str, Any]] = []

    def add(self, event_type: str, status: str, tool: str | None = None, details: dict[str, Any] | None = None):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "tool": tool,
            "status": status,
            "details": details or {},
        }
        self.events.append(event)
        return event

    def persist(self, state: WorkerState):
        out = RUN_DIR / f"run_{self.task_id}.json"
        payload = {
            "task_id": self.task_id,
            "events": self.events,
            "state": state.model_dump(mode="json"),
        }
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return out
