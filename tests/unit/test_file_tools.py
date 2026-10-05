from pathlib import Path

from app.tools import file_tools


def test_search_invoice_files_returns_all_matches(tmp_path, monkeypatch):
    invoice_paths = [tmp_path / "invoice-1.pdf", tmp_path / "invoice-2.pdf", tmp_path / "other.pdf"]
    for path in invoice_paths:
        path.touch()

    monkeypatch.setattr(file_tools, "INVOICE_DIR", tmp_path)
    monkeypatch.setattr(
        file_tools,
        "read_pdf_text",
        lambda path: (
            "Acme Corporation invoice"
            if Path(path).name.startswith("invoice-")
            else "Different vendor"
        ),
    )

    result = file_tools.search_invoice_files("Acme Corporation")

    assert result.success
    assert result.observation == "Found 2 invoice candidates for Acme Corporation."
    assert result.data["files"] == [str(path) for path in invoice_paths[:2]]


def test_search_invoice_files_returns_empty_list_when_no_match(tmp_path, monkeypatch):
    invoice_path = tmp_path / "invoice.pdf"
    invoice_path.touch()

    monkeypatch.setattr(file_tools, "INVOICE_DIR", tmp_path)
    monkeypatch.setattr(file_tools, "read_pdf_text", lambda _: "Different vendor")

    result = file_tools.search_invoice_files("Acme Corporation")

    assert result.success
    assert result.data == {"files": []}
