import time
from app.config import settings

def backoff_seconds(attempt_number: int) -> float:
    return min(2 ** max(attempt_number - 1, 0), 4)

def should_retry(error_type: str | None, attempt_number: int) -> bool:
    return error_type == "TRANSIENT" and attempt_number < settings.max_retries

def wait_before_retry(attempt_number: int) -> None:
    time.sleep(backoff_seconds(attempt_number))
