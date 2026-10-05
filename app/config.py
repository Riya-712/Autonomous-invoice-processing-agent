from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
INVOICE_DIR = DATA_DIR / "invoices"
POLICY_DIR = DATA_DIR / "policies"
SEED_DIR = DATA_DIR / "seed"
RUNTIME_DIR = DATA_DIR / "runtime"
RUN_DIR = ROOT_DIR / "runs"
SCREENSHOT_DIR = RUN_DIR / "screenshots"

for path in (INVOICE_DIR, POLICY_DIR, SEED_DIR, RUNTIME_DIR, SCREENSHOT_DIR):
    path.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-120b"
    llm_temperature: float = 0.0
    ap_base_url: str = "http://127.0.0.1:8000"
    database_url: str = f"sqlite:///{RUNTIME_DIR / 'centralign_ap.db'}"
    max_retries: int = 2
    approval_threshold: float = 100000.0
    worker_max_steps: int = 20
    simulate_transient_failures: bool = True
    demo_username: str = "operator"
    demo_password: str = "operator123"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
