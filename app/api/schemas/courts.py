from pydantic import BaseModel


class CourtRequest(BaseModel):
    address: str
    debt_amount: float
    case_type: str  # Например: "имущественный_спор", "алименты"


class CourtResponse(BaseModel):
    name: str
    address: str
    type: str
    electronic_form_url: str | None
