from datetime import date
from pydantic import BaseModel, Field, field_validator

class InvoiceData(BaseModel):
    vendor_name: str
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    subtotal: float | None = Field(default=None, ge=0)
    tax: float | None = Field(default=None, ge=0)
    total_amount: float | None = Field(default=None, ge=0)
    payment_terms: str | None = None
    vendor_tax_id: str | None = None

    @field_validator("vendor_name")
    @classmethod
    def vendor_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("vendor_name cannot be blank")
        return value.strip()

class ExtractionResult(BaseModel):
    invoice: InvoiceData
    missing_fields: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    derivations: list[str] = Field(default_factory=list)
