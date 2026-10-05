from pathlib import Path
from pypdf import PdfReader
from app.config import POLICY_DIR

def load_policy_text() -> str:
    texts = []
    for path in sorted(Path(POLICY_DIR).glob("*.pdf")):
        reader = PdfReader(str(path))
        texts.append(f"\n--- {path.name} ---\n" + "\n".join(page.extract_text() or "" for page in reader.pages))
    return "\n".join(texts)
