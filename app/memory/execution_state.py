import json
from pathlib import Path
from app.config import RUNTIME_DIR
from app.models.state import WorkerState

class StateStore:
    def __init__(self, task_id: str):
        self.path = Path(RUNTIME_DIR) / f"state_{task_id}.json"

    def save(self, state: WorkerState) -> None:
        self.path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def load(self) -> WorkerState:
        return WorkerState.model_validate_json(self.path.read_text(encoding="utf-8"))
